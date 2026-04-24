from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.schemas.core_async_job import CoreAsyncJobStatusRead


class SalesBriefProfileOut(BaseModel):
    lead_id: UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    source: str
    stage: str
    gym_name: str | None = None
    city: str | None = None
    estimated_members: int | None = None
    avg_monthly_fee: float | None = None
    current_management_system: str | None = None


class SalesBriefDiagnosisOut(BaseModel):
    has_diagnosis: bool
    message: str | None = None
    red_total: int = 0
    yellow_total: int = 0
    mrr_at_risk: float = 0.0
    annual_loss_projection: float = 0.0
    estimated_recovered_members: int = 0
    estimated_preserved_annual_revenue: float = 0.0


class SalesHistoryItemOut(BaseModel):
    kind: str
    channel: str | None = None
    title: str
    detail: str | None = None
    occurred_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SalesArgumentOut(BaseModel):
    title: str
    body: str
    usage: str


class SalesBriefOut(BaseModel):
    profile: SalesBriefProfileOut
    diagnosis: SalesBriefDiagnosisOut
    history: list[SalesHistoryItemOut] = Field(default_factory=list)
    ai_arguments: list[SalesArgumentOut] = Field(default_factory=list)
    next_step_recommended: str


class KnownObjectionOut(BaseModel):
    summary: str
    response_text: str
    source: str = "known"


class CallScriptOut(BaseModel):
    lead_id: UUID
    opening: str
    qualification_questions: list[str] = Field(default_factory=list)
    presentation_points: list[str] = Field(default_factory=list)
    objections: list[KnownObjectionOut] = Field(default_factory=list)
    closing: str
    quick_responses: dict[str, str] = Field(default_factory=dict)


class CallEventCreate(BaseModel):
    event_type: str = Field(min_length=2, max_length=64)
    label: str | None = Field(default=None, max_length=120)
    details: dict[str, Any] = Field(default_factory=dict)
    lost_reason: str | None = Field(default=None, max_length=1000)
    next_step: str | None = Field(default=None, max_length=80)


class CallEventResponse(BaseModel):
    message: str
    lead_id: UUID
    stage: str
    job_id: UUID | None = None
    job_status: str | None = None


class BookingStatusOut(BaseModel):
    has_booking: bool
    booking_id: UUID | None = None
    scheduled_for: datetime | None = None
    status: str | None = None
    provider_name: str | None = None


class PublicBookingConfirmRequest(BaseModel):
    lead_id: UUID | None = None
    prospect_name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    whatsapp: str | None = Field(default=None, max_length=32)
    scheduled_for: datetime
    provider_name: str | None = Field(default=None, max_length=40)
    provider_booking_id: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublicBookingConfirmResponse(BaseModel):
    message: str
    lead_id: UUID
    booking_id: UUID


class PublicWhatsappWebhookResponse(BaseModel):
    processed: bool
    detail: str


class LeadBookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID | None
    provider_name: str | None
    provider_booking_id: str | None
    prospect_name: str
    prospect_email: str | None
    prospect_whatsapp: str | None
    scheduled_for: datetime
    status: str
    reminder_sent_at: datetime | None
    extra_data: dict[str, Any]
    confirmed_at: datetime
    created_at: datetime
    updated_at: datetime


class LeadProposalDispatchStatusRead(CoreAsyncJobStatusRead):
    lead_id: UUID
