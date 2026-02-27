from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
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


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    request: Request,
    payload: UserRegister,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> User:
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


@router.get("/me", response_model=UserOut)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
