import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import TaskPriority, TaskStatus


class Task(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_status_assigned", "status", "assigned_to_user_id"),
        Index("ix_tasks_due_status", "due_date", "status"),
        Index("ix_tasks_kanban_column", "kanban_column"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority_enum", native_enum=False),
        default=TaskPriority.MEDIUM,
        nullable=False,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status_enum", native_enum=False),
        default=TaskStatus.TODO,
        nullable=False,
        index=True,
    )
    kanban_column: Mapped[str] = mapped_column(String(32), default=TaskStatus.TODO.value, nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suggested_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    member = relationship("Member", back_populates="tasks")
    lead = relationship("Lead", back_populates="tasks")
    assigned_user = relationship("User", back_populates="tasks_assigned")
