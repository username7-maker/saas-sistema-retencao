from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def hash_refresh_token(refresh_token: str) -> str:
    return hash_password(refresh_token)


def verify_refresh_token(refresh_token: str, hashed_token: str) -> bool:
    return verify_password(refresh_token, hashed_token)


def _encode_token(payload: dict[str, Any], expires_delta: timedelta) -> str:
    expire_at = datetime.now(tz=timezone.utc) + expires_delta
    token_payload = payload | {"exp": expire_at}
    return jwt.encode(token_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    user_id_or_payload: UUID | dict[str, Any],
    role: str | None = None,
    gym_id: UUID | None = None,
) -> str:
    # Backward-compatible call style for tests/legacy code:
    # create_access_token({"sub": "...", "gym_id": "..."})
    if isinstance(user_id_or_payload, dict):
        payload = dict(user_id_or_payload)
        payload.setdefault("type", "access")
        return _encode_token(payload, timedelta(minutes=settings.access_token_expire_minutes))

    if role is None or gym_id is None:
        raise TypeError("create_access_token requires role and gym_id when called with user_id")

    payload = {"sub": str(user_id_or_payload), "role": role, "gym_id": str(gym_id), "type": "access"}
    return _encode_token(payload, timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: UUID, gym_id: UUID) -> str:
    payload = {"sub": str(user_id), "gym_id": str(gym_id), "type": "refresh"}
    return _encode_token(payload, timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Token invalido ou expirado") from exc
