"""expand body composition v2 with OCR, AI and Actuar sync

Revision ID: 20260317_0020
Revises: 20260313_0019
Create Date: 2026-03-17
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260317_0020"
down_revision = "20260313_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE body_composition_evaluations DROP CONSTRAINT IF EXISTS ck_body_composition_evaluations_bce_source_valid")
    op.execute("ALTER TABLE body_composition_evaluations DROP CONSTRAINT IF EXISTS ck_body_composition_evaluations_ck_body_composition_eva_d7eb")

    op.add_column("body_composition_evaluations", sa.Column("body_fat_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("waist_hip_ratio", sa.Numeric(5, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("fat_free_mass_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("inorganic_salt_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("protein_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("body_water_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("skeletal_muscle_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("target_weight_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("weight_control_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("muscle_control_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("fat_control_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("total_energy_kcal", sa.Numeric(8, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("physical_age", sa.Integer(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("health_score", sa.Integer(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("raw_ocr_text", sa.Text(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("ocr_confidence", sa.Numeric(5, 4), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("ocr_warnings_json", JSONB(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("needs_review", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("body_composition_evaluations", sa.Column("reviewed_manually", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("body_composition_evaluations", sa.Column("device_model", sa.String(length=120), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("device_profile", sa.String(length=60), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("parsed_from_image", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("body_composition_evaluations", sa.Column("ocr_source_file_ref", sa.String(length=500), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("measured_ranges_json", JSONB(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("ai_coach_summary", sa.Text(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("ai_member_friendly_summary", sa.Text(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("ai_risk_flags_json", JSONB(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("ai_training_focus_json", JSONB(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("ai_generated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("actuar_sync_status", sa.String(length=20), server_default="disabled", nullable=False))
    op.add_column("body_composition_evaluations", sa.Column("actuar_sync_mode", sa.String(length=20), server_default="disabled", nullable=False))
    op.add_column("body_composition_evaluations", sa.Column("actuar_external_id", sa.String(length=120), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("actuar_last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("actuar_last_error", sa.Text(), nullable=True))

    op.create_check_constraint(
        "ck_body_composition_evaluations_bce_source_valid",
        "body_composition_evaluations",
        "source IN ('tezewa', 'manual', 'ocr_receipt', 'device_import', 'actuar_sync')",
    )
    op.create_check_constraint(
        "ck_body_composition_evaluations_bce_ocr_confidence_range",
        "body_composition_evaluations",
        "ocr_confidence IS NULL OR (ocr_confidence >= 0 AND ocr_confidence <= 1)",
    )
    op.create_check_constraint(
        "ck_body_composition_evaluations_bce_actuar_sync_mode_valid",
        "body_composition_evaluations",
        "actuar_sync_mode IN ('disabled', 'http_api', 'csv_export', 'assisted_rpa')",
    )
    op.create_check_constraint(
        "ck_body_composition_evaluations_bce_actuar_sync_status_valid",
        "body_composition_evaluations",
        "actuar_sync_status IN ('disabled', 'pending', 'exported', 'synced', 'failed', 'skipped')",
    )
    op.create_index("ix_bce_gym_sync_status", "body_composition_evaluations", ["gym_id", "actuar_sync_status"])

    op.create_table(
        "body_composition_sync_attempts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("gym_id", UUID(as_uuid=True), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "body_composition_evaluation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("body_composition_evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sync_mode", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload_snapshot_json", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "sync_mode IN ('disabled', 'http_api', 'csv_export', 'assisted_rpa')",
            name="ck_body_composition_sync_attempts_bcsa_sync_mode_valid",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'exported', 'synced', 'failed', 'skipped', 'disabled')",
            name="ck_body_composition_sync_attempts_bcsa_status_valid",
        ),
    )
    op.create_index("ix_bcsa_body_composition_evaluation_id", "body_composition_sync_attempts", ["body_composition_evaluation_id"])
    op.create_index("ix_bcsa_gym_id", "body_composition_sync_attempts", ["gym_id"])
    op.create_index("ix_bcsa_evaluation_created", "body_composition_sync_attempts", ["body_composition_evaluation_id", "created_at"])
    op.create_index("ix_bcsa_gym_created", "body_composition_sync_attempts", ["gym_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_bcsa_gym_created", table_name="body_composition_sync_attempts")
    op.drop_index("ix_bcsa_evaluation_created", table_name="body_composition_sync_attempts")
    op.drop_index("ix_bcsa_gym_id", table_name="body_composition_sync_attempts")
    op.drop_index("ix_bcsa_body_composition_evaluation_id", table_name="body_composition_sync_attempts")
    op.drop_table("body_composition_sync_attempts")

    op.drop_index("ix_bce_gym_sync_status", table_name="body_composition_evaluations")
    op.drop_constraint("ck_body_composition_evaluations_bce_actuar_sync_status_valid", "body_composition_evaluations", type_="check")
    op.drop_constraint("ck_body_composition_evaluations_bce_actuar_sync_mode_valid", "body_composition_evaluations", type_="check")
    op.drop_constraint("ck_body_composition_evaluations_bce_ocr_confidence_range", "body_composition_evaluations", type_="check")
    op.drop_constraint("ck_body_composition_evaluations_bce_source_valid", "body_composition_evaluations", type_="check")

    for column_name in (
        "actuar_last_error",
        "actuar_last_synced_at",
        "actuar_external_id",
        "actuar_sync_mode",
        "actuar_sync_status",
        "ai_generated_at",
        "ai_training_focus_json",
        "ai_risk_flags_json",
        "ai_member_friendly_summary",
        "ai_coach_summary",
        "measured_ranges_json",
        "ocr_source_file_ref",
        "parsed_from_image",
        "device_profile",
        "device_model",
        "reviewed_manually",
        "needs_review",
        "ocr_warnings_json",
        "ocr_confidence",
        "raw_ocr_text",
        "health_score",
        "physical_age",
        "total_energy_kcal",
        "fat_control_kg",
        "muscle_control_kg",
        "weight_control_kg",
        "target_weight_kg",
        "skeletal_muscle_kg",
        "body_water_kg",
        "protein_kg",
        "inorganic_salt_kg",
        "fat_free_mass_kg",
        "waist_hip_ratio",
        "body_fat_kg",
    ):
        op.drop_column("body_composition_evaluations", column_name)

    op.create_check_constraint(
        "ck_body_composition_evaluations_bce_source_valid",
        "body_composition_evaluations",
        "source IN ('tezewa', 'manual')",
    )
