from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ActuarBridgeDeviceStatus = Literal["pairing", "online", "offline", "revoked"]


class ActuarBridgeDeviceRead(BaseModel):
    id: UUID
    gym_id: UUID
    device_name: str
    status: ActuarBridgeDeviceStatus
    bridge_version: str | None = None
    browser_name: str | None = None
    paired_at: datetime | None = None
    last_seen_at: datetime | None = None
    last_job_claimed_at: datetime | None = None
    last_job_completed_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    revoked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActuarBridgePairingCodeRead(BaseModel):
    device_id: UUID
    pairing_code: str
    expires_at: datetime


class ActuarBridgePairRequest(BaseModel):
    pairing_code: str = Field(min_length=6, max_length=32)
    device_name: str = Field(min_length=3, max_length=120)
    bridge_version: str | None = Field(default=None, max_length=40)
    browser_name: str | None = Field(default=None, max_length=80)


class ActuarBridgePairResponse(BaseModel):
    device_token: str
    api_base_url: str | None = None
    poll_interval_seconds: int
    device: ActuarBridgeDeviceRead


class ActuarBridgeHeartbeatResponse(BaseModel):
    device: ActuarBridgeDeviceRead
    poll_interval_seconds: int


class ActuarBridgeClaimedJobRead(BaseModel):
    job_id: UUID
    evaluation_id: UUID
    member_id: UUID
    sync_mode: str
    member_name: str
    member_email: str | None = None
    member_birthdate: date | None = None
    member_document: str | None = None
    actuar_external_id: str | None = None
    payload_json: dict | None = None
    mapped_fields_json: dict | None = None
    critical_fields_json: list | None = None
    non_critical_fields_json: list | None = None
    manual_summary_text: str


class ActuarBridgeJobCompleteInput(BaseModel):
    external_id: str | None = Field(default=None, max_length=120)
    action_log_json: list[dict] | list | None = None
    note: str | None = Field(default=None, max_length=500)


class ActuarBridgeJobFailInput(BaseModel):
    error_code: str = Field(min_length=3, max_length=80)
    error_message: str = Field(min_length=3, max_length=1000)
    retryable: bool = False
    manual_fallback: bool = True
    action_log_json: list[dict] | list | None = None
