"""assessment origin backfill

Revision ID: 20260716_0051
Revises: 20260716_0050
Create Date: 2026-07-16
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260716_0051"
down_revision: str | None = "20260716_0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE assessments
        SET record_origin = 'legacy'
        WHERE record_origin IS NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE assessments
        SET record_origin = NULL
        WHERE assessment_method IS NULL
          AND record_origin = 'legacy'
        """
    )
