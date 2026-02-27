import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class BodyCompositionEvaluation(Base, TimestampMixin):
    __tablename__ = "body_composition_evaluations"
    __table_args__ = (
        CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="bce_weight_positive"),
        CheckConstraint(
            "body_fat_percent IS NULL OR (body_fat_percent >= 0 AND body_fat_percent <= 100)",
            name="bce_fat_range",
        ),
        CheckConstraint(
            "body_water_percent IS NULL OR (body_water_percent >= 0 AND body_water_percent <= 100)",
            name="bce_water_range",
        ),
        CheckConstraint("source IN ('tezewa', 'manual')", name="bce_source_valid"),
        Index("ix_bce_gym_member_date", "gym_id", "member_id", "evaluation_date"),
        Index("ix_bce_member_id", "member_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evaluation_date: Mapped[date] = mapped_column(Date, nullable=False)

    weight_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    body_fat_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    lean_mass_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    body_water_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    visceral_fat_level: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    bmi: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    basal_metabolic_rate_kcal: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    source: Mapped[str] = mapped_column(String(20), nullable=False, default="tezewa")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    member = relationship("Member", back_populates="body_composition_evaluations")
