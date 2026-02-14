import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import LeadStage


class Lead(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("estimated_value >= 0", name="lead_estimated_value_non_negative"),
        CheckConstraint("acquisition_cost >= 0", name="lead_acquisition_cost_non_negative"),
        Index("ix_leads_stage_source", "stage", "source"),
        Index("ix_leads_last_contact", "last_contact_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    converted_member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    stage: Mapped[LeadStage] = mapped_column(
        Enum(LeadStage, name="lead_stage_enum", native_enum=False),
        default=LeadStage.NEW,
        nullable=False,
        index=True,
    )
    estimated_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    acquisition_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    lost_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner = relationship("User", back_populates="leads_owned")
    converted_member = relationship("Member")
    tasks = relationship("Task", back_populates="lead")
