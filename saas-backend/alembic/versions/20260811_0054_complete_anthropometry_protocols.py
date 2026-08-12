"""complete anthropometry protocol inputs

Revision ID: 20260811_0054
Revises: 20260717_0053
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260811_0054"
down_revision: str | None = "20260717_0053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("body_composition_evaluations", sa.Column("iliac_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("anthropometry_ethnicity", sa.String(length=20), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("anthropometry_maturity", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        "bce_anthropometry_ethnicity_valid",
        "body_composition_evaluations",
        "anthropometry_ethnicity IS NULL OR anthropometry_ethnicity IN ('white', 'black')",
    )
    op.create_check_constraint(
        "bce_anthropometry_maturity_valid",
        "body_composition_evaluations",
        "anthropometry_maturity IS NULL OR anthropometry_maturity IN ('prepubertal', 'pubertal', 'postpubertal')",
    )


def downgrade() -> None:
    op.drop_constraint("bce_anthropometry_maturity_valid", "body_composition_evaluations", type_="check")
    op.drop_constraint("bce_anthropometry_ethnicity_valid", "body_composition_evaluations", type_="check")
    op.drop_column("body_composition_evaluations", "anthropometry_maturity")
    op.drop_column("body_composition_evaluations", "anthropometry_ethnicity")
    op.drop_column("body_composition_evaluations", "iliac_cm")
