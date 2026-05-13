import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MovementVideoReview(Base, TimestampMixin):
    __tablename__ = "movement_video_reviews"
    __table_args__ = (
        Index("ix_movement_video_reviews_gym_member_created", "gym_id", "member_id", "created_at"),
        Index("ix_movement_video_reviews_gym_status", "gym_id", "status"),
        Index("ix_movement_video_reviews_trainer_status", "trainer_user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    trainer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    exercise_name: Mapped[str] = mapped_column(String(120), nullable=False)
    video_asset_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_asset_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_video_stored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review", index=True)
    analysis_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started", index=True)
    safety_level: Mapped[str] = mapped_column(String(32), nullable=False, default="coach_review")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_points: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    suggested_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    coach_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocked_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    member = relationship("Member")
    trainer_user = relationship("User")

