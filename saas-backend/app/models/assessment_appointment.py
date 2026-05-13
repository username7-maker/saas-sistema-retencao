import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class AssessmentAppointment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "assessment_appointments"
    __table_args__ = (
        UniqueConstraint("gym_id", "external_reference", name="uq_assessment_appointments_gym_external_reference"),
        Index("ix_assessment_appointments_gym_scheduled", "gym_id", "scheduled_at"),
        Index("ix_assessment_appointments_member_scheduled", "member_id", "scheduled_at"),
        Index("ix_assessment_appointments_gym_status", "gym_id", "status"),
        Index("ix_assessment_appointments_gym_payment", "gym_id", "payment_status"),
        Index("ix_assessment_appointments_evaluator", "evaluator_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluator_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(60), default="physical_assessment", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="scheduled", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(24), default="unknown", nullable=False)
    evaluator_name_raw: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(60), default="manual", nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    member = relationship("Member", back_populates="assessment_appointments")
    evaluator_user = relationship("User", foreign_keys=[evaluator_user_id])
