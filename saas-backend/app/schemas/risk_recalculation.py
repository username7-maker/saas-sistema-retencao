from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RiskRecalculationRequestOut(BaseModel):
    request_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    result: dict | None = None
