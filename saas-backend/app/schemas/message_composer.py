from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MessageTemplateOut(BaseModel):
    key: str
    domain: str
    channel: str
    objective: str
    content: str
    default_content: str
    allowed_variables: list[str]
    required_variables: list[str]
    version: str
    active: bool
    origin: str


class MessageTemplateUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MessageTemplatePreviewIn(BaseModel):
    variables: dict[str, str | int | float | None] = Field(default_factory=dict)


class MessageTemplatePreviewOut(BaseModel):
    template_key: str
    message: str
    origin: str


class MessageImproveIn(BaseModel):
    source_type: str = Field(min_length=2, max_length=40)
    source_id: UUID | None = None
    template_key: str = Field(min_length=3, max_length=100)
    objective: str = Field(min_length=3, max_length=280)
    idempotency_key: str = Field(min_length=8, max_length=180)


class MessageCompositionOut(BaseModel):
    request_id: UUID
    base_message: str
    improved_message: str | None
    model: str | None
    prompt_version: str | None
    origin: str
    warnings: list[str]
    status: str
    created_at: datetime


class MessageComposerMetricsOut(BaseModel):
    requests: int
    applied: int
    discarded: int
    pending_preview: int
    fallback_count: int
    input_tokens: int
    output_tokens: int
    application_rate: float
