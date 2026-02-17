from datetime import datetime, timedelta, timezone
import re
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
from app.models import Gym, RoleEnum, User
from app.schemas import TokenPair, UserLogin, UserRegister


def _already_exists_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail ja cadastrado para esta academia")


def _auth_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais invalidas")


def _normalize_gym_slug(raw_slug: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", raw_slug.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if len(slug) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug da academia invalido")
    return slug


def create_gym(db: Session, *, name: str, slug: str) -> Gym:
    normalized_slug = _normalize_gym_slug(slug)
    existing = db.scalar(select(Gym).where(Gym.slug == normalized_slug))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug da academia ja cadastrado")

    gym = Gym(name=name.strip(), slug=normalized_slug, is_active=True)
    db.add(gym)
    db.commit()
    db.refresh(gym)
    return gym


def create_user(db: Session, payload: UserRegister, *, gym_id: UUID, force_role: RoleEnum | None = None) -> User:
    existing = db.scalar(
        select(User).where(
            User.email == payload.email,
            User.gym_id == gym_id,
            User.deleted_at.is_(None),
        )
    )
    if existing:
        raise _already_exists_exception()

    role = force_role or payload.role

    user = User(
        gym_id=gym_id,
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
    gym_slug = _normalize_gym_slug(payload.gym_slug)
    gym = db.scalar(select(Gym).where(Gym.slug == gym_slug, Gym.is_active.is_(True)))
    if not gym:
        raise _auth_exception()

    user = db.scalar(
        select(User).where(
            User.email == payload.email,
            User.gym_id == gym.id,
            User.deleted_at.is_(None),
        )
    )
    if not user or not verify_password(payload.password, user.hashed_password):
        raise _auth_exception()
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inativo")
    user.last_login_at = datetime.now(tz=timezone.utc)
    db.add(user)
    db.commit()
    return user


def issue_tokens(db: Session, user: User) -> TokenPair:
    access = create_access_token(user.id, user.role.value, user.gym_id)
    refresh = create_refresh_token(user.id, user.gym_id)
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
        token_gym_id = UUID(payload["gym_id"])
    except (KeyError, ValueError):
        raise _auth_exception()

    user = db.get(User, user_id)
    if (
        not user
        or user.deleted_at is not None
        or user.gym_id != token_gym_id
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
