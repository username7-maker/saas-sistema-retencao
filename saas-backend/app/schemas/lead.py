from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import LeadStage


class LeadCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    source: str = Field(min_length=2, max_length=80)
    stage: LeadStage = LeadStage.NEW
    pitch_step: str = Field(default="briefing", min_length=2, max_length=40)
    estimated_value: Decimal = Decimal("0")
    acquisition_cost: Decimal = Decimal("0")
    owner_id: UUID | None = None
    notes: list = Field(default_factory=list)


class LeadNoteCreate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    entry_type: str = Field(default="note", min_length=2, max_length=50)
    channel: str | None = Field(default=None, max_length=50)
    outcome: str | None = Field(default=None, max_length=80)
    occurred_at: datetime | None = None


class LeadConversionHandoff(BaseModel):
    plan_name: str = Field(min_length=2, max_length=100)
    join_date: date
    email_confirmed: bool = False
    phone_confirmed: bool = False
    notes: str | None = Field(default=None, max_length=1000)


class LeadUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    source: str | None = None
    stage: LeadStage | None = None
    pitch_step: str | None = Field(default=None, min_length=2, max_length=40)
    estimated_value: Decimal | None = None
    acquisition_cost: Decimal | None = None
    owner_id: UUID | None = None
    notes: list | None = None
    lost_reason: str | None = None
    last_contact_at: datetime | None = None
    converted_member_id: UUID | None = None
    conversion_handoff: LeadConversionHandoff | None = None


class LeadOut(BaseModel):
    id: UUID
    full_name: str
    email: str | None
    phone: str | None
    source: str
    stage: LeadStage
    pitch_step: str
    estimated_value: Decimal
    acquisition_cost: Decimal
    owner_id: UUID | None
    last_contact_at: datetime | None
    converted_member_id: UUID | None
    notes: list
    lost_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
