from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.models import RoleEnum, User
from app.schemas import TokenPair, UserLogin, UserRegister


def _already_exists_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail ja cadastrado")


def _auth_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais invalidas")


def create_user(db: Session, payload: UserRegister) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email, User.deleted_at.is_(None)))
    if existing:
        raise _already_exists_exception()

    first_user = db.scalar(select(User).limit(1))
    role = payload.role
    if first_user is None:
        role = RoleEnum.OWNER

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: UserLogin) -> User:
    user = db.scalar(select(User).where(User.email == payload.email, User.deleted_at.is_(None)))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise _auth_exception()
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inativo")
    user.last_login_at = datetime.now(tz=timezone.utc)
    db.add(user)
    db.commit()
    return user


def issue_tokens(db: Session, user: User) -> TokenPair:
    access = create_access_token(user.id, user.role.value)
    refresh = create_refresh_token(user.id)
    user.refresh_token_hash = hash_refresh_token(refresh)
    user.refresh_token_expires_at = datetime.now(tz=timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    db.add(user)
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


def refresh_access_token(db: Session, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise _auth_exception()
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        raise _auth_exception()

    user = db.get(User, user_id)
    if (
        not user
        or user.deleted_at is not None
        or not user.refresh_token_hash
        or not verify_refresh_token(refresh_token, user.refresh_token_hash)
    ):
        raise _auth_exception()

    if not user.refresh_token_expires_at or user.refresh_token_expires_at < datetime.now(tz=timezone.utc):
        raise _auth_exception()

    return issue_tokens(db, user)


def logout(db: Session, user: User) -> None:
    user.refresh_token_hash = None
    user.refresh_token_expires_at = None
    db.add(user)
    db.commit()
