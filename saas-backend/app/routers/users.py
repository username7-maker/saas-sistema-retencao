from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import UserOut, UserRegister
from app.services.auth_service import create_user


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserRegister,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> User:
    return create_user(db, payload)


@router.get("/", response_model=list[UserOut])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> list[User]:
    return db.scalars(select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.asc())).all()


@router.get("/me", response_model=UserOut)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
