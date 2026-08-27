"""add Lee muscle mass to anthropometric assessments

Revision ID: 20260827_0058
Revises: 20260820_0057
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0058"
down_revision: str | None = "20260820_0057"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("muscle_mass_kg", sa.Numeric(precision=6, scale=2), nullable=True))
    op.create_check_constraint(
        "assessment_muscle_mass_positive",
        "assessments",
        "muscle_mass_kg IS NULL OR muscle_mass_kg > 0",
    )


def downgrade() -> None:
    op.drop_constraint("assessment_muscle_mass_positive", "assessments", type_="check")
    op.drop_column("assessments", "muscle_mass_kg")
