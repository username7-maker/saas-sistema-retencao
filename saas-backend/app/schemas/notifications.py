from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InAppNotificationOut(BaseModel):
    id: UUID
    member_id: UUID | None
    user_id: UUID | None
    title: str
    message: str
    category: str
    read_at: datetime | None
    created_at: datetime
    extra_data: dict

    model_config = ConfigDict(from_attributes=True)


class MarkNotificationReadInput(BaseModel):
    read: bool = Field(default=True)
