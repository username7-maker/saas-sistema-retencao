from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_request_context
from app.core.security import decode_token
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import APIMessage, GymOwnerRegister, RefreshTokenInput, TokenPair, UserLogin, UserOut, UserRegister
from app.services.auth_service import authenticate_user, create_gym, create_user, issue_tokens, logout, refresh_access_token
from app.services.audit_service import log_audit_event


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: GymOwnerRegister, db: Annotated[Session, Depends(get_db)]) -> User:
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
def login(request: Request, payload: UserLogin, db: Annotated[Session, Depends(get_db)]) -> TokenPair:
    user = authenticate_user(db, payload)
    context = get_request_context(request)
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
        pass
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


@router.get("/me", response_model=UserOut)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
