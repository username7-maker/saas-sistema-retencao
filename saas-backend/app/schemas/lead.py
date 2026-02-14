from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models import LeadStage


class LeadCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    source: str = Field(min_length=2, max_length=80)
    stage: LeadStage = LeadStage.NEW
    estimated_value: Decimal = Decimal("0")
    acquisition_cost: Decimal = Decimal("0")
    owner_id: UUID | None = None
    notes: list = Field(default_factory=list)


class LeadUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    source: str | None = None
    stage: LeadStage | None = None
    estimated_value: Decimal | None = None
    acquisition_cost: Decimal | None = None
    owner_id: UUID | None = None
    notes: list | None = None
    lost_reason: str | None = None
    last_contact_at: datetime | None = None
    converted_member_id: UUID | None = None


class LeadOut(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr | None
    phone: str | None
    source: str
    stage: LeadStage
    estimated_value: Decimal
    acquisition_cost: Decimal
    owner_id: UUID | None
    last_contact_at: datetime | None
    converted_member_id: UUID | None
    notes: list
    lost_reason: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
