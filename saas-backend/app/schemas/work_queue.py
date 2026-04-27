from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


WorkQueueSourceType = Literal["task", "ai_triage"]
WorkQueueState = Literal["do_now", "awaiting_outcome", "done"]
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
    "completed",
]


class WorkQueueItemOut(BaseModel):
    source_type: WorkQueueSourceType
    source_id: UUID
    subject_name: str
    member_id: UUID | None = None
    lead_id: UUID | None = None
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
    assigned_to_user_id: UUID | None = None
    context_path: str
    outcome_state: str


class WorkQueueExecuteInput(BaseModel):
    auto_approve: bool = False
    confirm_approval: bool = False
    operator_note: str | None = Field(default=None, max_length=280)


class WorkQueueOutcomeInput(BaseModel):
    outcome: WorkQueueOutcome
    note: str | None = Field(default=None, max_length=280)


class WorkQueueActionResultOut(BaseModel):
    item: WorkQueueItemOut
    detail: str
    prepared_message: str | None = None
    context_path: str
    task_id: UUID | None = None
    supported: bool = True
