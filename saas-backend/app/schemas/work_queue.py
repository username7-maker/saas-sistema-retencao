from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


WorkQueueSourceType = Literal["task", "ai_triage", "assessment_queue", "ai_service_agent", "student_personal_ai"]
WorkQueueState = Literal["do_now", "awaiting_outcome", "done"]
WorkQueueSnoozePreset = Literal["tomorrow", "next_week", "custom"]
WorkQueueContactChannel = Literal["whatsapp", "kommo", "call", "in_person", "other"]
WorkQueueOutcome = Literal[
    "responded",
    "no_response",
    "scheduled_assessment",
    "will_return",
    "not_interested",
    "invalid_number",
    "postponed",
    "forwarded_to_trainer",
    "forwarded_to_reception",
    "forwarded_to_manager",
    "payment_confirmed",
    "payment_promised",
    "payment_link_sent",
    "charge_disputed",
    "training_delivered",
    "training_missing",
    "training_adjusted",
    "feedback_positive",
    "needs_training_adjustment",
    "reassessment_scheduled",
    "completed",
]


class WorkQueueItemOut(BaseModel):
    source_type: WorkQueueSourceType
    source_id: UUID
    subject_name: str
    member_id: UUID | None = None
    lead_id: UUID | None = None
    subject_phone: str | None = None
    domain: str
    severity: str
    preferred_shift: str | None = None
    reason: str
    primary_action_label: str
    primary_action_type: str
    suggested_message: str | None = None
    requires_confirmation: bool = False
    state: WorkQueueState
    due_at: datetime | None = None
    visible_from: datetime | None = None
    assigned_to_user_id: UUID | None = None
    context_path: str
    outcome_state: str
    retention_stage: str | None = None
    retention_stage_label: str | None = None
    retention_stage_priority: int = 0
    technical_ladder_step: str | None = None
    technical_ladder_step_label: str | None = None
    autopilot_state: str | None = None
    autopilot_badges: list[str] = Field(default_factory=list)
    execution_channel: str | None = None
    channel_action_label: str | None = None
    channel_status: str | None = None
    kommo_contact_id: str | None = None
    kommo_lead_id: str | None = None


class WorkQueueExecuteInput(BaseModel):
    auto_approve: bool = False
    confirm_approval: bool = False
    operator_note: str | None = Field(default=None, max_length=280)


class WorkQueueOutcomeInput(BaseModel):
    outcome: WorkQueueOutcome
    note: str | None = Field(default=None, max_length=280)
    scheduled_for: datetime | None = None
    snooze_preset: WorkQueueSnoozePreset | None = None
    contact_channel: WorkQueueContactChannel | None = None


class WorkQueueActionResultOut(BaseModel):
    item: WorkQueueItemOut
    detail: str
    prepared_message: str | None = None
    context_path: str
    task_id: UUID | None = None
    supported: bool = True
