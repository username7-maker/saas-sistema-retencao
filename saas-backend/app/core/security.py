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


def create_access_token(user_id: UUID, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "type": "access"}
    return _encode_token(payload, timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: UUID) -> str:
    payload = {"sub": str(user_id), "type": "refresh"}
    return _encode_token(payload, timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Token invalido ou expirado") from exc
