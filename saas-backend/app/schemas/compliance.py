from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ConsentType = Literal["lgpd", "communication", "image", "contract", "terms"]
ConsentStatus = Literal["accepted", "revoked", "expired"]


class MemberConsentRecordCreate(BaseModel):
    consent_type: ConsentType
    status: ConsentStatus = "accepted"
    source: str = Field(default="manual", min_length=2, max_length=80)
    document_title: str | None = Field(default=None, max_length=160)
    document_version: str | None = Field(default=None, max_length=80)
    evidence_ref: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    signed_at: datetime | None = None
    expires_at: datetime | None = None
    extra_data: dict[str, Any] = Field(default_factory=dict)


class MemberConsentRecordOut(BaseModel):
    id: UUID
    gym_id: UUID
    member_id: UUID
    consent_type: str
    status: str
    source: str
    document_title: str | None
    document_version: str | None
    evidence_ref: str | None
    notes: str | None
    signed_at: datetime | None
    revoked_at: datetime | None
    expires_at: datetime | None
    extra_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberConsentCurrentOut(BaseModel):
    consent_type: str
    status: str
    accepted: bool
    source: str | None = None
    document_title: str | None = None
    document_version: str | None = None
    signed_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None
    record_id: UUID | None = None
    missing: bool = False
    expired: bool = False


class MemberConsentSummaryOut(BaseModel):
    member_id: UUID
    current: list[MemberConsentCurrentOut]
    records: list[MemberConsentRecordOut]
    missing: list[str] = Field(default_factory=list)
    expired: list[str] = Field(default_factory=list)
    updated_at: datetime
