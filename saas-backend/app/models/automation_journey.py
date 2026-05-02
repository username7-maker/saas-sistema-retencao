import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AutomationJourney(Base, TimestampMixin):
    __tablename__ = "automation_journeys"
    __table_args__ = (
        Index("ix_automation_journeys_gym_active", "gym_id", "is_active"),
        Index("ix_automation_journeys_gym_domain", "gym_id", "domain"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entry_trigger: Mapped[str] = mapped_column(String(80), nullable=False)
    audience_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    exit_conditions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    metrics_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    steps = relationship("AutomationJourneyStep", back_populates="journey", cascade="all, delete-orphan")
    enrollments = relationship("AutomationJourneyEnrollment", back_populates="journey", cascade="all, delete-orphan")
    events = relationship("AutomationJourneyEvent", back_populates="journey", cascade="all, delete-orphan")


class AutomationJourneyStep(Base, TimestampMixin):
    __tablename__ = "automation_journey_steps"
    __table_args__ = (
        UniqueConstraint("journey_id", "step_order", name="uq_automation_journey_step_order"),
        Index("ix_automation_journey_steps_gym_journey", "gym_id", "journey_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_journeys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    delay_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delay_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    condition_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    action_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    owner_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preferred_shift: Mapped[str | None] = mapped_column(String(24), nullable=True)
    template_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fallback_mode: Mapped[str] = mapped_column(String(40), default="manual_required", nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)

    journey = relationship("AutomationJourney", back_populates="steps")
    enrollments = relationship("AutomationJourneyEnrollment", back_populates="current_step")
    events = relationship("AutomationJourneyEvent", back_populates="step")


class AutomationJourneyEnrollment(Base, TimestampMixin):
    __tablename__ = "automation_journey_enrollments"
    __table_args__ = (
        UniqueConstraint("journey_id", "member_id", name="uq_automation_journey_member"),
        UniqueConstraint("journey_id", "lead_id", name="uq_automation_journey_lead"),
        Index("ix_automation_journey_enrollments_gym_state", "gym_id", "state"),
        Index("ix_automation_journey_enrollments_due", "next_step_due_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_journeys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    current_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_journey_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    state: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    current_step_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_step_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    exit_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    journey = relationship("AutomationJourney", back_populates="enrollments")
    current_step = relationship("AutomationJourneyStep", back_populates="enrollments")
    events = relationship("AutomationJourneyEvent", back_populates="enrollment", cascade="all, delete-orphan")
    member = relationship("Member")
    lead = relationship("Lead")


class AutomationJourneyEvent(Base):
    __tablename__ = "automation_journey_events"
    __table_args__ = (
        Index("ix_automation_journey_events_gym_created", "gym_id", "created_at"),
        Index("ix_automation_journey_events_enrollment_created", "enrollment_id", "created_at"),
        Index("ix_automation_journey_events_type_created", "event_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_journeys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_journey_enrollments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("automation_journey_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    outcome: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    journey = relationship("AutomationJourney", back_populates="events")
    enrollment = relationship("AutomationJourneyEnrollment", back_populates="events")
    step = relationship("AutomationJourneyStep", back_populates="events")
