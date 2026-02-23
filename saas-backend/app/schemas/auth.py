from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import RoleEnum


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: RoleEnum = RoleEnum.RECEPTIONIST


class GymOwnerRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    gym_name: str = Field(min_length=2, max_length=160)
    gym_slug: str = Field(min_length=3, max_length=80)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    gym_slug: str = Field(min_length=3, max_length=80)


class UserOut(BaseModel):
    id: UUID
    gym_id: UUID
    full_name: str
    email: EmailStr
    role: RoleEnum
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class RefreshTokenInput(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    gym_slug: str = Field(min_length=3, max_length=80)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)
