import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class FinancialEntry(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "financial_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_type in ('receivable', 'payable', 'cash_in', 'cash_out')",
            name="financial_entry_type_check",
        ),
        CheckConstraint(
            "status in ('open', 'paid', 'overdue', 'cancelled')",
            name="financial_entry_status_check",
        ),
        CheckConstraint("amount >= 0", name="financial_entry_amount_non_negative"),
        Index("ix_financial_entries_gym_type_status", "gym_id", "entry_type", "status"),
        Index("ix_financial_entries_gym_due", "gym_id", "due_date"),
        Index("ix_financial_entries_gym_occurred", "gym_id", "occurred_at"),
        Index("ix_financial_entries_member", "member_id"),
        Index("ix_financial_entries_lead", "lead_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
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
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="geral")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    gym = relationship("Gym")
    member = relationship("Member")
    lead = relationship("Lead")
    created_by_user = relationship("User")
