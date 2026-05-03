import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AutopilotEvent(Base):
    __tablename__ = "autopilot_events"
    __table_args__ = (
        UniqueConstraint("gym_id", "deduplication_key", name="uq_autopilot_events_gym_dedupe"),
        Index("ix_autopilot_events_gym_created", "gym_id", "created_at"),
        Index("ix_autopilot_events_gym_status", "gym_id", "processing_status"),
        Index("ix_autopilot_events_type_created", "event_type", "created_at"),
        Index("ix_autopilot_events_member_created", "member_id", "created_at"),
        Index("ix_autopilot_events_lead_created", "lead_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="system")
    member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    autopilot_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("autopilot_actions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, server_default="{}")
    deduplication_key: Mapped[str | None] = mapped_column(String(180), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    created_by_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    raw_payload_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AutopilotAction(Base, TimestampMixin):
    __tablename__ = "autopilot_actions"
    __table_args__ = (
        Index("ix_autopilot_actions_gym_status", "gym_id", "status"),
        Index("ix_autopilot_actions_policy_status", "policy_key", "status"),
        Index("ix_autopilot_actions_member_status", "member_id", "status"),
        Index("ix_autopilot_actions_lead_status", "lead_id", "status"),
        Index("ix_autopilot_actions_scheduled", "scheduled_for", "status"),
        Index("ix_autopilot_actions_timeout", "timeout_at", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    action_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned", index=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    related_task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="none")
    template_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    message_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timeout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(60), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, server_default="{}")

    events = relationship("AutopilotEvent", backref="autopilot_action", foreign_keys=[AutopilotEvent.autopilot_action_id])


class GymAutopilotSettings(Base, TimestampMixin):
    __tablename__ = "gym_autopilot_settings"
    __table_args__ = (Index("ix_gym_autopilot_settings_gym", "gym_id", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    autopilot_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    autopilot_auto_close_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    autopilot_auto_send_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    retention_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    finance_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    sales_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    onboarding_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    assessment_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    nps_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    business_hours_start: Mapped[str] = mapped_column(String(5), nullable=False, default="08:00", server_default="08:00")
    business_hours_end: Mapped[str] = mapped_column(String(5), nullable=False, default="20:00", server_default="20:00")
    max_auto_messages_per_member_per_week: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")
    max_auto_messages_per_lead_per_week: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    max_auto_actions_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    max_human_tasks_created_by_autopilot_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=25, server_default="25")
    default_timeout_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=48, server_default="48")
    human_recent_activity_cooldown_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24, server_default="24")
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, server_default="{}")
