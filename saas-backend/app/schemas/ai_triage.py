from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AITriageRecommendedOwner(BaseModel):
    user_id: UUID | None = None
    role: str | None = None
    label: str | None = None


class AITriageRecommendationRead(BaseModel):
    id: UUID
    source_domain: str
    source_entity_kind: str
    source_entity_id: UUID
    member_id: UUID | None = None
    lead_id: UUID | None = None
    subject_name: str
    priority_score: int
    priority_bucket: str
    why_now_summary: str
    why_now_details: list[str] = []
    recommended_action: str
    recommended_channel: str | None = None
    recommended_owner: AITriageRecommendedOwner | None = None
    suggested_message: str | None = None
    expected_impact: str
    operator_summary: str
    primary_action_type: str | None = None
    primary_action_label: str | None = None
    requires_explicit_approval: bool = False
    show_outcome_step: bool = False
    suggestion_state: str
    approval_state: str
    execution_state: str
    outcome_state: str
    metadata: dict[str, Any] = {}
    last_refreshed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AITriageApprovalUpdate(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=280)


class AITriageSafeActionPrepareInput(BaseModel):
    action: Literal[
        "create_task",
        "assign_owner",
        "open_follow_up",
        "prepare_outbound_message",
        "enqueue_approved_job",
    ]
    assigned_to_user_id: UUID | None = None
    owner_role: str | None = Field(default=None, max_length=64)
    owner_label: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=280)
    operator_note: str | None = Field(default=None, max_length=280)
    auto_approve: bool = False
    confirm_approval: bool = False


class AITriageSafeActionPreparedRead(BaseModel):
    recommendation: AITriageRecommendationRead
    action: str
    supported: bool
    detail: str
    task_id: UUID | None = None
    follow_up_url: str | None = None
    prepared_message: str | None = None
    metadata: dict[str, Any] = {}


class AITriageOutcomeUpdate(BaseModel):
    outcome: Literal["pending", "positive", "neutral", "negative"]
    note: str | None = Field(default=None, max_length=280)


class AITriageMetricsSummaryRead(BaseModel):
    total_active: int
    pending_approval_total: int
    approved_total: int
    rejected_total: int
    prepared_action_total: int
    positive_outcome_total: int
    neutral_outcome_total: int
    negative_outcome_total: int
    acceptance_rate: float | None = None
    average_time_to_approval_seconds: float | None = None
    median_time_to_approval_seconds: float | None = None
    same_day_prepared_total: int
