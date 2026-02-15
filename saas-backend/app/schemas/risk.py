from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import RiskLevel


class RiskAlertOut(BaseModel):
    id: UUID
    member_id: UUID
    score: int
    level: RiskLevel
    reasons: dict
    action_history: list
    automation_stage: str | None
    resolved: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskAlertResolveInput(BaseModel):
    resolution_note: str | None = Field(default=None, max_length=500)
