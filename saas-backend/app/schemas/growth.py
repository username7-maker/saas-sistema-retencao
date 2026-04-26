from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


GrowthAudienceId = Literal[
    "conversion_hot_leads",
    "conversion_stale_leads",
    "reactivation_inactive_members",
    "renewal_attention",
    "upsell_promoters",
    "nps_recovery",
]

GrowthSubjectType = Literal["lead", "member"]
GrowthChannel = Literal["whatsapp", "email", "task", "crm_note", "kommo"]


class GrowthOpportunityOut(BaseModel):
    id: str
    audience_id: GrowthAudienceId
    subject_type: GrowthSubjectType
    subject_id: UUID
    display_name: str
    contact: str | None = None
    preferred_shift: str | None = None
    stage_or_status: str | None = None
    score: int
    priority: Literal["low", "medium", "high", "urgent"]
    channel: GrowthChannel
    action_label: str
    reason: str
    suggested_message: str
    next_step: str
    consent_required: bool = True
    consent_ok: bool = False
    source_tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class GrowthAudienceOut(BaseModel):
    id: GrowthAudienceId
    label: str
    objective: str
    count: int
    priority: Literal["low", "medium", "high", "urgent"]
    recommended_channel: GrowthChannel
    cta_label: str
    summary: str
    experiment_hint: str
    items: list[GrowthOpportunityOut] = Field(default_factory=list)


class GrowthOpportunityPrepareInput(BaseModel):
    channel: GrowthChannel | None = None
    operator_note: str | None = Field(default=None, max_length=1000)
    create_task: bool = False


class GrowthOpportunityPreparedOut(BaseModel):
    opportunity_id: str
    prepared_action: str
    action_label: str
    channel: GrowthChannel
    target_name: str
    message: str
    whatsapp_url: str | None = None
    task_id: UUID | None = None
    crm_note_created: bool = False
    kommo_status: str | None = None
    warnings: list[str] = Field(default_factory=list)
