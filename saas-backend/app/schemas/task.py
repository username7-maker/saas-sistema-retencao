from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import TaskPriority, TaskStatus

TaskEventType = Literal[
    "comment",
    "execution_started",
    "contact_attempt",
    "outcome_recorded",
    "snoozed",
    "status_changed",
    "reassigned",
    "forwarded",
    "delinquency_stage_updated",
]
TaskContactChannel = Literal["whatsapp", "call", "in_person", "other"]
TaskOutcome = Literal[
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
    "completed",
]


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str | None = None
    member_id: UUID | None = None
    lead_id: UUID | None = None
    assigned_to_user_id: UUID | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    due_date: datetime | None = None
    suggested_message: str | None = None
    extra_data: dict = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = None
    assigned_to_user_id: UUID | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    kanban_column: str | None = None
    due_date: datetime | None = None
    suggested_message: str | None = None
    extra_data: dict | None = None


class TaskOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    member_id: UUID | None
    lead_id: UUID | None
    assigned_to_user_id: UUID | None
    # Enriched display names — populated by the service layer via eager-loaded relationships
    member_name: str | None = None
    lead_name: str | None = None
    preferred_shift: str | None = None
    priority: TaskPriority
    status: TaskStatus
    kanban_column: str
    due_date: datetime | None
    completed_at: datetime | None
    suggested_message: str | None
    extra_data: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskEventCreate(BaseModel):
    event_type: TaskEventType
    outcome: TaskOutcome | None = None
    contact_channel: TaskContactChannel | None = None
    note: str | None = Field(default=None, max_length=1000)
    scheduled_for: datetime | None = None
    metadata_json: dict = Field(default_factory=dict)


class TaskEventOut(BaseModel):
    id: UUID
    gym_id: UUID
    task_id: UUID
    member_id: UUID | None
    lead_id: UUID | None
    user_id: UUID | None
    event_type: str
    outcome: str | None
    contact_channel: str | None
    note: str | None
    scheduled_for: datetime | None
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskMetricsOwnerOut(BaseModel):
    user_id: UUID | None
    owner_name: str
    open_total: int = 0
    overdue_total: int = 0
    completed_7d_total: int = 0


class TaskMetricsBreakdownOut(BaseModel):
    key: str
    label: str
    total: int


class TaskMetricsOut(BaseModel):
    open_total: int = 0
    overdue_total: int = 0
    due_today_total: int = 0
    completed_today_total: int = 0
    completed_7d_total: int = 0
    avg_completion_hours: float | None = None
    on_time_rate_pct: float | None = None
    by_owner: list[TaskMetricsOwnerOut] = Field(default_factory=list)
    by_source: list[TaskMetricsBreakdownOut] = Field(default_factory=list)
    by_outcome: list[TaskMetricsBreakdownOut] = Field(default_factory=list)


class TaskOperationalCleanupPreviewOut(BaseModel):
    candidate_total: int = 0
    cutoff_days: int = 14
    oldest_created_at: datetime | None = None
    by_source: list[TaskMetricsBreakdownOut] = Field(default_factory=list)


class TaskOperationalCleanupApplyInput(BaseModel):
    reason: str = Field(default="fila_24h_cleanup", min_length=3, max_length=160)


class TaskOperationalCleanupApplyOut(TaskOperationalCleanupPreviewOut):
    archived_total: int = 0
    batch_id: str
