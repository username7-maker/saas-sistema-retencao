"""legacy unified assessment production marker

Revision ID: 20260715_0052
Revises: 20260707_0049
Create Date: 2026-07-15

This revision id exists in the pilot database from the abandoned
`gsd/phase-11-unified-physical-assessment-actuar-v2` branch.

The Phase 11 local anthropometry branch must not reintroduce that full schema
or Actuar Core pipeline. Keeping this marker as a no-op lets Alembic recognize
the pilot database revision and continue with the scoped V1 local migrations.
"""

from collections.abc import Sequence


revision: str = "20260715_0052"
down_revision: str | None = "20260707_0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
