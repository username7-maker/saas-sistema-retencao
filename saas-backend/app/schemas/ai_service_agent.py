from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


AiServiceAgentMode = Literal["draft_only"]


class AiServiceAgentSettingsOut(BaseModel):
    enabled: bool = False
    mode: AiServiceAgentMode = "draft_only"
    auto_send_enabled: bool = False
    sensitive_escalation_enabled: bool = True
    kommo_required: bool = True
    max_drafts_per_day: int = 100
    human_recent_activity_cooldown_hours: int = 24
    allowed_intents: list[str] = Field(default_factory=list)


class AiServiceAgentSettingsUpdate(BaseModel):
    enabled: bool | None = None
    mode: AiServiceAgentMode | None = None
    auto_send_enabled: bool | None = None
    sensitive_escalation_enabled: bool | None = None
    kommo_required: bool | None = None
    max_drafts_per_day: int | None = Field(default=None, ge=0, le=1000)
    human_recent_activity_cooldown_hours: int | None = Field(default=None, ge=0, le=168)
    allowed_intents: list[str] | None = None


class AiServiceAgentDraftOut(BaseModel):
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
    kommo_contact_id: str | None = None
    kommo_lead_id: str | None = None
    kommo_task_id: str | None = None
    created_at: datetime
    updated_at: datetime


class AiServiceAgentPrepareResultOut(BaseModel):
    draft: AiServiceAgentDraftOut
    detail: str
    kommo_contact_id: str | None = None
    kommo_lead_id: str | None = None
    kommo_task_id: str | None = None
