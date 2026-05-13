from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


AssessmentAppointmentStatus = Literal["scheduled", "confirmed", "attended", "no_show", "cancelled", "rescheduled", "completed"]
AssessmentAppointmentPaymentStatus = Literal["unknown", "pending", "paid", "waived", "not_required"]


class AssessmentAppointmentBase(BaseModel):
    member_id: UUID
    scheduled_at: datetime
    assessment_type: str = Field(default="physical_assessment", max_length=60)
    status: AssessmentAppointmentStatus = "scheduled"
    payment_status: AssessmentAppointmentPaymentStatus = "unknown"
    evaluator_user_id: UUID | None = None
    evaluator_name_raw: str | None = Field(default=None, max_length=160)
    notes: str | None = None
    source: str = Field(default="manual", max_length=60)
    external_reference: str | None = Field(default=None, max_length=160)
    metadata_json: dict = Field(default_factory=dict)


class AssessmentAppointmentCreate(AssessmentAppointmentBase):
    pass


class AssessmentAppointmentUpdate(BaseModel):
    scheduled_at: datetime | None = None
    assessment_type: str | None = Field(default=None, max_length=60)
    status: AssessmentAppointmentStatus | None = None
    payment_status: AssessmentAppointmentPaymentStatus | None = None
    evaluator_user_id: UUID | None = None
    evaluator_name_raw: str | None = Field(default=None, max_length=160)
    notes: str | None = None
    source: str | None = Field(default=None, max_length=60)
    external_reference: str | None = Field(default=None, max_length=160)
    metadata_json: dict | None = None


class AssessmentAppointmentOut(BaseModel):
    id: UUID
    gym_id: UUID
    member_id: UUID
    member_name: str | None = None
    scheduled_at: datetime
    assessment_type: str
    status: str
    payment_status: str
    evaluator_user_id: UUID | None
    evaluator_name: str | None = None
    evaluator_name_raw: str | None
    notes: str | None
    source: str
    external_reference: str | None
    metadata_json: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
