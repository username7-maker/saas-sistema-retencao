from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


StudentPersonalAiMode = Literal["draft_only"]


class StudentPersonalAiSettingsOut(BaseModel):
    enabled: bool = False
    mode: StudentPersonalAiMode = "draft_only"
    auto_send_enabled: bool = False
    kommo_required: bool = True
    personal_ai_enabled: bool = True
    movement_video_enabled: bool = True
    require_member_match: bool = True
    require_communication_consent: bool = True
    require_image_consent_for_video: bool = True
    sensitive_escalation_enabled: bool = True
    max_drafts_per_day: int = 50
    human_recent_activity_cooldown_hours: int = 24
    allowed_domains: list[str] = Field(default_factory=list)


class StudentPersonalAiSettingsUpdate(BaseModel):
    enabled: bool | None = None
    mode: StudentPersonalAiMode | None = None
    auto_send_enabled: bool | None = None
    kommo_required: bool | None = None
    personal_ai_enabled: bool | None = None
    movement_video_enabled: bool | None = None
    require_member_match: bool | None = None
    require_communication_consent: bool | None = None
    require_image_consent_for_video: bool | None = None
    sensitive_escalation_enabled: bool | None = None
    max_drafts_per_day: int | None = Field(default=None, ge=0, le=500)
    human_recent_activity_cooldown_hours: int | None = Field(default=None, ge=0, le=168)
    allowed_domains: list[str] | None = None


class StudentPersonalAiDraftOut(BaseModel):
    id: UUID
    status: str
    gym_id: UUID
    member_id: UUID | None = None
    lead_id: UUID | None = None
    intent: str
    sensitivity: str
    summary: str
    draft_reply: str | None = None
    next_action: str
    recommended_owner_role: str
    blocked_reasons: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    received_message: str | None = None
    source_event_id: str | None = None
    message_log_id: str | None = None
    movement_video_review_id: str | None = None
    kommo_contact_id: str | None = None
    kommo_lead_id: str | None = None
    kommo_task_id: str | None = None
    created_at: datetime
    updated_at: datetime


class StudentPersonalAiPrepareResultOut(BaseModel):
    draft: StudentPersonalAiDraftOut
    detail: str
    kommo_contact_id: str | None = None
    kommo_lead_id: str | None = None
    kommo_task_id: str | None = None


class StudentPersonalAiRejectInput(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
