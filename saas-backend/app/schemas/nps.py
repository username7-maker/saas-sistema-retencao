from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import NPSSentiment, NPSTrigger


class NPSResponseCreate(BaseModel):
    member_id: UUID | None = None
    score: int = Field(ge=0, le=10)
    comment: str | None = Field(default=None, max_length=2000)
    trigger: NPSTrigger


class NPSResponseOut(BaseModel):
    id: UUID
    member_id: UUID | None
    score: int
    comment: str | None
    sentiment: NPSSentiment
    sentiment_summary: str | None
    trigger: NPSTrigger
    response_date: datetime

    model_config = ConfigDict(from_attributes=True)


class NPSEvolutionPoint(BaseModel):
    month: str
    average_score: float
    responses: int
