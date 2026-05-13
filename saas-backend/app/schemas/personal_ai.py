from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


PersonalAiMode = Literal["coach_review"]
PersonalAiDomain = Literal[
    "training_guidance",
    "routine_support",
    "assessment_explanation",
    "body_composition_explanation",
]
PersonalAiChannel = Literal["internal", "kommo"]


class PersonalAiSettingsOut(BaseModel):
    enabled: bool = False
    mode: PersonalAiMode = "coach_review"
    auto_send_enabled: bool = False
    sensitive_escalation_enabled: bool = True
    kommo_prepare_enabled: bool = True
    max_drafts_per_day: int = 50
    allowed_domains: list[str] = Field(default_factory=list)


class PersonalAiSettingsUpdate(BaseModel):
    enabled: bool | None = None
    mode: PersonalAiMode | None = None
    auto_send_enabled: bool | None = None
    sensitive_escalation_enabled: bool | None = None
    kommo_prepare_enabled: bool | None = None
    max_drafts_per_day: int | None = Field(default=None, ge=0, le=500)
    allowed_domains: list[str] | None = None


class PersonalAiContextOut(BaseModel):
    member_id: UUID
    member_name: str
    preferred_shift: str | None = None
    lifecycle_stage: str | None = None
    risk_level: str | None = None
    risk_score: int | None = None
    latest_assessment: dict | None = None
    latest_body_composition: dict | None = None
    active_training_plan: dict | None = None
    active_goals: list[dict] = Field(default_factory=list)
    constraints: dict | None = None
    checkins_30d: int = 0
    recent_technical_tasks: list[dict] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)


class PersonalAiDraftCreate(BaseModel):
    question: str = Field(min_length=3, max_length=1200)
    domain: PersonalAiDomain | None = None
    channel: PersonalAiChannel = "internal"


class PersonalAiDraftOut(BaseModel):
    id: UUID
    status: str
    gym_id: UUID
    member_id: UUID
    intent: str
    sensitivity: str
    summary: str
    draft_reply: str | None = None
    next_action: str
    recommended_owner_role: str
    blocked_reasons: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    question: str
    context_snapshot: PersonalAiContextOut | None = None
    kommo_contact_id: str | None = None
    kommo_lead_id: str | None = None
    kommo_task_id: str | None = None
    created_at: datetime
    updated_at: datetime


class PersonalAiPrepareResultOut(BaseModel):
    draft: PersonalAiDraftOut
    detail: str
    kommo_contact_id: str | None = None
    kommo_lead_id: str | None = None
    kommo_task_id: str | None = None
