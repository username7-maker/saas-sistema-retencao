"""Add recoverable deletion to body composition evaluations.

Revision ID: 20260911_0063
Revises: 20260908_0062
"""

import sqlalchemy as sa

from alembic import op

revision = "20260911_0063"
down_revision = "20260908_0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("body_composition_evaluations", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_body_composition_evaluations_deleted_at",
        "body_composition_evaluations",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_body_composition_evaluations_deleted_at", table_name="body_composition_evaluations")
    op.drop_column("body_composition_evaluations", "deleted_at")
