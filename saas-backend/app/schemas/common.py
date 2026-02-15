from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class APIMessage(BaseModel):
    message: str


class AuditContext(BaseModel):
    ip_address: str | None = None
    user_agent: str | None = None


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class AuditLogOut(BaseModel):
    id: UUID
    action: str
    entity: str
    entity_id: UUID | None
    created_at: datetime
    details: dict

    model_config = ConfigDict(from_attributes=True)
