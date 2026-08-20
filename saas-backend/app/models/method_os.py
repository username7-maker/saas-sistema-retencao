import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


PILLARS = ("acquisition", "sales", "post_sale")
CLIENT_STATUSES = ("prospect", "onboarding", "active", "paused", "churned")
PERSON_TYPES = ("lead", "customer", "inactive_customer", "prospect")
EVENT_SOURCES = ("manual", "import", "integration", "automation", "ai")
TASK_PRIORITIES = ("low", "medium", "high", "critical")
METHOD_TASK_STATUSES = ("open", "in_progress", "done", "dismissed", "expired")
ACTION_TYPES = ("whatsapp", "call", "email", "in_person", "internal_note", "other")
ACTION_RESULTS = ("no_response", "responded", "scheduled", "bought", "returned", "renewed", "lost", "dismissed", "other")
REPORT_TYPES = ("weekly", "monthly", "pilot", "internal")
IMPORT_BATCH_STATUSES = ("previewed", "imported", "failed")
IMPORT_BATCH_TYPES = ("people", "events")


class Segment(Base, TimestampMixin):
    __tablename__ = "method_segments"
    __table_args__ = (
        Index("ix_method_segments_slug_unique", "slug", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    default_entry_pillar: Mapped[str] = mapped_column(
        Enum(*PILLARS, name="method_pillar_enum", native_enum=False),
        nullable=False,
        default="post_sale",
    )

    playbook = relationship("SegmentPlaybook", back_populates="segment", cascade="all, delete-orphan", uselist=False)


class SegmentPlaybook(Base, TimestampMixin):
    __tablename__ = "method_segment_playbooks"
    __table_args__ = (
        Index("ix_method_segment_playbooks_segment_unique", "segment_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    segment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("method_segments.id", ondelete="CASCADE"), nullable=False)
    channels_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    qualification_questions_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    risk_opportunity_signals_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    message_templates_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    success_metrics_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    segment = relationship("Segment", back_populates="playbook")


class ClientMethodConfig(Base, TimestampMixin):
    __tablename__ = "method_client_configs"
    __table_args__ = (
        Index("ix_method_client_configs_gym_unique", "gym_id", unique=True),
        Index("ix_method_client_configs_segment", "segment_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("method_segments.id", ondelete="SET NULL"), nullable=True)
    active_pillars_json: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {"acquisition": True, "sales": True, "post_sale": True},
        nullable=False,
    )
    entry_pillar: Mapped[str] = mapped_column(
        Enum(*PILLARS, name="method_pillar_enum", native_enum=False),
        nullable=False,
        default="post_sale",
    )
    toolkit_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    baseline_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    success_criteria_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    cadence_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    segment = relationship("Segment")


class Person(Base, TimestampMixin):
    __tablename__ = "method_people"
    __table_args__ = (
        Index("ix_method_people_gym_type_status", "gym_id", "person_type", "status"),
        Index("ix_method_people_gym_phone", "gym_id", "phone"),
        Index("ix_method_people_gym_external", "gym_id", "external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    person_type: Mapped[str] = mapped_column(
        Enum(*PERSON_TYPES, name="method_person_type_enum", native_enum=False),
        nullable=False,
        default="lead",
    )
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="active")
    source_channel: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    events = relationship("OperationalEvent", back_populates="person")
    tasks = relationship("OperationalTask", back_populates="person")


class OperationalEvent(Base):
    __tablename__ = "method_operational_events"
    __table_args__ = (
        Index("ix_method_events_gym_pillar_type", "gym_id", "pillar", "event_type"),
        Index("ix_method_events_gym_occurred", "gym_id", "occurred_at"),
        Index("ix_method_events_person", "person_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("method_people.id", ondelete="SET NULL"), nullable=True)
    pillar: Mapped[str] = mapped_column(Enum(*PILLARS, name="method_pillar_enum", native_enum=False), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_source: Mapped[str] = mapped_column(
        Enum(*EVENT_SOURCES, name="method_event_source_enum", native_enum=False),
        nullable=False,
        default="manual",
    )
    event_payload_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    person = relationship("Person", back_populates="events")
    tasks = relationship("OperationalTask", back_populates="event")


class OperationalTask(Base, TimestampMixin):
    __tablename__ = "method_operational_tasks"
    __table_args__ = (
        Index("ix_method_tasks_gym_status_due", "gym_id", "status", "due_date"),
        Index("ix_method_tasks_gym_pillar", "gym_id", "pillar"),
        Index("ix_method_tasks_person", "person_id"),
        Index("ix_method_tasks_event", "event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("method_people.id", ondelete="SET NULL"), nullable=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("method_operational_events.id", ondelete="SET NULL"), nullable=True)
    pillar: Mapped[str] = mapped_column(Enum(*PILLARS, name="method_pillar_enum", native_enum=False), nullable=False)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_role: Mapped[str] = mapped_column(String(80), nullable=False, default="operacao")
    assigned_to: Mapped[str | None] = mapped_column(String(120), nullable=True)
    priority: Mapped[str] = mapped_column(
        Enum(*TASK_PRIORITIES, name="method_task_priority_enum", native_enum=False),
        nullable=False,
        default="medium",
    )
    status: Mapped[str] = mapped_column(
        Enum(*METHOD_TASK_STATUSES, name="method_task_status_enum", native_enum=False),
        nullable=False,
        default="open",
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suggested_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    wa_me_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    dismissal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ai_metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    person = relationship("Person", back_populates="tasks")
    event = relationship("OperationalEvent", back_populates="tasks")
    actions = relationship("HumanAction", back_populates="task")
    outcomes = relationship("Outcome", back_populates="task")


class HumanAction(Base):
    __tablename__ = "method_human_actions"
    __table_args__ = (
        Index("ix_method_actions_gym_created", "gym_id", "created_at"),
        Index("ix_method_actions_task", "task_id"),
        Index("ix_method_actions_person", "person_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("method_people.id", ondelete="SET NULL"), nullable=True)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("method_operational_tasks.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(Enum(*ACTION_TYPES, name="method_action_type_enum", native_enum=False), nullable=False)
    action_summary: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Enum(*ACTION_RESULTS, name="method_action_result_enum", native_enum=False), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    task = relationship("OperationalTask", back_populates="actions")


class Outcome(Base):
    __tablename__ = "method_outcomes"
    __table_args__ = (
        Index("ix_method_outcomes_gym_type_measured", "gym_id", "outcome_type", "measured_at"),
        Index("ix_method_outcomes_task", "task_id"),
        Index("ix_method_outcomes_action", "action_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("method_people.id", ondelete="SET NULL"), nullable=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("method_operational_tasks.id", ondelete="SET NULL"), nullable=True)
    action_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("method_human_actions.id", ondelete="SET NULL"), nullable=True)
    outcome_type: Mapped[str] = mapped_column(String(80), nullable=False)
    value_numeric: Mapped[float | None] = mapped_column(nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    task = relationship("OperationalTask", back_populates="outcomes")


class MethodReport(Base):
    __tablename__ = "method_reports"
    __table_args__ = (
        Index("ix_method_reports_gym_type_period", "gym_id", "report_type", "period_start", "period_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(Enum(*REPORT_TYPES, name="method_report_type_enum", native_enum=False), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    recommendations_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ImportBatch(Base):
    __tablename__ = "method_import_batches"
    __table_args__ = (
        Index("ix_method_import_batches_gym_type_created", "gym_id", "import_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    import_type: Mapped[str] = mapped_column(Enum(*IMPORT_BATCH_TYPES, name="method_import_type_enum", native_enum=False), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(Enum(*IMPORT_BATCH_STATUSES, name="method_import_status_enum", native_enum=False), nullable=False)
    column_mapping_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    error_report_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
