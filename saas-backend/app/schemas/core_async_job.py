from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CoreAsyncJobStatusRead(BaseModel):
    job_id: UUID
    job_type: str
    status: str
    attempt_count: int
    max_attempts: int
    next_retry_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    queue_wait_seconds: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    result: dict[str, Any] | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class CoreAsyncJobAcceptedResponse(BaseModel):
    message: str
    job_id: UUID
    job_type: str
    status: str
