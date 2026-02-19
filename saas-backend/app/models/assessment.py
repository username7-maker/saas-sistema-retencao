import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Assessment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint("assessment_number >= 1", name="assessment_number_positive"),
        CheckConstraint("height_cm IS NULL OR height_cm > 0", name="assessment_height_positive"),
        CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="assessment_weight_positive"),
        CheckConstraint("bmi IS NULL OR bmi > 0", name="assessment_bmi_positive"),
        CheckConstraint("body_fat_pct IS NULL OR (body_fat_pct >= 0 AND body_fat_pct <= 100)", name="assessment_body_fat_range"),
        CheckConstraint("strength_score IS NULL OR (strength_score >= 0 AND strength_score <= 100)", name="assessment_strength_range"),
        CheckConstraint("flexibility_score IS NULL OR (flexibility_score >= 0 AND flexibility_score <= 100)", name="assessment_flexibility_range"),
        CheckConstraint("cardio_score IS NULL OR (cardio_score >= 0 AND cardio_score <= 100)", name="assessment_cardio_range"),
        UniqueConstraint("member_id", "assessment_number", name="uq_assessment_member_number"),
        Index("ix_assessments_gym_date", "gym_id", "assessment_date"),
        Index("ix_assessments_member_date_desc", "member_id", "assessment_date"),
        Index("ix_assessments_due_date", "next_assessment_due"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluator_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    assessment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    assessment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_assessment_due: Mapped[date | None] = mapped_column(Date, nullable=True)

    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    bmi: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    body_fat_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    lean_mass_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    waist_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    hip_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    chest_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    arm_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    thigh_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    resting_hr: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    blood_pressure_systolic: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    blood_pressure_diastolic: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    vo2_estimated: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    strength_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    flexibility_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    cardio_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_risk_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    member = relationship("Member", back_populates="assessments")
    evaluator = relationship("User", foreign_keys=[evaluator_id])
    goals = relationship("MemberGoal", back_populates="assessment")
    training_plans = relationship("TrainingPlan", back_populates="assessment")


class MemberGoal(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "member_goals"
    __table_args__ = (
        CheckConstraint("target_value IS NULL OR target_value >= 0", name="member_goal_target_non_negative"),
        CheckConstraint("current_value >= 0", name="member_goal_current_non_negative"),
        CheckConstraint("progress_pct >= 0 AND progress_pct <= 100", name="member_goal_progress_range"),
        Index("ix_member_goals_gym_member_status", "gym_id", "member_id", "status"),
        Index("ix_member_goals_member_target_date", "member_id", "target_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(60), default="general", nullable=False)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    current_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    progress_pct: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    achieved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    achieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    member = relationship("Member", back_populates="member_goals")
    assessment = relationship("Assessment", back_populates="goals")


class TrainingPlan(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "training_plans"
    __table_args__ = (
        CheckConstraint("sessions_per_week >= 1 AND sessions_per_week <= 14", name="training_plan_sessions_range"),
        Index("ix_training_plans_gym_member_active", "gym_id", "member_id", "is_active"),
        Index("ix_training_plans_member_start_date", "member_id", "start_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    sessions_per_week: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    split_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    plan_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    member = relationship("Member", back_populates="training_plans")
    assessment = relationship("Assessment", back_populates="training_plans")
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class MemberConstraints(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "member_constraints"
    __table_args__ = (
        UniqueConstraint("member_id", name="uq_member_constraints_member"),
        Index("ix_member_constraints_gym_member", "gym_id", "member_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)

    medical_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    injuries: Mapped[str | None] = mapped_column(Text, nullable=True)
    medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    contraindications: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_training_times: Mapped[str | None] = mapped_column(String(120), nullable=True)
    restrictions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    member = relationship("Member", back_populates="member_constraints")
