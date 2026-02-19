"""add assessment tables

Revision ID: 20260217_0007
Revises: 20260217_0006
Create Date: 2026-02-17 15:20:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260217_0007"
down_revision = "20260217_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assessment_number", sa.Integer(), nullable=False),
        sa.Column("assessment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_assessment_due", sa.Date(), nullable=True),
        sa.Column("height_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("bmi", sa.Numeric(6, 2), nullable=True),
        sa.Column("body_fat_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("lean_mass_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("waist_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("hip_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("chest_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("arm_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("thigh_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("resting_hr", sa.SmallInteger(), nullable=True),
        sa.Column("blood_pressure_systolic", sa.SmallInteger(), nullable=True),
        sa.Column("blood_pressure_diastolic", sa.SmallInteger(), nullable=True),
        sa.Column("vo2_estimated", sa.Numeric(6, 2), nullable=True),
        sa.Column("strength_score", sa.SmallInteger(), nullable=True),
        sa.Column("flexibility_score", sa.SmallInteger(), nullable=True),
        sa.Column("cardio_score", sa.SmallInteger(), nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("ai_analysis", sa.Text(), nullable=True),
        sa.Column("ai_recommendations", sa.Text(), nullable=True),
        sa.Column("ai_risk_flags", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("assessment_number >= 1", name="ck_assessments_assessment_number_positive"),
        sa.CheckConstraint("height_cm IS NULL OR height_cm > 0", name="ck_assessments_assessment_height_positive"),
        sa.CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="ck_assessments_assessment_weight_positive"),
        sa.CheckConstraint("bmi IS NULL OR bmi > 0", name="ck_assessments_assessment_bmi_positive"),
        sa.CheckConstraint(
            "body_fat_pct IS NULL OR (body_fat_pct >= 0 AND body_fat_pct <= 100)",
            name="ck_assessments_assessment_body_fat_range",
        ),
        sa.CheckConstraint(
            "strength_score IS NULL OR (strength_score >= 0 AND strength_score <= 100)",
            name="ck_assessments_assessment_strength_range",
        ),
        sa.CheckConstraint(
            "flexibility_score IS NULL OR (flexibility_score >= 0 AND flexibility_score <= 100)",
            name="ck_assessments_assessment_flexibility_range",
        ),
        sa.CheckConstraint(
            "cardio_score IS NULL OR (cardio_score >= 0 AND cardio_score <= 100)",
            name="ck_assessments_assessment_cardio_range",
        ),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evaluator_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("member_id", "assessment_number", name="uq_assessment_member_number"),
    )

    op.create_table(
        "member_constraints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("medical_conditions", sa.Text(), nullable=True),
        sa.Column("injuries", sa.Text(), nullable=True),
        sa.Column("medications", sa.Text(), nullable=True),
        sa.Column("contraindications", sa.Text(), nullable=True),
        sa.Column("preferred_training_times", sa.String(length=120), nullable=True),
        sa.Column("restrictions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("member_id", name="uq_member_constraints_member"),
    )

    op.create_table(
        "member_goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=60), nullable=False, server_default=sa.text("'general'")),
        sa.Column("target_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("current_value", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("progress_pct", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("achieved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("achieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("target_value IS NULL OR target_value >= 0", name="ck_member_goals_member_goal_target_non_negative"),
        sa.CheckConstraint("current_value >= 0", name="ck_member_goals_member_goal_current_non_negative"),
        sa.CheckConstraint("progress_pct >= 0 AND progress_pct <= 100", name="ck_member_goals_member_goal_progress_range"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "training_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("sessions_per_week", sa.SmallInteger(), nullable=False, server_default=sa.text("3")),
        sa.Column("split_type", sa.String(length=60), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("plan_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "sessions_per_week >= 1 AND sessions_per_week <= 14",
            name="ck_training_plans_training_plan_sessions_range",
        ),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_assessments_deleted_at", "assessments", ["deleted_at"], unique=False)
    op.create_index("ix_assessments_gym_id", "assessments", ["gym_id"], unique=False)
    op.create_index("ix_assessments_member_id", "assessments", ["member_id"], unique=False)
    op.create_index("ix_assessments_evaluator_id", "assessments", ["evaluator_id"], unique=False)
    op.create_index("ix_assessments_gym_date", "assessments", ["gym_id", "assessment_date"], unique=False)
    op.create_index("ix_assessments_member_date_desc", "assessments", ["member_id", "assessment_date"], unique=False)
    op.create_index("ix_assessments_due_date", "assessments", ["next_assessment_due"], unique=False)

    op.create_index("ix_member_constraints_deleted_at", "member_constraints", ["deleted_at"], unique=False)
    op.create_index("ix_member_constraints_gym_id", "member_constraints", ["gym_id"], unique=False)
    op.create_index("ix_member_constraints_member_id", "member_constraints", ["member_id"], unique=False)
    op.create_index("ix_member_constraints_gym_member", "member_constraints", ["gym_id", "member_id"], unique=False)

    op.create_index("ix_member_goals_deleted_at", "member_goals", ["deleted_at"], unique=False)
    op.create_index("ix_member_goals_gym_id", "member_goals", ["gym_id"], unique=False)
    op.create_index("ix_member_goals_member_id", "member_goals", ["member_id"], unique=False)
    op.create_index("ix_member_goals_assessment_id", "member_goals", ["assessment_id"], unique=False)
    op.create_index("ix_member_goals_gym_member_status", "member_goals", ["gym_id", "member_id", "status"], unique=False)
    op.create_index("ix_member_goals_member_target_date", "member_goals", ["member_id", "target_date"], unique=False)

    op.create_index("ix_training_plans_deleted_at", "training_plans", ["deleted_at"], unique=False)
    op.create_index("ix_training_plans_gym_id", "training_plans", ["gym_id"], unique=False)
    op.create_index("ix_training_plans_member_id", "training_plans", ["member_id"], unique=False)
    op.create_index("ix_training_plans_assessment_id", "training_plans", ["assessment_id"], unique=False)
    op.create_index("ix_training_plans_created_by_user_id", "training_plans", ["created_by_user_id"], unique=False)
    op.create_index("ix_training_plans_gym_member_active", "training_plans", ["gym_id", "member_id", "is_active"], unique=False)
    op.create_index("ix_training_plans_member_start_date", "training_plans", ["member_id", "start_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_training_plans_member_start_date", table_name="training_plans")
    op.drop_index("ix_training_plans_gym_member_active", table_name="training_plans")
    op.drop_index("ix_training_plans_created_by_user_id", table_name="training_plans")
    op.drop_index("ix_training_plans_assessment_id", table_name="training_plans")
    op.drop_index("ix_training_plans_member_id", table_name="training_plans")
    op.drop_index("ix_training_plans_gym_id", table_name="training_plans")
    op.drop_index("ix_training_plans_deleted_at", table_name="training_plans")

    op.drop_index("ix_member_goals_member_target_date", table_name="member_goals")
    op.drop_index("ix_member_goals_gym_member_status", table_name="member_goals")
    op.drop_index("ix_member_goals_assessment_id", table_name="member_goals")
    op.drop_index("ix_member_goals_member_id", table_name="member_goals")
    op.drop_index("ix_member_goals_gym_id", table_name="member_goals")
    op.drop_index("ix_member_goals_deleted_at", table_name="member_goals")

    op.drop_index("ix_member_constraints_gym_member", table_name="member_constraints")
    op.drop_index("ix_member_constraints_member_id", table_name="member_constraints")
    op.drop_index("ix_member_constraints_gym_id", table_name="member_constraints")
    op.drop_index("ix_member_constraints_deleted_at", table_name="member_constraints")

    op.drop_index("ix_assessments_due_date", table_name="assessments")
    op.drop_index("ix_assessments_member_date_desc", table_name="assessments")
    op.drop_index("ix_assessments_gym_date", table_name="assessments")
    op.drop_index("ix_assessments_evaluator_id", table_name="assessments")
    op.drop_index("ix_assessments_member_id", table_name="assessments")
    op.drop_index("ix_assessments_gym_id", table_name="assessments")
    op.drop_index("ix_assessments_deleted_at", table_name="assessments")

    op.drop_table("training_plans")
    op.drop_table("member_goals")
    op.drop_table("member_constraints")
    op.drop_table("assessments")
