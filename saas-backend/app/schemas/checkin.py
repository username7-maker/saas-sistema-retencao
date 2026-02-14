from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import CheckinSource


class CheckinCreate(BaseModel):
    member_id: UUID
    checkin_at: datetime
    source: CheckinSource = CheckinSource.MANUAL
    extra_data: dict = Field(default_factory=dict)


class CheckinOut(BaseModel):
    id: UUID
    member_id: UUID
    checkin_at: datetime
    source: CheckinSource
    hour_bucket: int
    weekday: int

    class Config:
        from_attributes = True
