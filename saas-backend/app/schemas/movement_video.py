from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


MovementVideoAiMode = Literal["coach_review"]


class MovementVideoAiSettingsOut(BaseModel):
    enabled: bool = False
    mode: MovementVideoAiMode = "coach_review"
    auto_send_enabled: bool = False
    require_image_consent: bool = True
    store_original_video: bool = False
    retention_days: int = 30
    max_video_mb: int = 100
    max_duration_seconds: int = 120
    allowed_media_types: list[str] = Field(default_factory=list)


class MovementVideoAiSettingsUpdate(BaseModel):
    enabled: bool | None = None
    mode: MovementVideoAiMode | None = None
    auto_send_enabled: bool | None = None
    require_image_consent: bool | None = None
    store_original_video: bool | None = None
    retention_days: int | None = Field(default=None, ge=1, le=365)
    max_video_mb: int | None = Field(default=None, ge=1, le=500)
    max_duration_seconds: int | None = Field(default=None, ge=5, le=600)
    allowed_media_types: list[str] | None = None


class MovementVideoReviewCreate(BaseModel):
    exercise_name: str = Field(min_length=2, max_length=120)
    video_asset_url: HttpUrl | None = None
    video_asset_hash: str | None = Field(default=None, max_length=128)
    media_type: str | None = Field(default=None, max_length=80)
    file_size_bytes: int | None = Field(default=None, ge=1)
    duration_seconds: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=1000)


class MovementVideoAnalyzeInput(BaseModel):
    coach_observation: str | None = Field(default=None, max_length=1500)


class MovementVideoApproveInput(BaseModel):
    coach_feedback: str = Field(min_length=3, max_length=2000)


class MovementVideoRejectInput(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class MovementVideoReviewOut(BaseModel):
    id: UUID
    gym_id: UUID
    member_id: UUID
    trainer_user_id: UUID | None = None
    exercise_name: str
    video_asset_url: str | None = None
    video_asset_hash: str | None = None
    media_type: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: int | None = None
    original_video_stored: bool = False
    status: str
    analysis_status: str
    safety_level: str
    summary: str | None = None
    detected_points: list[dict] = Field(default_factory=list)
    suggested_feedback: str | None = None
    coach_feedback: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None
    rejected_at: datetime | None = None


class MovementVideoKommoPrepareOut(BaseModel):
    review: MovementVideoReviewOut
    detail: str
    kommo_contact_id: str | None = None
    kommo_lead_id: str | None = None
    kommo_task_id: str | None = None

