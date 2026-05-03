"""add task autopilot tables

Revision ID: 20260503_0037
Revises: 20260428_0036
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260503_0037"
down_revision: str | None = "20260428_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "autopilot_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_key", sa.String(length=100), nullable=False),
        sa.Column("domain", sa.String(length=40), nullable=False),
        sa.Column("action_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("template_key", sa.String(length=100), nullable=True),
        sa.Column("message_body", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timeout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="1", nullable=False),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=60), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_autopilot_actions_gym_id", "autopilot_actions", ["gym_id"])
    op.create_index("ix_autopilot_actions_gym_status", "autopilot_actions", ["gym_id", "status"])
    op.create_index("ix_autopilot_actions_idempotency_key", "autopilot_actions", ["idempotency_key"])
    op.create_index("ix_autopilot_actions_lead_status", "autopilot_actions", ["lead_id", "status"])
    op.create_index("ix_autopilot_actions_member_status", "autopilot_actions", ["member_id", "status"])
    op.create_index("ix_autopilot_actions_policy_status", "autopilot_actions", ["policy_key", "status"])
    op.create_index("ix_autopilot_actions_scheduled", "autopilot_actions", ["scheduled_for", "status"])
    op.create_index("ix_autopilot_actions_timeout", "autopilot_actions", ["timeout_at", "status"])

    op.create_table(
        "autopilot_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("autopilot_action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("deduplication_key", sa.String(length=180), nullable=True),
        sa.Column("correlation_id", sa.String(length=120), nullable=True),
        sa.Column("created_by_system", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("raw_payload_hash", sa.String(length=80), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["autopilot_action_id"], ["autopilot_actions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "deduplication_key", name="uq_autopilot_events_gym_dedupe"),
    )
    op.create_index("ix_autopilot_events_correlation_id", "autopilot_events", ["correlation_id"])
    op.create_index("ix_autopilot_events_gym_created", "autopilot_events", ["gym_id", "created_at"])
    op.create_index("ix_autopilot_events_gym_id", "autopilot_events", ["gym_id"])
    op.create_index("ix_autopilot_events_gym_status", "autopilot_events", ["gym_id", "processing_status"])
    op.create_index("ix_autopilot_events_lead_created", "autopilot_events", ["lead_id", "created_at"])
    op.create_index("ix_autopilot_events_member_created", "autopilot_events", ["member_id", "created_at"])
    op.create_index("ix_autopilot_events_task_id", "autopilot_events", ["task_id"])
    op.create_index("ix_autopilot_events_type_created", "autopilot_events", ["event_type", "created_at"])

    op.create_table(
        "gym_autopilot_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("autopilot_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("autopilot_auto_close_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("autopilot_auto_send_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("retention_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("finance_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sales_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("onboarding_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("assessment_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("nps_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("business_hours_start", sa.String(length=5), server_default="08:00", nullable=False),
        sa.Column("business_hours_end", sa.String(length=5), server_default="20:00", nullable=False),
        sa.Column("max_auto_messages_per_member_per_week", sa.Integer(), server_default="2", nullable=False),
        sa.Column("max_auto_messages_per_lead_per_week", sa.Integer(), server_default="3", nullable=False),
        sa.Column("max_auto_actions_per_day", sa.Integer(), server_default="100", nullable=False),
        sa.Column("max_human_tasks_created_by_autopilot_per_day", sa.Integer(), server_default="25", nullable=False),
        sa.Column("default_timeout_hours", sa.Integer(), server_default="48", nullable=False),
        sa.Column("human_recent_activity_cooldown_hours", sa.Integer(), server_default="24", nullable=False),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id"),
    )
    op.create_index("ix_gym_autopilot_settings_gym", "gym_autopilot_settings", ["gym_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_gym_autopilot_settings_gym", table_name="gym_autopilot_settings")
    op.drop_table("gym_autopilot_settings")
    op.drop_index("ix_autopilot_events_type_created", table_name="autopilot_events")
    op.drop_index("ix_autopilot_events_task_id", table_name="autopilot_events")
    op.drop_index("ix_autopilot_events_member_created", table_name="autopilot_events")
    op.drop_index("ix_autopilot_events_lead_created", table_name="autopilot_events")
    op.drop_index("ix_autopilot_events_gym_status", table_name="autopilot_events")
    op.drop_index("ix_autopilot_events_gym_id", table_name="autopilot_events")
    op.drop_index("ix_autopilot_events_gym_created", table_name="autopilot_events")
    op.drop_index("ix_autopilot_events_correlation_id", table_name="autopilot_events")
    op.drop_table("autopilot_events")
    op.drop_index("ix_autopilot_actions_timeout", table_name="autopilot_actions")
    op.drop_index("ix_autopilot_actions_scheduled", table_name="autopilot_actions")
    op.drop_index("ix_autopilot_actions_policy_status", table_name="autopilot_actions")
    op.drop_index("ix_autopilot_actions_member_status", table_name="autopilot_actions")
    op.drop_index("ix_autopilot_actions_lead_status", table_name="autopilot_actions")
    op.drop_index("ix_autopilot_actions_idempotency_key", table_name="autopilot_actions")
    op.drop_index("ix_autopilot_actions_gym_status", table_name="autopilot_actions")
    op.drop_index("ix_autopilot_actions_gym_id", table_name="autopilot_actions")
    op.drop_table("autopilot_actions")
