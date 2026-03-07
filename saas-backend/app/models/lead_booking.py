import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class LeadBooking(Base, TimestampMixin):
    __tablename__ = "lead_bookings"
    __table_args__ = (
        Index("ix_lead_bookings_gym_scheduled", "gym_id", "scheduled_for"),
        Index("ix_lead_bookings_lead_status", "lead_id", "status"),
        Index("ix_lead_bookings_status_reminder", "status", "reminder_sent_at"),
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
    provider_name: Mapped[str | None] = mapped_column(String(40), nullable=True, default=None)
    provider_booking_id: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None, index=True)
    prospect_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prospect_email: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None, index=True)
    prospect_whatsapp: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="confirmed", server_default="confirmed")
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    extra_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    lead = relationship("Lead", back_populates="bookings")
