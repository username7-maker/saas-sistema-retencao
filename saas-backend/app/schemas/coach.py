from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


CoachWorkspaceLane = Literal[
    "training_delivery",
    "training_feedback",
    "reassessment",
    "assessment_pending",
    "body_composition_review",
    "training_adjustment",
    "technical_attention",
]
CoachWorkspaceState = Literal["do_now", "awaiting_outcome", "done", "all"]
CoachWorkspaceShift = Literal["my_shift", "all", "overnight", "morning", "afternoon", "evening", "unassigned"]


class CoachWorkspaceEvidenceOut(BaseModel):
    label: str
    value: str


class CoachWorkspaceItemOut(BaseModel):
    source_type: str
    source_id: UUID
    member_id: UUID | None = None
    subject_name: str
    preferred_shift: str | None = None
    lane: CoachWorkspaceLane
    lane_label: str
    severity: str
    state: str
    next_action_label: str
    reason: str
    due_at: datetime | None = None
    visible_from: datetime | None = None
    context_path: str
    suggested_message: str | None = None
    technical_ladder_step: str | None = None
    technical_ladder_step_label: str | None = None
    evidence: list[CoachWorkspaceEvidenceOut] = Field(default_factory=list)
    allowed_outcomes: list[str] = Field(default_factory=list)


class CoachWorkspaceSummaryOut(BaseModel):
    total: int = 0
    do_now: int = 0
    awaiting_outcome: int = 0
    done: int = 0
    overdue: int = 0
    by_lane: dict[str, int] = Field(default_factory=dict)


class CoachWorkspaceOut(BaseModel):
    items: list[CoachWorkspaceItemOut]
    total: int
    page: int
    page_size: int
    state: CoachWorkspaceState
    shift: CoachWorkspaceShift
    summary: CoachWorkspaceSummaryOut
    generated_at: datetime
