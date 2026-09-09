"""Add idempotency protection to body composition evaluations.

Revision ID: 20260908_0062
Revises: 20260908_0061
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260908_0062"
down_revision = "20260908_0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "body_composition_evaluations",
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "body_composition_evaluations",
        sa.Column("idempotency_payload_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "uq_bce_gym_idempotency_key",
        "body_composition_evaluations",
        ["gym_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_bce_gym_idempotency_key", table_name="body_composition_evaluations")
    op.drop_column("body_composition_evaluations", "idempotency_payload_hash")
    op.drop_column("body_composition_evaluations", "idempotency_key")
