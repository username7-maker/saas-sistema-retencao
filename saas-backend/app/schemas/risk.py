from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

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

    class Config:
        from_attributes = True
