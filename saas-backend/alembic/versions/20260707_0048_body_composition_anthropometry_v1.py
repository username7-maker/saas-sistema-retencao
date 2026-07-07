"""body composition anthropometry v1

Revision ID: 20260707_0048
Revises: 20260603_0047
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260707_0048"
down_revision: str | None = "20260603_0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("body_composition_evaluations", sa.Column("body_fat_bioimpedance_percent", sa.Numeric(5, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("body_fat_anthropometric_percent", sa.Numeric(5, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("body_fat_manual_override_percent", sa.Numeric(5, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("body_fat_used_percent", sa.Numeric(5, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("body_fat_used_source", sa.String(length=30), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("body_fat_method", sa.String(length=40), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("body_fat_confidence", sa.String(length=20), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("body_fat_range_min", sa.Numeric(5, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("body_fat_range_max", sa.Numeric(5, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("preferred_body_fat_source", sa.String(length=30), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("measurement_source", sa.String(length=30), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("fat_mass_estimated_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("lean_mass_estimated_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("neck_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("shoulders_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("chest_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("waist_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("abdomen_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("hip_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("right_arm_relaxed_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("left_arm_relaxed_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("right_arm_flexed_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("left_arm_flexed_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("right_thigh_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("left_thigh_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("right_calf_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("left_calf_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("anthropometry_notes", sa.Text(), nullable=True))
    op.add_column(
        "body_composition_evaluations",
        sa.Column("body_fat_manual_review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "body_composition_evaluations",
        sa.Column("body_fat_manual_review_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "body_composition_evaluations",
        sa.Column("anthropometry_review_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("body_composition_evaluations", sa.Column("measurement_protocol", sa.String(length=60), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("evaluated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.create_foreign_key(
        "fk_bce_evaluated_by_user_id_users",
        "body_composition_evaluations",
        "users",
        ["evaluated_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        """
        UPDATE body_composition_evaluations
        SET
            body_fat_bioimpedance_percent = body_fat_percent,
            body_fat_used_percent = body_fat_percent,
            body_fat_used_source = CASE WHEN body_fat_percent IS NULL THEN NULL ELSE 'bioimpedance' END,
            body_fat_method = CASE WHEN body_fat_percent IS NULL THEN NULL ELSE 'legacy_bioimpedance' END,
            preferred_body_fat_source = 'bioimpedance',
            measurement_source = 'bioimpedance'
        WHERE body_fat_used_percent IS NULL
        """
    )

    op.create_check_constraint(
        "bce_body_fat_bioimpedance_range",
        "body_composition_evaluations",
        "body_fat_bioimpedance_percent IS NULL OR (body_fat_bioimpedance_percent >= 0 AND body_fat_bioimpedance_percent <= 100)",
    )
    op.create_check_constraint(
        "bce_body_fat_anthropometric_range",
        "body_composition_evaluations",
        "body_fat_anthropometric_percent IS NULL OR (body_fat_anthropometric_percent >= 0 AND body_fat_anthropometric_percent <= 100)",
    )
    op.create_check_constraint(
        "bce_body_fat_manual_override_range",
        "body_composition_evaluations",
        "body_fat_manual_override_percent IS NULL OR (body_fat_manual_override_percent >= 0 AND body_fat_manual_override_percent <= 100)",
    )
    op.create_check_constraint(
        "bce_body_fat_used_range",
        "body_composition_evaluations",
        "body_fat_used_percent IS NULL OR (body_fat_used_percent >= 0 AND body_fat_used_percent <= 100)",
    )
    op.create_check_constraint(
        "bce_measurement_source_valid",
        "body_composition_evaluations",
        "measurement_source IS NULL OR measurement_source IN ('bioimpedance', 'manual_anthropometry', 'composite_geneos', 'manual_override')",
    )
    op.create_check_constraint(
        "bce_preferred_body_fat_source_valid",
        "body_composition_evaluations",
        "preferred_body_fat_source IS NULL OR preferred_body_fat_source IN ('bioimpedance', 'anthropometry', 'geneos_composite', 'manual_override')",
    )
    op.create_check_constraint(
        "bce_body_fat_used_source_valid",
        "body_composition_evaluations",
        "body_fat_used_source IS NULL OR body_fat_used_source IN ('bioimpedance', 'anthropometry', 'manual_override')",
    )
    op.create_check_constraint(
        "bce_body_fat_method_valid",
        "body_composition_evaluations",
        "body_fat_method IS NULL OR body_fat_method IN ('legacy_bioimpedance', 'navy_circumference', 'rfm', 'geneos_composite', 'manual_override')",
    )
    op.create_check_constraint(
        "bce_body_fat_confidence_valid",
        "body_composition_evaluations",
        "body_fat_confidence IS NULL OR body_fat_confidence IN ('high', 'medium_high', 'medium', 'low', 'inconsistent')",
    )


def downgrade() -> None:
    op.drop_constraint("bce_body_fat_confidence_valid", "body_composition_evaluations", type_="check")
    op.drop_constraint("bce_body_fat_method_valid", "body_composition_evaluations", type_="check")
    op.drop_constraint("bce_body_fat_used_source_valid", "body_composition_evaluations", type_="check")
    op.drop_constraint("bce_preferred_body_fat_source_valid", "body_composition_evaluations", type_="check")
    op.drop_constraint("bce_measurement_source_valid", "body_composition_evaluations", type_="check")
    op.drop_constraint("bce_body_fat_used_range", "body_composition_evaluations", type_="check")
    op.drop_constraint("bce_body_fat_manual_override_range", "body_composition_evaluations", type_="check")
    op.drop_constraint("bce_body_fat_anthropometric_range", "body_composition_evaluations", type_="check")
    op.drop_constraint("bce_body_fat_bioimpedance_range", "body_composition_evaluations", type_="check")
    op.drop_constraint("fk_bce_evaluated_by_user_id_users", "body_composition_evaluations", type_="foreignkey")

    for column in (
        "evaluated_by_user_id",
        "measurement_protocol",
        "anthropometry_review_completed",
        "body_fat_manual_review_completed",
        "body_fat_manual_review_required",
        "anthropometry_notes",
        "left_calf_cm",
        "right_calf_cm",
        "left_thigh_cm",
        "right_thigh_cm",
        "left_arm_flexed_cm",
        "right_arm_flexed_cm",
        "left_arm_relaxed_cm",
        "right_arm_relaxed_cm",
        "hip_cm",
        "abdomen_cm",
        "waist_cm",
        "chest_cm",
        "shoulders_cm",
        "neck_cm",
        "lean_mass_estimated_kg",
        "fat_mass_estimated_kg",
        "measurement_source",
        "preferred_body_fat_source",
        "body_fat_range_max",
        "body_fat_range_min",
        "body_fat_confidence",
        "body_fat_method",
        "body_fat_used_source",
        "body_fat_used_percent",
        "body_fat_manual_override_percent",
        "body_fat_anthropometric_percent",
        "body_fat_bioimpedance_percent",
    ):
        op.drop_column("body_composition_evaluations", column)
