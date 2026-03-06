from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ObjectionResponseOut(BaseModel):
    id: UUID
    gym_id: UUID | None
    trigger_keywords: list[str]
    objection_summary: str
    response_template: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ObjectionResponseUpdate(BaseModel):
    trigger_keywords: list[str] | None = Field(default=None, min_length=1)
    objection_summary: str | None = Field(default=None, min_length=3, max_length=2000)
    response_template: str | None = Field(default=None, min_length=3, max_length=4000)
    is_active: bool | None = None
