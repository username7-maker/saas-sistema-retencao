"""autopilot action dispatch intent hardening

Revision ID: 20260713_0051
Revises: 20260713_0050
Create Date: 2026-07-13 18:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260713_0051"
down_revision: str | None = "20260713_0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("autopilot_actions", sa.Column("request_fingerprint", sa.String(length=96), nullable=True))
    op.add_column(
        "autopilot_actions",
        sa.Column("consent_snapshot", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )
    op.add_column("autopilot_actions", sa.Column("provider_status", sa.String(length=32), nullable=True))
    op.add_column("autopilot_actions", sa.Column("provider_reference", sa.String(length=180), nullable=True))
    op.add_column("autopilot_actions", sa.Column("provider_error", sa.Text(), nullable=True))
    op.add_column("autopilot_actions", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_autopilot_actions_request_fingerprint", "autopilot_actions", ["request_fingerprint"])
    op.create_index(
        "uq_autopilot_actions_gym_idempotency_key",
        "autopilot_actions",
        ["gym_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_autopilot_actions_gym_idempotency_key", table_name="autopilot_actions", postgresql_where=sa.text("idempotency_key IS NOT NULL"))
    op.drop_index("ix_autopilot_actions_request_fingerprint", table_name="autopilot_actions")
    op.drop_column("autopilot_actions", "dispatched_at")
    op.drop_column("autopilot_actions", "provider_error")
    op.drop_column("autopilot_actions", "provider_reference")
    op.drop_column("autopilot_actions", "provider_status")
    op.drop_column("autopilot_actions", "consent_snapshot")
    op.drop_column("autopilot_actions", "request_fingerprint")
