import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NurturingSequence(Base):
    __tablename__ = "nurturing_sequences"
    __table_args__ = (
        Index("ix_nurturing_sequences_due_open", "completed", "next_send_at"),
        Index("ix_nurturing_sequences_lead", "lead_id"),
        Index("ix_nurturing_sequences_gym_due", "gym_id", "next_send_at"),
        Index("ix_nurturing_sequences_paused", "paused_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prospect_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    prospect_whatsapp: Mapped[str] = mapped_column(String(32), nullable=False)
    prospect_name: Mapped[str] = mapped_column(String(120), nullable=False)
    diagnosis_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    paused_reason: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    lead = relationship("Lead")
