import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_request_context
from app.core.limiter import limiter
from app.core.security import decode_token
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import APIMessage, GymOwnerRegister, RefreshTokenInput, TokenPair, UserLogin, UserOut, UserRegister
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.services.auth_service import (
    authenticate_user,
    create_gym,
    create_user,
    issue_tokens,
    logout,
    refresh_access_token,
    request_password_reset,
    reset_password,
)
from app.services.audit_service import log_audit_event


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
def register_user(request: Request, payload: GymOwnerRegister, db: Annotated[Session, Depends(get_db)]) -> User:
    gym = create_gym(db, name=payload.gym_name, slug=payload.gym_slug)
    user_payload = UserRegister(
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        role=RoleEnum.OWNER,
    )
    user = create_user(db, user_payload, gym_id=gym.id, force_role=RoleEnum.OWNER)
    log_audit_event(
        db,
        action="auth_bootstrap_register",
        entity="user",
        user=user,
        entity_id=user.id,
        details={"email": user.email, "gym_id": str(gym.id), "gym_slug": gym.slug},
    )
    db.commit()
    return user


@router.post("/login", response_model=TokenPair)
@limiter.limit("5/minute")
def login(request: Request, payload: UserLogin, db: Annotated[Session, Depends(get_db)]) -> TokenPair:
    context = get_request_context(request)
    try:
        user = authenticate_user(db, payload)
    except HTTPException:
        log_audit_event(
            db,
            action="auth_login_failed",
            entity="user",
            details={"email": payload.email, "gym_slug": payload.gym_slug},
            ip_address=context["ip_address"],
            user_agent=context["user_agent"],
        )
        db.commit()
        raise
    log_audit_event(
        db,
        action="auth_login",
        entity="user",
        user=user,
        entity_id=user.id,
        details={"email": user.email},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    return issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(request: Request, payload: RefreshTokenInput, db: Annotated[Session, Depends(get_db)]) -> TokenPair:
    tokens = refresh_access_token(db, payload.refresh_token)
    context = get_request_context(request)
    try:
        decoded = decode_token(payload.refresh_token)
        user = db.get(User, UUID(decoded["sub"]))
        if user:
            log_audit_event(
                db,
                action="auth_refresh",
                entity="user",
                user=user,
                entity_id=user.id,
                ip_address=context["ip_address"],
                user_agent=context["user_agent"],
            )
            db.commit()
    except Exception:
        logger.warning("Falha ao registrar audit de refresh", exc_info=True)
    return tokens


@router.post("/logout", response_model=APIMessage)
def logout_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> APIMessage:
    context = get_request_context(request)
    log_audit_event(
        db,
        action="auth_logout",
        entity="user",
        user=current_user,
        entity_id=current_user.id,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    logout(db, current_user)
    return APIMessage(message="Sessao encerrada")



@router.post("/forgot-password", response_model=APIMessage)
@limiter.limit("3/hour")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Annotated[Session, Depends(get_db)]) -> APIMessage:
    request_password_reset(db, email=payload.email, gym_slug=payload.gym_slug)
    return APIMessage(message="Se o e-mail estiver cadastrado, você receberá as instruções em breve.")


@router.post("/reset-password", response_model=APIMessage)
@limiter.limit("5/minute")
def do_reset_password(request: Request, payload: ResetPasswordRequest, db: Annotated[Session, Depends(get_db)]) -> APIMessage:
    reset_password(db, token=payload.token, new_password=payload.new_password)
    return APIMessage(message="Senha redefinida com sucesso. Faça login com a nova senha.")
