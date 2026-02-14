from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import decode_token, oauth2_scheme
from app.database import get_db
from app.models import RoleEnum, User


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais invalidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise _credentials_exception()
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise _credentials_exception()

    user = db.get(User, user_id)
    if not user or not user.is_active or user.deleted_at is not None:
        raise _credentials_exception()
    return user


def require_roles(*roles: RoleEnum) -> Callable[[User], User]:
    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente",
            )
        return current_user

    return dependency


def get_request_context(request: Request) -> dict[str, str]:
    return {
        "ip_address": request.client.host if request.client else "",
        "user_agent": request.headers.get("user-agent", ""),
    }
