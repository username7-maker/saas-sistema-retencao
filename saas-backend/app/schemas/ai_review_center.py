from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


AiReviewCenterSource = Literal[
    "ai_service_agent",
    "personal_ai",
    "student_personal_ai",
    "movement_video",
    "movement_video_review",
]

AiReviewCenterFeedbackDecision = Literal["approved", "edited", "rejected", "escalated"]


class AiReviewCenterItemOut(BaseModel):
    source_type: AiReviewCenterSource
    source_id: UUID
    status: str
    domain: str
    channel: str | None = None
    subject_name: str
    member_id: UUID | None = None
    lead_id: UUID | None = None
    intent: str | None = None
    sensitivity: str | None = None
    summary: str | None = None
    received_message: str | None = None
    draft_reply: str | None = None
    next_action: str | None = None
    recommended_owner_role: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    badges: list[str] = Field(default_factory=list)
    context_path: str | None = None
    kommo_contact_id: str | None = None
    kommo_lead_id: str | None = None
    kommo_task_id: str | None = None
    review_decision: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by_user_id: UUID | None = None
    review_notes: str | None = None
    review_latency_minutes: int | None = None
    can_prepare_kommo: bool = False
    can_reject: bool = True
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AiReviewCenterMetricsOut(BaseModel):
    total: int = 0
    ready: int = 0
    blocked: int = 0
    escalated: int = 0
    awaiting_outcome: int = 0
    prepared: int = 0
    reviewed: int = 0
    approved: int = 0
    edited: int = 0
    rejected: int = 0
    review_escalated: int = 0
    utilization_rate: float = 0.0
    average_review_minutes: int | None = None
    by_source: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)


class AiReviewCenterListOut(BaseModel):
    items: list[AiReviewCenterItemOut] = Field(default_factory=list)
    metrics: AiReviewCenterMetricsOut
    generated_at: datetime


class AiReviewCenterRejectInput(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class AiReviewCenterFeedbackInput(BaseModel):
    decision: AiReviewCenterFeedbackDecision
    reason: str | None = Field(default=None, max_length=500)
    edited_reply: str | None = Field(default=None, max_length=4000)


class AiReviewCenterActionOut(BaseModel):
    item: AiReviewCenterItemOut
    detail: str
    kommo_contact_id: str | None = None
    kommo_lead_id: str | None = None
    kommo_task_id: str | None = None
