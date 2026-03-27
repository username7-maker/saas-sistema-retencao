import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
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


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.resolved_refresh_cookie_secure,
        samesite=settings.resolved_refresh_cookie_samesite,
        path=settings.refresh_cookie_path,
        domain=settings.refresh_cookie_domain or None,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        domain=settings.refresh_cookie_domain or None,
        secure=settings.resolved_refresh_cookie_secure,
        httponly=True,
        samesite=settings.resolved_refresh_cookie_samesite,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _client_visible_tokens(tokens: TokenPair) -> TokenPair:
    return TokenPair(
        access_token=tokens.access_token,
        refresh_token=None,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )


def _resolve_refresh_token(request: Request, payload: RefreshTokenInput | None) -> str:
    body_token = (payload.refresh_token if payload else None) or ""
    if isinstance(body_token, str) and body_token.strip():
        return body_token.strip()

    cookie_token = request.cookies.get(settings.refresh_cookie_name, "").strip()
    if cookie_token:
        return cookie_token

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais invalidas")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
def register_user(request: Request, payload: GymOwnerRegister, db: Annotated[Session, Depends(get_db)]) -> User:
    gym = create_gym(db, name=payload.gym_name, slug=payload.gym_slug, commit=False)
    user_payload = UserRegister(
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        role=RoleEnum.OWNER,
    )
    user = create_user(db, user_payload, gym_id=gym.id, force_role=RoleEnum.OWNER, commit=False)
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
def login(request: Request, response: Response, payload: UserLogin, db: Annotated[Session, Depends(get_db)]) -> TokenPair:
    context = get_request_context(request)
    try:
        user = authenticate_user(db, payload, commit=False)
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
    tokens = issue_tokens(db, user, commit=False)
    db.commit()
    _set_refresh_cookie(response, tokens.refresh_token or "")
    return _client_visible_tokens(tokens)


@router.post("/refresh", response_model=TokenPair)
def refresh(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    payload: RefreshTokenInput | None = None,
) -> TokenPair:
    refresh_token = _resolve_refresh_token(request, payload)
    tokens = refresh_access_token(db, refresh_token, commit=False)
    context = get_request_context(request)
    try:
        decoded = decode_token(refresh_token)
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
        db.commit()
    _set_refresh_cookie(response, tokens.refresh_token or "")
    return _client_visible_tokens(tokens)


@router.post("/logout", response_model=APIMessage)
def logout_session(
    request: Request,
    response: Response,
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
    logout(db, current_user, commit=False)
    db.commit()
    _clear_refresh_cookie(response)
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
