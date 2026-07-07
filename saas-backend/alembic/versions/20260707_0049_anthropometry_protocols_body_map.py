"""anthropometry protocols body map

Revision ID: 20260707_0049
Revises: 20260707_0048
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260707_0049"
down_revision: str | None = "20260707_0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_METHODS = (
    "'legacy_bioimpedance'",
    "'navy_circumference'",
    "'rfm'",
    "'geneos_composite'",
    "'skinfold_protocol'",
    "'manual_override'",
)

_OLD_METHODS = (
    "'legacy_bioimpedance'",
    "'navy_circumference'",
    "'rfm'",
    "'geneos_composite'",
    "'manual_override'",
)

_SKINFOLD_COLUMNS = (
    "skinfold_chest_mm",
    "skinfold_midaxillary_mm",
    "skinfold_subscapular_mm",
    "skinfold_triceps_mm",
    "skinfold_biceps_mm",
    "skinfold_abdominal_mm",
    "skinfold_suprailiac_mm",
    "skinfold_thigh_mm",
    "skinfold_calf_mm",
)


def upgrade() -> None:
    for column in _SKINFOLD_COLUMNS:
        op.add_column("body_composition_evaluations", sa.Column(column, sa.Numeric(6, 2), nullable=True))

    op.alter_column("body_composition_evaluations", "measurement_protocol", type_=sa.String(length=80), existing_type=sa.String(length=60))
    op.drop_constraint("bce_body_fat_method_valid", "body_composition_evaluations", type_="check")
    op.create_check_constraint(
        "bce_body_fat_method_valid",
        "body_composition_evaluations",
        f"body_fat_method IS NULL OR body_fat_method IN ({', '.join(_NEW_METHODS)})",
    )


def downgrade() -> None:
    op.drop_constraint("bce_body_fat_method_valid", "body_composition_evaluations", type_="check")
    op.create_check_constraint(
        "bce_body_fat_method_valid",
        "body_composition_evaluations",
        f"body_fat_method IS NULL OR body_fat_method IN ({', '.join(_OLD_METHODS)})",
    )
    op.alter_column("body_composition_evaluations", "measurement_protocol", type_=sa.String(length=60), existing_type=sa.String(length=80))

    for column in reversed(_SKINFOLD_COLUMNS):
        op.drop_column("body_composition_evaluations", column)
