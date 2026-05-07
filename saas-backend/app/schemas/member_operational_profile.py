from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


MemberNoteType = Literal["internal", "retention", "coach", "manager", "sales_handoff", "health_context"]
MemberNoteVisibility = Literal["internal", "team", "manager", "coach", "sales"]


class MemberNoteCreate(BaseModel):
    note_type: MemberNoteType = "internal"
    body: str = Field(min_length=1, max_length=5000)
    visibility: MemberNoteVisibility = "internal"
    extra_data: dict = Field(default_factory=dict)


class MemberNoteOut(BaseModel):
    id: UUID
    gym_id: UUID
    member_id: UUID
    author_user_id: UUID | None
    note_type: str
    body: str
    visibility: str
    extra_data: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberOperationalProfileOut(BaseModel):
    generated_at: datetime
    member: dict
    permissions: dict
    summary: dict
    lifecycle: dict = Field(default_factory=dict)
    risk: dict
    activity: dict
    assessment: dict
    financial: dict | None = None
    commercial: dict | None = None
    communication: dict
    tasks: dict
    autopilot: dict
    next_best_action: dict
    signals: list[dict] = Field(default_factory=list)
    timeline_preview: list[dict] = Field(default_factory=list)
    data_quality_flags: list[dict] = Field(default_factory=list)
    notes: list[MemberNoteOut] = Field(default_factory=list)
