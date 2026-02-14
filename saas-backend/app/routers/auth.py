from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import APIMessage, RefreshTokenInput, TokenPair, UserLogin, UserOut, UserRegister
from app.services.auth_service import authenticate_user, create_user, issue_tokens, logout, refresh_access_token


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister, db: Annotated[Session, Depends(get_db)]) -> User:
    existing_user = db.scalar(select(User).limit(1))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registro aberto apenas para bootstrap inicial. Use endpoint interno para novos usuarios.",
        )
    return create_user(db, payload)


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, db: Annotated[Session, Depends(get_db)]) -> TokenPair:
    user = authenticate_user(db, payload)
    return issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshTokenInput, db: Annotated[Session, Depends(get_db)]) -> TokenPair:
    return refresh_access_token(db, payload.refresh_token)


@router.post("/logout", response_model=APIMessage)
def logout_session(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> APIMessage:
    logout(db, current_user)
    return APIMessage(message="Sessao encerrada")


@router.get("/me", response_model=UserOut)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
