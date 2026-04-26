from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.lead import LeadOut
from app.schemas.sales import LeadBookingOut


class AcquisitionCaptureInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    source: str = Field(default="landing_page", min_length=2, max_length=80)
    channel: str | None = Field(default=None, max_length=80)
    campaign: str | None = Field(default=None, max_length=120)
    desired_goal: str | None = Field(default=None, max_length=300)
    preferred_shift: str | None = Field(default=None, max_length=40)
    trial_interest: bool = False
    scheduled_for: datetime | None = None
    consent_lgpd: bool | None = None
    consent_communication: bool | None = None
    operator_note: str | None = Field(default=None, max_length=1000)
    qualification_answers: dict[str, Any] = Field(default_factory=dict)
    estimated_value: Decimal = Decimal("0")
    acquisition_cost: Decimal = Decimal("0")
    owner_id: UUID | None = None


class AcquisitionQualificationOut(BaseModel):
    score: int = Field(ge=0, le=100)
    label: str
    next_action: str
    recommended_stage: str
    reasons: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class AcquisitionLeadSummaryOut(BaseModel):
    lead_id: UUID
    full_name: str
    source: str | None = None
    channel: str | None = None
    campaign: str | None = None
    desired_goal: str | None = None
    preferred_shift: str | None = None
    qualification_score: int | None = None
    qualification_label: str | None = None
    next_action: str | None = None
    has_trial_booking: bool = False
    next_booking_at: datetime | None = None
    consent_lgpd: bool | None = None
    consent_communication: bool | None = None
    reasons: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class AcquisitionCaptureResponse(BaseModel):
    lead: LeadOut
    booking: LeadBookingOut | None = None
    qualification: AcquisitionQualificationOut
    summary: AcquisitionLeadSummaryOut
