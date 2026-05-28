from base64 import b64encode
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.core.security import hash_password, verify_password
from app.schemas import APIMessage, UserOut, UserRegister
from app.services.auth_service import (
    create_user,
    generate_bootstrap_password,
    generate_temporary_password,
    send_password_setup_email,
)
from app.services.audit_service import log_audit_event
from app.services.preferred_shift_service import normalize_preferred_shift, normalize_preferred_shift_scope


router = APIRouter(prefix="/users", tags=["users"])

MANAGER_ALLOWED_CREATE_ROLES = {
    RoleEnum.RECEPTIONIST,
    RoleEnum.SALESPERSON,
    RoleEnum.TRAINER,
}
WorkShift = Literal["overnight", "morning", "afternoon", "evening"]


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: RoleEnum | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    job_title: str | None = Field(default=None, max_length=120)
    work_shift: WorkShift | None = None
    work_shift_scope: list[WorkShift] | None = None
    avatar_url: str | None = None


class AdminUserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str | None = Field(default=None, min_length=8, max_length=72)
    password_setup: Literal["manual", "invite", "temporary"] = "manual"
    role: RoleEnum = RoleEnum.RECEPTIONIST
    job_title: str | None = Field(default=None, max_length=120)
    work_shift: WorkShift | None = None
    work_shift_scope: list[WorkShift] | None = None
    avatar_url: str | None = None


class UserCreatedOut(UserOut):
    temporary_password: str | None = None
    setup_status: Literal["invite_sent", "temporary_password_generated", "manual_password_set"] = "invite_sent"


class AdminPasswordResetOut(BaseModel):
    temporary_password: str


class UserActivationUpdate(BaseModel):
    is_active: bool


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    job_title: str | None = Field(default=None, max_length=120)
    work_shift: WorkShift | None = None
    work_shift_scope: list[WorkShift] | None = None
    avatar_url: str | None = None


class MyPasswordUpdate(BaseModel):
    current_password: str = Field(min_length=8, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)


ALLOWED_AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_UPLOAD_BYTES = 1_500_000


async def _read_avatar_upload(file: UploadFile) -> tuple[str, int]:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie uma imagem JPG, PNG ou WebP.",
        )

    payload = await file.read(MAX_AVATAR_UPLOAD_BYTES + 1)
    if len(payload) > MAX_AVATAR_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Imagem muito grande. Envie arquivo de ate 1,5 MB.",
        )
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo de imagem vazio.")

    encoded = b64encode(payload).decode("ascii")
    return f"data:{content_type};base64,{encoded}", len(payload)


@router.post("/", response_model=UserCreatedOut, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    request: Request,
    payload: AdminUserCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> UserCreatedOut:
    if current_user.role == RoleEnum.MANAGER and payload.role in {RoleEnum.OWNER, RoleEnum.MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gerente nao pode criar owner ou gerente")

    password_setup = "manual" if payload.password and payload.password_setup == "invite" else payload.password_setup
    if password_setup == "manual" and not payload.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe uma senha para criacao manual")

    generated_temporary_password: str | None = None
    if password_setup == "temporary":
        password = generate_temporary_password()
        generated_temporary_password = password
    elif password_setup == "manual":
        password = payload.password or ""
    else:
        password = generate_bootstrap_password()

    user_payload = UserRegister(
        full_name=payload.full_name,
        email=payload.email,
        password=password,
        role=payload.role,
        job_title=payload.job_title,
        work_shift=payload.work_shift,
        work_shift_scope=payload.work_shift_scope,
        avatar_url=payload.avatar_url,
    )
    new_user = create_user(db, user_payload, gym_id=current_user.gym_id, commit=False)

    if password_setup == "invite":
        email_result = send_password_setup_email(db, user=new_user, commit=False)
        if not email_result.sent:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE if email_result.blocked else status.HTTP_502_BAD_GATEWAY,
                detail="Nao foi possivel enviar o convite de senha. Use senha provisoria apenas se o usuario solicitou.",
            )

    context = get_request_context(request)
    setup_status: Literal["invite_sent", "temporary_password_generated", "manual_password_set"]
    if password_setup == "temporary":
        setup_status = "temporary_password_generated"
    elif password_setup == "manual":
        setup_status = "manual_password_set"
    else:
        setup_status = "invite_sent"
    log_audit_event(
        db,
        action="user_created",
        entity="user",
        user=current_user,
        entity_id=new_user.id,
        details={"email": new_user.email, "role": new_user.role.value, "password_setup": password_setup},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(new_user)
    return UserCreatedOut.model_validate(new_user).model_copy(
        update={"temporary_password": generated_temporary_password, "setup_status": setup_status}
    )


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
    if payload.work_shift is not None:
        current_user.work_shift = normalize_preferred_shift(payload.work_shift)
        if "work_shift_scope" not in updates:
            current_user.work_shift_scope = normalize_preferred_shift_scope(
                current_user.work_shift_scope,
                fallback=current_user.work_shift,
            )
    if "work_shift_scope" in updates:
        current_user.work_shift_scope = normalize_preferred_shift_scope(
            payload.work_shift_scope,
            fallback=current_user.work_shift,
        )
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


@router.post("/me/password", response_model=APIMessage)
def update_my_password_endpoint(
    request: Request,
    payload: MyPasswordUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> APIMessage:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual invalida")

    current_user.hashed_password = hash_password(payload.new_password)
    current_user.refresh_token_hash = None
    current_user.refresh_token_expires_at = None
    current_user.password_reset_token_hash = None
    current_user.password_reset_expires_at = None
    db.add(current_user)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="my_password_updated",
        entity="user",
        user=current_user,
        entity_id=current_user.id,
        details={"method": "authenticated_change"},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return APIMessage(message="Senha atualizada com sucesso. Entre novamente com a nova senha.")


@router.post("/me/avatar", response_model=UserOut)
async def upload_my_avatar_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> User:
    avatar_data_url, size_bytes = await _read_avatar_upload(file)
    current_user.avatar_url = avatar_data_url
    db.add(current_user)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="my_avatar_uploaded",
        entity="user",
        user=current_user,
        entity_id=current_user.id,
        details={"content_type": file.content_type, "size_bytes": size_bytes},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/{user_id}/avatar", response_model=UserOut)
async def upload_user_avatar_endpoint(
    request: Request,
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
) -> User:
    target = db.scalar(
        select(User).where(User.id == user_id, User.gym_id == current_user.gym_id, User.deleted_at.is_(None))
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    if current_user.role == RoleEnum.MANAGER and target.role == RoleEnum.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gerente nao pode editar avatar do owner")

    avatar_data_url, size_bytes = await _read_avatar_upload(file)
    target.avatar_url = avatar_data_url
    db.add(target)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="user_avatar_uploaded",
        entity="user",
        user=current_user,
        entity_id=target.id,
        details={"target_role": target.role.value, "content_type": file.content_type, "size_bytes": size_bytes},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(target)
    return target


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

    updates = payload.model_dump(exclude_unset=True)
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
    if payload.work_shift is not None:
        target.work_shift = normalize_preferred_shift(payload.work_shift)
        if "work_shift_scope" not in updates:
            target.work_shift_scope = normalize_preferred_shift_scope(target.work_shift_scope, fallback=target.work_shift)
    if "work_shift_scope" in updates:
        target.work_shift_scope = normalize_preferred_shift_scope(payload.work_shift_scope, fallback=target.work_shift)
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
        details={"updated_fields": updates},
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
    if payload.work_shift is not None:
        target.work_shift = normalize_preferred_shift(payload.work_shift)
        if "work_shift_scope" not in updates:
            target.work_shift_scope = normalize_preferred_shift_scope(target.work_shift_scope, fallback=target.work_shift)
    if "work_shift_scope" in updates:
        target.work_shift_scope = normalize_preferred_shift_scope(payload.work_shift_scope, fallback=target.work_shift)
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


@router.post("/{user_id}/password-reset", response_model=AdminPasswordResetOut)
def reset_user_password_endpoint(
    request: Request,
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> AdminPasswordResetOut:
    target = db.scalar(
        select(User).where(User.id == user_id, User.gym_id == current_user.gym_id, User.deleted_at.is_(None))
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")
    if target.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nao e possivel redefinir sua propria senha")
    if current_user.role == RoleEnum.OWNER and target.role == RoleEnum.OWNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner nao pode redefinir senha de outro owner")
    if current_user.role == RoleEnum.MANAGER and target.role not in MANAGER_ALLOWED_CREATE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gerente nao pode redefinir senha deste usuario")

    temporary_password = generate_temporary_password()
    target.hashed_password = hash_password(temporary_password)
    target.refresh_token_hash = None
    target.refresh_token_expires_at = None
    target.password_reset_token_hash = None
    target.password_reset_expires_at = None
    db.add(target)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="user_password_reset",
        entity="user",
        user=current_user,
        entity_id=target.id,
        details={"target_role": target.role.value},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return AdminPasswordResetOut(temporary_password=temporary_password)
