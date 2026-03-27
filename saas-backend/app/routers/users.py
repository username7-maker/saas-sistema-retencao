from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import UserOut, UserRegister
from app.services.auth_service import create_user
from app.services.audit_service import log_audit_event


router = APIRouter(prefix="/users", tags=["users"])


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: RoleEnum | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    job_title: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)


class UserActivationUpdate(BaseModel):
    is_active: bool


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    job_title: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    request: Request,
    payload: UserRegister,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> User:
    if current_user.role == RoleEnum.MANAGER and payload.role in {RoleEnum.OWNER, RoleEnum.MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gerente nao pode criar owner ou gerente")
    new_user = create_user(db, payload, gym_id=current_user.gym_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="user_created",
        entity="user",
        user=current_user,
        entity_id=new_user.id,
        details={"email": new_user.email, "role": new_user.role.value},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return new_user


@router.get("/", response_model=list[UserOut])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> list[User]:
    return db.scalars(
        select(User)
        .where(User.gym_id == current_user.gym_id, User.deleted_at.is_(None))
        .order_by(User.created_at.asc())
    ).all()


@router.get("/me", response_model=UserOut)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.patch("/me/profile", response_model=UserOut)
def update_my_profile_endpoint(
    request: Request,
    payload: UserProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    updates = payload.model_dump(exclude_unset=True)
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.job_title is not None:
        current_user.job_title = payload.job_title.strip() or None
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip() or None

    db.add(current_user)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="my_profile_updated",
        entity="user",
        user=current_user,
        entity_id=current_user.id,
        details={"updated_fields": list(updates.keys())},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/{user_id}", response_model=UserOut)
def update_user_endpoint(
    request: Request,
    user_id: UUID,
    payload: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER))],
) -> User:
    target = db.scalar(
        select(User).where(User.id == user_id, User.gym_id == current_user.gym_id, User.deleted_at.is_(None))
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    if target.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não é possível alterar sua própria conta")

    if payload.is_active is not None:
        target.is_active = payload.is_active
    if payload.role is not None:
        target.role = payload.role
    if payload.full_name is not None:
        target.full_name = payload.full_name.strip()
    if payload.email is not None:
        duplicate = db.scalar(
            select(User).where(
                User.email == payload.email,
                User.gym_id == current_user.gym_id,
                User.id != target.id,
                User.deleted_at.is_(None),
            )
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail ja cadastrado para esta academia")
        target.email = payload.email
    if payload.job_title is not None:
        target.job_title = payload.job_title.strip() or None
    if payload.avatar_url is not None:
        target.avatar_url = payload.avatar_url.strip() or None

    db.add(target)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="user_updated",
        entity="user",
        user=current_user,
        entity_id=target.id,
        details={"updated_fields": payload.model_dump(exclude_none=True)},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(target)
    return target


@router.patch("/{user_id}/profile", response_model=UserOut)
def update_user_profile_endpoint(
    request: Request,
    user_id: UUID,
    payload: UserProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> User:
    target = db.scalar(
        select(User).where(User.id == user_id, User.gym_id == current_user.gym_id, User.deleted_at.is_(None))
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    if current_user.role == RoleEnum.MANAGER and target.role == RoleEnum.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gerente nao pode editar perfil do owner")

    updates = payload.model_dump(exclude_unset=True)
    if payload.full_name is not None:
        target.full_name = payload.full_name.strip()
    if payload.job_title is not None:
        target.job_title = payload.job_title.strip() or None
    if payload.avatar_url is not None:
        target.avatar_url = payload.avatar_url.strip() or None

    db.add(target)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="user_profile_updated",
        entity="user",
        user=current_user,
        entity_id=target.id,
        details={"updated_fields": list(updates.keys())},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(target)
    return target


@router.patch("/{user_id}/activation", response_model=UserOut)
def update_user_activation_endpoint(
    request: Request,
    user_id: UUID,
    payload: UserActivationUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> User:
    target = db.scalar(
        select(User).where(User.id == user_id, User.gym_id == current_user.gym_id, User.deleted_at.is_(None))
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    if target.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não é possível alterar sua própria conta")
    if current_user.role == RoleEnum.MANAGER and target.role == RoleEnum.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gerente nao pode ativar ou desativar owner")

    target.is_active = payload.is_active
    db.add(target)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="user_activation_updated",
        entity="user",
        user=current_user,
        entity_id=target.id,
        details={"is_active": payload.is_active},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(target)
    return target


