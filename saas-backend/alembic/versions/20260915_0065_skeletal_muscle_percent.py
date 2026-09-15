"""Store the skeletal-muscle percentage printed by the bioimpedance report.

Revision ID: 20260915_0065
Revises: 20260914_0064
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260915_0065"
down_revision: str | None = "20260914_0064"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "body_composition_evaluations",
        sa.Column("skeletal_muscle_percent", sa.Numeric(5, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("body_composition_evaluations", "skeletal_muscle_percent")
