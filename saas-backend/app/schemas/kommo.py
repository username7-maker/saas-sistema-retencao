from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


KommoSendDomain = Literal[
    "retention",
    "onboarding",
    "assessment",
    "body_composition",
    "finance",
    "sales",
    "student_ai",
    "support",
]


class KommoSendMessageRequest(BaseModel):
    member_id: UUID | None = None
    lead_id: UUID | None = None
    domain: KommoSendDomain
    message_text: str = Field(min_length=1, max_length=3000)
    source_type: str = Field(min_length=1, max_length=80)
    source_id: UUID | str
    pdf_kind: Literal["summary", "technical"] | None = None
    pdf_delivery_mode: Literal["native_file_required", "native_file_preferred", "link_only"] | None = None


class KommoSendMessageResponse(BaseModel):
    status: str
    delivery_mode: str
    detail: str | None = None
    member_id: UUID | None = None
    local_lead_id: UUID | None = None
    source_type: str
    source_id: str
    domain: str
    lead_id: str | None = None
    contact_id: str | None = None
    task_id: str | None = None
    message_log_id: UUID | None = None
    salesbot_id: str | None = None
    pdf_url: str | None = None
    kommo_file_uuid: str | None = None
    file_upload_status: str | None = None
    file_attach_status: str | None = None
    pdf_delivery_mode: str | None = None
    fallback_available: bool = False


class KommoNativeFileUploadTestRequest(BaseModel):
    lead_id: str | None = Field(default=None, max_length=40)


class KommoNativeFileUploadTestResponse(BaseModel):
    success: bool
    message: str
    file_uuid: str | None = None
    upload_status: str | None = None
    attach_status: str | None = None
    detail: str | None = None
