from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


AutomationJourneyDomain = Literal[
    "onboarding",
    "retention",
    "nps",
    "renewal",
    "finance",
    "commercial",
    "upsell",
]


class AutomationJourneyStepTemplateOut(BaseModel):
    name: str
    delay_days: int = 0
    delay_hours: int = 0
    action_type: str
    channel: str | None = None
    owner_role: str | None = None
    severity: str = "medium"
    message: str | None = None


class AutomationJourneyTemplateOut(BaseModel):
    id: str
    name: str
    description: str
    domain: AutomationJourneyDomain | str
    entry_trigger: str
    requires_human_approval: bool = True
    steps: list[AutomationJourneyStepTemplateOut] = Field(default_factory=list)


class AutomationJourneyStepOut(BaseModel):
    id: UUID
    journey_id: UUID
    step_order: int
    name: str
    delay_days: int
    delay_hours: int
    condition_config: dict = Field(default_factory=dict)
    action_type: str
    action_config: dict = Field(default_factory=dict)
    channel: str | None = None
    owner_role: str | None = None
    preferred_shift: str | None = None
    template_key: str | None = None
    fallback_mode: str
    severity: str

    model_config = ConfigDict(from_attributes=True)


class AutomationJourneyOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    domain: str
    entry_trigger: str
    audience_config: dict = Field(default_factory=dict)
    exit_conditions: dict = Field(default_factory=dict)
    metrics_config: dict = Field(default_factory=dict)
    is_active: bool
    requires_human_approval: bool
    steps: list[AutomationJourneyStepOut] = Field(default_factory=list)
    enrollments_total: int = 0
    active_enrollments_total: int = 0
    awaiting_outcome_total: int = 0
    tasks_created_total: int = 0
    positive_outcomes_total: int = 0
    neutral_outcomes_total: int = 0
    negative_outcomes_total: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AutomationJourneyCreate(BaseModel):
    template_id: str | None = None
    name: str | None = Field(default=None, max_length=160)
    description: str | None = None
    domain: str | None = None
    entry_trigger: str | None = None
    audience_config: dict = Field(default_factory=dict)
    exit_conditions: dict = Field(default_factory=dict)
    metrics_config: dict = Field(default_factory=dict)
    requires_human_approval: bool = True


class AutomationJourneyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = None
    audience_config: dict | None = None
    exit_conditions: dict | None = None
    metrics_config: dict | None = None
    requires_human_approval: bool | None = None


class AutomationJourneyPreviewSampleOut(BaseModel):
    id: UUID
    kind: Literal["member", "lead", "task"]
    name: str
    preferred_shift: str | None = None
    reason: str | None = None


class AutomationJourneyPreviewOut(BaseModel):
    template_id: str | None = None
    journey_id: UUID | None = None
    eligible_count: int
    sample: list[AutomationJourneyPreviewSampleOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AutomationJourneyActivationOut(BaseModel):
    journey: AutomationJourneyOut
    enrolled_count: int
    skipped_existing_count: int


class AutomationJourneyEnrollmentOut(BaseModel):
    id: UUID
    journey_id: UUID
    member_id: UUID | None
    lead_id: UUID | None
    subject_name: str
    state: str
    current_step_order: int
    next_step_due_at: datetime | None
    last_executed_at: datetime | None
    exit_reason: str | None
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AutomationJourneyEventOut(BaseModel):
    id: UUID
    journey_id: UUID
    enrollment_id: UUID | None
    step_id: UUID | None
    task_id: UUID | None
    member_id: UUID | None
    lead_id: UUID | None
    user_id: UUID | None
    event_type: str
    outcome: str | None
    note: str | None
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
