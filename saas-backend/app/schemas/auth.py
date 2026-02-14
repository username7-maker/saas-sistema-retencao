from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models import RoleEnum


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: RoleEnum = RoleEnum.RECEPTIONIST


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: RoleEnum
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class RefreshTokenInput(BaseModel):
    refresh_token: str
