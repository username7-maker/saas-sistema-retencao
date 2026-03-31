import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin
from app.models.body_composition_constants import (
    ACTUAR_BRIDGE_DEVICE_STATUSES,
    ACTUAR_SYNC_ATTEMPT_V2_STATUSES,
    ACTUAR_SYNC_JOB_STATUSES,
    ACTUAR_SYNC_JOB_TYPES,
)
from app.utils.encryption import EncryptedString


class ActuarBridgeDevice(Base, TimestampMixin):
    __tablename__ = "actuar_bridge_devices"
    __table_args__ = (
        CheckConstraint(f"status IN {ACTUAR_BRIDGE_DEVICE_STATUSES}", name="actuar_bridge_devices_status_valid"),
        Index("ix_actuar_bridge_devices_gym_status", "gym_id", "status"),
        Index("ix_actuar_bridge_devices_gym_last_seen", "gym_id", "last_seen_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    device_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pairing")
    pairing_code_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    pairing_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auth_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    bridge_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    browser_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_job_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_job_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ActuarMemberLink(Base, TimestampMixin):
    __tablename__ = "actuar_member_links"
    __table_args__ = (
        Index("ix_actuar_member_links_gym_member", "gym_id", "member_id", unique=True),
        Index(
            "ix_actuar_member_links_gym_external_active",
            "gym_id",
            "actuar_external_id",
            unique=True,
            postgresql_where=text("actuar_external_id IS NOT NULL"),
        ),
        Index("ix_actuar_member_links_gym_active", "gym_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actuar_external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actuar_search_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    actuar_search_document: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    actuar_search_birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    match_confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    member = relationship("Member", back_populates="actuar_link")


class ActuarSyncJob(Base, TimestampMixin):
    __tablename__ = "actuar_sync_jobs"
    __table_args__ = (
        CheckConstraint(f"job_type IN {ACTUAR_SYNC_JOB_TYPES}", name="actuar_sync_jobs_job_type_valid"),
        CheckConstraint(f"status IN {ACTUAR_SYNC_JOB_STATUSES}", name="actuar_sync_jobs_status_valid"),
        Index("ix_actuar_sync_jobs_gym_status_retry", "gym_id", "status", "next_retry_at"),
        Index("ix_actuar_sync_jobs_eval_created", "body_composition_evaluation_id", "created_at"),
        Index("ix_actuar_sync_jobs_member_created", "member_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    body_composition_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("body_composition_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(40), nullable=False, default="body_composition_push")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mapped_fields_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    critical_fields_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    non_critical_fields_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    evaluation = relationship(
        "BodyCompositionEvaluation",
        foreign_keys=[body_composition_evaluation_id],
        back_populates="sync_jobs",
    )
    attempts = relationship(
        "ActuarSyncAttempt",
        back_populates="sync_job",
        cascade="all, delete-orphan",
        order_by="ActuarSyncAttempt.started_at.desc()",
    )


class ActuarSyncAttempt(Base):
    __tablename__ = "actuar_sync_attempts"
    __table_args__ = (
        CheckConstraint(f"status IN {ACTUAR_SYNC_ATTEMPT_V2_STATUSES}", name="actuar_sync_attempts_status_valid"),
        Index("ix_actuar_sync_attempts_job_started", "sync_job_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    sync_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("actuar_sync_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="started")
    action_log_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_html_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    sync_job = relationship("ActuarSyncJob", back_populates="attempts")
