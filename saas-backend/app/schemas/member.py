from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models import MemberStatus, RiskLevel


class MemberCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=14)
    plan_name: str = "Plano Base"
    monthly_fee: Decimal = Decimal("0")
    join_date: date = Field(default_factory=date.today)
    preferred_shift: str | None = None
    assigned_user_id: UUID | None = None
    loyalty_months: int = 0
    extra_data: dict = Field(default_factory=dict)


class MemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=14)
    status: MemberStatus | None = None
    plan_name: str | None = None
    monthly_fee: Decimal | None = None
    preferred_shift: str | None = None
    assigned_user_id: UUID | None = None
    loyalty_months: int | None = None
    nps_last_score: int | None = Field(default=None, ge=0, le=10)
    extra_data: dict | None = None


class MemberOut(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr | None
    phone: str | None
    status: MemberStatus
    plan_name: str
    monthly_fee: Decimal
    join_date: date
    preferred_shift: str | None
    nps_last_score: int
    loyalty_months: int
    risk_score: int
    risk_level: RiskLevel
    last_checkin_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemberRiskOut(BaseModel):
    member_id: UUID
    score: int
    level: RiskLevel
    reasons: dict
