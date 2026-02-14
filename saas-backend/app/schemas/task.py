from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import TaskPriority, TaskStatus


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
    priority: TaskPriority
    status: TaskStatus
    kanban_column: str
    due_date: datetime | None
    completed_at: datetime | None
    suggested_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
