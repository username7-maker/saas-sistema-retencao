"""add automation journeys

Revision ID: 20260428_0036
Revises: 20260427_0035
Create Date: 2026-04-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260428_0036"
down_revision: str | tuple[str, str] | None = "20260427_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "automation_journeys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=40), nullable=False),
        sa.Column("entry_trigger", sa.String(length=80), nullable=False),
        sa.Column("audience_config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("exit_conditions", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("metrics_config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("requires_human_approval", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_journeys_gym_id", "automation_journeys", ["gym_id"])
    op.create_index("ix_automation_journeys_domain", "automation_journeys", ["domain"])
    op.create_index("ix_automation_journeys_gym_active", "automation_journeys", ["gym_id", "is_active"])
    op.create_index("ix_automation_journeys_gym_domain", "automation_journeys", ["gym_id", "domain"])

    op.create_table(
        "automation_journey_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("delay_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("delay_hours", sa.Integer(), server_default="0", nullable=False),
        sa.Column("condition_config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("action_config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=True),
        sa.Column("owner_role", sa.String(length=40), nullable=True),
        sa.Column("preferred_shift", sa.String(length=24), nullable=True),
        sa.Column("template_key", sa.String(length=80), nullable=True),
        sa.Column("fallback_mode", sa.String(length=40), server_default="manual_required", nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["journey_id"], ["automation_journeys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("journey_id", "step_order", name="uq_automation_journey_step_order"),
    )
    op.create_index("ix_automation_journey_steps_gym_id", "automation_journey_steps", ["gym_id"])
    op.create_index("ix_automation_journey_steps_journey_id", "automation_journey_steps", ["journey_id"])
    op.create_index("ix_automation_journey_steps_gym_journey", "automation_journey_steps", ["gym_id", "journey_id"])

    op.create_table(
        "automation_journey_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("state", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("current_step_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_step_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["current_step_id"], ["automation_journey_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["journey_id"], ["automation_journeys.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("journey_id", "lead_id", name="uq_automation_journey_lead"),
        sa.UniqueConstraint("journey_id", "member_id", name="uq_automation_journey_member"),
    )
    op.create_index("ix_automation_journey_enrollments_gym_id", "automation_journey_enrollments", ["gym_id"])
    op.create_index("ix_automation_journey_enrollments_journey_id", "automation_journey_enrollments", ["journey_id"])
    op.create_index("ix_automation_journey_enrollments_member_id", "automation_journey_enrollments", ["member_id"])
    op.create_index("ix_automation_journey_enrollments_lead_id", "automation_journey_enrollments", ["lead_id"])
    op.create_index("ix_automation_journey_enrollments_current_step_id", "automation_journey_enrollments", ["current_step_id"])
    op.create_index("ix_automation_journey_enrollments_state", "automation_journey_enrollments", ["state"])
    op.create_index("ix_automation_journey_enrollments_next_step_due_at", "automation_journey_enrollments", ["next_step_due_at"])
    op.create_index("ix_automation_journey_enrollments_gym_state", "automation_journey_enrollments", ["gym_id", "state"])
    op.create_index("ix_automation_journey_enrollments_due", "automation_journey_enrollments", ["next_step_due_at"])

    op.create_table(
        "automation_journey_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journey_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["automation_journey_enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["journey_id"], ["automation_journeys.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["step_id"], ["automation_journey_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_journey_events_gym_id", "automation_journey_events", ["gym_id"])
    op.create_index("ix_automation_journey_events_journey_id", "automation_journey_events", ["journey_id"])
    op.create_index("ix_automation_journey_events_enrollment_id", "automation_journey_events", ["enrollment_id"])
    op.create_index("ix_automation_journey_events_step_id", "automation_journey_events", ["step_id"])
    op.create_index("ix_automation_journey_events_task_id", "automation_journey_events", ["task_id"])
    op.create_index("ix_automation_journey_events_member_id", "automation_journey_events", ["member_id"])
    op.create_index("ix_automation_journey_events_lead_id", "automation_journey_events", ["lead_id"])
    op.create_index("ix_automation_journey_events_user_id", "automation_journey_events", ["user_id"])
    op.create_index("ix_automation_journey_events_event_type", "automation_journey_events", ["event_type"])
    op.create_index("ix_automation_journey_events_outcome", "automation_journey_events", ["outcome"])
    op.create_index("ix_automation_journey_events_gym_created", "automation_journey_events", ["gym_id", "created_at"])
    op.create_index("ix_automation_journey_events_enrollment_created", "automation_journey_events", ["enrollment_id", "created_at"])
    op.create_index("ix_automation_journey_events_type_created", "automation_journey_events", ["event_type", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_automation_journey_events_type_created", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_enrollment_created", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_gym_created", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_outcome", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_event_type", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_user_id", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_lead_id", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_member_id", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_task_id", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_step_id", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_enrollment_id", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_journey_id", table_name="automation_journey_events")
    op.drop_index("ix_automation_journey_events_gym_id", table_name="automation_journey_events")
    op.drop_table("automation_journey_events")
    op.drop_index("ix_automation_journey_enrollments_due", table_name="automation_journey_enrollments")
    op.drop_index("ix_automation_journey_enrollments_gym_state", table_name="automation_journey_enrollments")
    op.drop_index("ix_automation_journey_enrollments_next_step_due_at", table_name="automation_journey_enrollments")
    op.drop_index("ix_automation_journey_enrollments_state", table_name="automation_journey_enrollments")
    op.drop_index("ix_automation_journey_enrollments_current_step_id", table_name="automation_journey_enrollments")
    op.drop_index("ix_automation_journey_enrollments_lead_id", table_name="automation_journey_enrollments")
    op.drop_index("ix_automation_journey_enrollments_member_id", table_name="automation_journey_enrollments")
    op.drop_index("ix_automation_journey_enrollments_journey_id", table_name="automation_journey_enrollments")
    op.drop_index("ix_automation_journey_enrollments_gym_id", table_name="automation_journey_enrollments")
    op.drop_table("automation_journey_enrollments")
    op.drop_index("ix_automation_journey_steps_gym_journey", table_name="automation_journey_steps")
    op.drop_index("ix_automation_journey_steps_journey_id", table_name="automation_journey_steps")
    op.drop_index("ix_automation_journey_steps_gym_id", table_name="automation_journey_steps")
    op.drop_table("automation_journey_steps")
    op.drop_index("ix_automation_journeys_gym_domain", table_name="automation_journeys")
    op.drop_index("ix_automation_journeys_gym_active", table_name="automation_journeys")
    op.drop_index("ix_automation_journeys_domain", table_name="automation_journeys")
    op.drop_index("ix_automation_journeys_gym_id", table_name="automation_journeys")
    op.drop_table("automation_journeys")
