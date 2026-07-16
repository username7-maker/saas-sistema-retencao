"""assessment anthropometry local

Revision ID: 20260716_0050
Revises: 20260715_0052
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260716_0050"
down_revision: str | None = "20260715_0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("members", sa.Column("sex_for_clinical_calculation", sa.String(length=16), nullable=True))
    op.add_column("members", sa.Column("height_cm", sa.Numeric(6, 2), nullable=True))
    op.create_check_constraint(
        "members_clinical_sex_valid",
        "members",
        "sex_for_clinical_calculation IS NULL OR sex_for_clinical_calculation IN ('male', 'female')",
    )
    op.create_check_constraint(
        "members_height_positive",
        "members",
        "height_cm IS NULL OR height_cm > 0",
    )

    op.add_column("assessments", sa.Column("fat_mass_kg", sa.Numeric(6, 2), nullable=True))
    op.add_column("assessments", sa.Column("waist_hip_ratio", sa.Numeric(6, 2), nullable=True))
    op.add_column("assessments", sa.Column("basal_metabolic_rate", sa.Numeric(8, 2), nullable=True))
    op.add_column("assessments", sa.Column("assessment_method", sa.String(length=32), nullable=True))
    op.add_column("assessments", sa.Column("record_origin", sa.String(length=32), nullable=True))
    op.add_column("assessments", sa.Column("sex_used_for_formula", sa.String(length=16), nullable=True))
    op.add_column("assessments", sa.Column("age_used_for_formula", sa.SmallInteger(), nullable=True))
    op.add_column("assessments", sa.Column("height_used_for_formula", sa.Numeric(6, 2), nullable=True))
    op.add_column("assessments", sa.Column("weight_used_for_formula", sa.Numeric(6, 2), nullable=True))
    op.add_column("assessments", sa.Column("measurement_protocol", sa.String(length=120), nullable=True))
    op.add_column("assessments", sa.Column("formula_version", sa.String(length=120), nullable=True))
    op.add_column("assessments", sa.Column("calculation_hash", sa.String(length=64), nullable=True))
    op.add_column("assessments", sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("assessments", sa.Column("anthropometry_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.create_check_constraint(
        "assessment_method_valid",
        "assessments",
        "assessment_method IS NULL OR assessment_method IN ('manual_anthropometry', 'bioimpedance', 'hybrid', 'imported')",
    )
    op.create_check_constraint(
        "assessment_record_origin_valid",
        "assessments",
        "record_origin IS NULL OR record_origin IN ('cordex', 'legacy', 'actuar')",
    )
    op.create_check_constraint(
        "assessment_formula_sex_valid",
        "assessments",
        "sex_used_for_formula IS NULL OR sex_used_for_formula IN ('male', 'female')",
    )
    op.create_check_constraint(
        "assessment_fat_mass_non_negative",
        "assessments",
        "fat_mass_kg IS NULL OR fat_mass_kg >= 0",
    )
    op.create_check_constraint(
        "assessment_whr_positive",
        "assessments",
        "waist_hip_ratio IS NULL OR waist_hip_ratio > 0",
    )
    op.create_check_constraint(
        "assessment_bmr_positive",
        "assessments",
        "basal_metabolic_rate IS NULL OR basal_metabolic_rate > 0",
    )
    op.create_unique_constraint("uq_assessments_gym_idempotency_key", "assessments", ["gym_id", "idempotency_key"])
    op.create_index("ix_assessments_idempotency_key", "assessments", ["idempotency_key"])
    op.create_index(
        "ix_assessments_method_member_date",
        "assessments",
        ["assessment_method", "member_id", "assessment_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_assessments_method_member_date", table_name="assessments")
    op.drop_index("ix_assessments_idempotency_key", table_name="assessments")
    op.drop_constraint("uq_assessments_gym_idempotency_key", "assessments", type_="unique")
    op.drop_constraint("assessment_bmr_positive", "assessments", type_="check")
    op.drop_constraint("assessment_whr_positive", "assessments", type_="check")
    op.drop_constraint("assessment_fat_mass_non_negative", "assessments", type_="check")
    op.drop_constraint("assessment_formula_sex_valid", "assessments", type_="check")
    op.drop_constraint("assessment_record_origin_valid", "assessments", type_="check")
    op.drop_constraint("assessment_method_valid", "assessments", type_="check")

    for column in (
        "anthropometry_snapshot_json",
        "idempotency_key",
        "calculation_hash",
        "formula_version",
        "measurement_protocol",
        "weight_used_for_formula",
        "height_used_for_formula",
        "age_used_for_formula",
        "sex_used_for_formula",
        "record_origin",
        "assessment_method",
        "basal_metabolic_rate",
        "waist_hip_ratio",
        "fat_mass_kg",
    ):
        op.drop_column("assessments", column)

    op.drop_constraint("members_height_positive", "members", type_="check")
    op.drop_constraint("members_clinical_sex_valid", "members", type_="check")
    op.drop_column("members", "height_cm")
    op.drop_column("members", "sex_for_clinical_calculation")
