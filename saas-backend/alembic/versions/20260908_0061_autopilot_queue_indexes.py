"""Add composite indexes for due autopilot queue scans.

Revision ID: 20260908_0061
Revises: 20260904_0060
"""

from alembic import op


revision = "20260908_0061"
down_revision = "20260904_0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_autopilot_events_gym_status_received",
        "autopilot_events",
        ["gym_id", "processing_status", "received_at"],
        unique=False,
    )
    op.create_index(
        "ix_autopilot_actions_gym_status_scheduled",
        "autopilot_actions",
        ["gym_id", "status", "scheduled_for", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_autopilot_actions_gym_status_timeout",
        "autopilot_actions",
        ["gym_id", "status", "timeout_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_autopilot_actions_gym_status_timeout", table_name="autopilot_actions")
    op.drop_index("ix_autopilot_actions_gym_status_scheduled", table_name="autopilot_actions")
    op.drop_index("ix_autopilot_events_gym_status_received", table_name="autopilot_events")
