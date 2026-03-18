import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.body_composition_constants import ACTUAR_SYNC_MODES, ACTUAR_SYNC_STATUSES, BODY_COMPOSITION_SOURCES


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
        CheckConstraint("ocr_confidence IS NULL OR (ocr_confidence >= 0 AND ocr_confidence <= 1)", name="bce_ocr_confidence_range"),
        CheckConstraint(f"source IN {BODY_COMPOSITION_SOURCES}", name="bce_source_valid"),
        CheckConstraint(f"actuar_sync_mode IN {ACTUAR_SYNC_MODES}", name="bce_actuar_sync_mode_valid"),
        CheckConstraint(f"actuar_sync_status IN {ACTUAR_SYNC_STATUSES}", name="bce_actuar_sync_status_valid"),
        Index("ix_bce_gym_member_date", "gym_id", "member_id", "evaluation_date"),
        Index("ix_bce_member_id", "member_id"),
        Index("ix_bce_gym_sync_status", "gym_id", "actuar_sync_status"),
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
    body_fat_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    body_fat_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    waist_hip_ratio: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    # Canonical field for modern bioimpedance exams. lean_mass_kg remains legacy compatibility only.
    fat_free_mass_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    inorganic_salt_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    protein_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    body_water_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    skeletal_muscle_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    weight_control_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    muscle_control_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    fat_control_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    total_energy_kcal: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    physical_age: Mapped[int | None] = mapped_column(nullable=True)
    health_score: Mapped[int | None] = mapped_column(nullable=True)
    # Legacy compatibility field kept for existing data and older screens.
    lean_mass_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    body_water_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    visceral_fat_level: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    bmi: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    basal_metabolic_rate_kcal: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    source: Mapped[str] = mapped_column(String(20), nullable=False, default="tezewa")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    ocr_warnings_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_manually: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    device_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    device_profile: Mapped[str | None] = mapped_column(String(60), nullable=True)
    parsed_from_image: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ocr_source_file_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    measured_ranges_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_coach_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_member_friendly_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_risk_flags_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    ai_training_focus_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actuar_sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="disabled")
    actuar_sync_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="disabled")
    actuar_external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actuar_last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actuar_last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    member = relationship("Member", back_populates="body_composition_evaluations")
    sync_attempts = relationship(
        "BodyCompositionSyncAttempt",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="BodyCompositionSyncAttempt.created_at.desc()",
    )
