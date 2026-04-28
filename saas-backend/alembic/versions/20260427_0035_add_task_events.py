"""add task events

Revision ID: 20260427_0035
Revises: 20260424_0020, 20260426_0034
Create Date: 2026-04-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260427_0035"
down_revision: str | tuple[str, str] | None = ("20260424_0020", "20260426_0034")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=True),
        sa.Column("contact_channel", sa.String(length=40), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_events_gym_id", "task_events", ["gym_id"])
    op.create_index("ix_task_events_task_id", "task_events", ["task_id"])
    op.create_index("ix_task_events_member_id", "task_events", ["member_id"])
    op.create_index("ix_task_events_lead_id", "task_events", ["lead_id"])
    op.create_index("ix_task_events_user_id", "task_events", ["user_id"])
    op.create_index("ix_task_events_event_type", "task_events", ["event_type"])
    op.create_index("ix_task_events_outcome", "task_events", ["outcome"])
    op.create_index("ix_task_events_task_created", "task_events", ["task_id", "created_at"])
    op.create_index("ix_task_events_gym_created", "task_events", ["gym_id", "created_at"])
    op.create_index("ix_task_events_user_created", "task_events", ["user_id", "created_at"])
    op.create_index("ix_task_events_type_created", "task_events", ["event_type", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_task_events_type_created", table_name="task_events")
    op.drop_index("ix_task_events_user_created", table_name="task_events")
    op.drop_index("ix_task_events_gym_created", table_name="task_events")
    op.drop_index("ix_task_events_task_created", table_name="task_events")
    op.drop_index("ix_task_events_outcome", table_name="task_events")
    op.drop_index("ix_task_events_event_type", table_name="task_events")
    op.drop_index("ix_task_events_user_id", table_name="task_events")
    op.drop_index("ix_task_events_lead_id", table_name="task_events")
    op.drop_index("ix_task_events_member_id", table_name="task_events")
    op.drop_index("ix_task_events_task_id", table_name="task_events")
    op.drop_index("ix_task_events_gym_id", table_name="task_events")
    op.drop_table("task_events")
