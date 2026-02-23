from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
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
from app.utils.email import send_email

_PASSWORD_RESET_EXPIRY_HOURS = 1


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


def request_password_reset(db: Session, *, email: str, gym_slug: str) -> None:
    """Generate a reset token and send it via email. Always returns successfully
    (even if the user does not exist) to avoid account enumeration."""
    normalized_slug = _normalize_gym_slug(gym_slug)
    gym = db.scalar(select(Gym).where(Gym.slug == normalized_slug, Gym.is_active.is_(True)))
    if not gym:
        return

    user = db.scalar(
        select(User).where(
            User.email == email,
            User.gym_id == gym.id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
    )
    if not user:
        return

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    user.password_reset_token_hash = token_hash
    user.password_reset_expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=_PASSWORD_RESET_EXPIRY_HOURS)
    db.add(user)
    db.commit()

    reset_link = f"{settings.frontend_url}/reset-password?token={raw_token}"
    send_email(
        to_email=email,
        subject="Redefinição de Senha — AI GYM OS",
        content=(
            f"Olá, {user.full_name}!\n\n"
            f"Clique no link abaixo para redefinir sua senha (válido por {_PASSWORD_RESET_EXPIRY_HOURS}h):\n\n"
            f"{reset_link}\n\n"
            "Se você não solicitou a redefinição, ignore este e-mail."
        ),
    )


def reset_password(db: Session, *, token: str, new_password: str) -> None:
    """Validate the reset token and update the user's password."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(tz=timezone.utc)

    user = db.scalar(
        select(User).where(
            User.password_reset_token_hash == token_hash,
            User.password_reset_expires_at > now,
            User.deleted_at.is_(None),
        )
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado",
        )

    user.hashed_password = hash_password(new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.refresh_token_hash = None
    user.refresh_token_expires_at = None
    db.add(user)
    db.commit()
