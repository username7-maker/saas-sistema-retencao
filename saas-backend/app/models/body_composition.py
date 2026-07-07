import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.body_composition_constants import (
    ACTUAR_SYNC_MODES,
    ACTUAR_SYNC_STATUSES,
    BODY_COMPOSITION_SOURCES,
    BODY_FAT_CONFIDENCES,
    BODY_FAT_MEASUREMENT_SOURCES,
    BODY_FAT_METHODS,
    BODY_FAT_USED_SOURCES,
    PREFERRED_BODY_FAT_SOURCES,
)


class BodyCompositionEvaluation(Base, TimestampMixin):
    __tablename__ = "body_composition_evaluations"
    __table_args__ = (
        CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="bce_weight_positive"),
        CheckConstraint(
            "body_fat_percent IS NULL OR (body_fat_percent >= 0 AND body_fat_percent <= 100)",
            name="bce_fat_range",
        ),
        CheckConstraint(
            "body_fat_bioimpedance_percent IS NULL OR "
            "(body_fat_bioimpedance_percent >= 0 AND body_fat_bioimpedance_percent <= 100)",
            name="bce_body_fat_bioimpedance_range",
        ),
        CheckConstraint(
            "body_fat_anthropometric_percent IS NULL OR "
            "(body_fat_anthropometric_percent >= 0 AND body_fat_anthropometric_percent <= 100)",
            name="bce_body_fat_anthropometric_range",
        ),
        CheckConstraint(
            "body_fat_manual_override_percent IS NULL OR "
            "(body_fat_manual_override_percent >= 0 AND body_fat_manual_override_percent <= 100)",
            name="bce_body_fat_manual_override_range",
        ),
        CheckConstraint(
            "body_fat_used_percent IS NULL OR (body_fat_used_percent >= 0 AND body_fat_used_percent <= 100)",
            name="bce_body_fat_used_range",
        ),
        CheckConstraint(f"measurement_source IS NULL OR measurement_source IN {BODY_FAT_MEASUREMENT_SOURCES}", name="bce_measurement_source_valid"),
        CheckConstraint(f"preferred_body_fat_source IS NULL OR preferred_body_fat_source IN {PREFERRED_BODY_FAT_SOURCES}", name="bce_preferred_body_fat_source_valid"),
        CheckConstraint(f"body_fat_used_source IS NULL OR body_fat_used_source IN {BODY_FAT_USED_SOURCES}", name="bce_body_fat_used_source_valid"),
        CheckConstraint(f"body_fat_method IS NULL OR body_fat_method IN {BODY_FAT_METHODS}", name="bce_body_fat_method_valid"),
        CheckConstraint(f"body_fat_confidence IS NULL OR body_fat_confidence IN {BODY_FAT_CONFIDENCES}", name="bce_body_fat_confidence_valid"),
        CheckConstraint(
            "body_water_percent IS NULL OR (body_water_percent >= 0 AND body_water_percent <= 100)",
            name="bce_water_range",
        ),
        CheckConstraint("ocr_confidence IS NULL OR (ocr_confidence >= 0 AND ocr_confidence <= 1)", name="bce_ocr_confidence_range"),
        CheckConstraint(
            "parsing_confidence IS NULL OR (parsing_confidence >= 0 AND parsing_confidence <= 1)",
            name="bce_parsing_confidence_range",
        ),
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
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(10), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    weight_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    body_fat_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    # Legacy/raw compatibility field. Product surfaces must use body_fat_used_percent.
    body_fat_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_bioimpedance_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_anthropometric_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_manual_override_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_used_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_used_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    body_fat_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    body_fat_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    body_fat_range_min: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_range_max: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    preferred_body_fat_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    measurement_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fat_mass_estimated_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    lean_mass_estimated_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
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
    neck_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    shoulders_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    chest_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    abdomen_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    hip_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    right_arm_relaxed_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    left_arm_relaxed_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    right_arm_flexed_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    left_arm_flexed_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    right_thigh_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    left_thigh_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    right_calf_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    left_calf_cm: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    anthropometry_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_fat_manual_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    body_fat_manual_review_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anthropometry_review_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    measurement_protocol: Mapped[str | None] = mapped_column(String(60), nullable=True)
    evaluated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    source: Mapped[str] = mapped_column(String(20), nullable=False, default="tezewa")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    parsing_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    ocr_warnings_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    data_quality_flags_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_manually: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    device_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    device_profile: Mapped[str | None] = mapped_column(String(60), nullable=True)
    parsed_from_image: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ocr_source_file_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    import_batch_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    measured_ranges_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_coach_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_member_friendly_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_risk_flags_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    ai_training_focus_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actuar_sync_status: Mapped[str] = mapped_column(String(30), nullable=False, default="saved")
    actuar_sync_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="disabled")
    actuar_external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actuar_last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actuar_last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_required_for_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sync_last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sync_last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    actuar_sync_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("actuar_sync_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )

    member = relationship("Member", back_populates="body_composition_evaluations")
    sync_attempts = relationship(
        "BodyCompositionSyncAttempt",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="BodyCompositionSyncAttempt.created_at.desc()",
    )
    current_sync_job = relationship(
        "ActuarSyncJob",
        foreign_keys=[actuar_sync_job_id],
        post_update=True,
    )
    sync_jobs = relationship(
        "ActuarSyncJob",
        foreign_keys="ActuarSyncJob.body_composition_evaluation_id",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="ActuarSyncJob.created_at.desc()",
    )

    @property
    def training_ready(self) -> bool:
        return self.actuar_sync_status == "synced_to_actuar"
