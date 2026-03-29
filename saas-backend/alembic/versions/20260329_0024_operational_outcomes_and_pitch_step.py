"""add operational outcomes and pitch step

Revision ID: 20260329_0024
Revises: 20260323_0023
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_0024"
down_revision = "20260323_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("pitch_step", sa.String(length=40), nullable=False, server_default="briefing"),
    )
    op.create_index("ix_leads_pitch_step", "leads", ["pitch_step"], unique=False)

    op.create_table(
        "operational_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("risk_alert_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=20), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("related_entity_type", sa.String(length=40), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("playbook_key", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_booking_id"], ["lead_bookings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_log_id"], ["message_logs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["risk_alert_id"], ["risk_alerts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operational_outcomes")),
    )
    op.create_index(op.f("ix_operational_outcomes_gym_id"), "operational_outcomes", ["gym_id"], unique=False)
    op.create_index(op.f("ix_operational_outcomes_member_id"), "operational_outcomes", ["member_id"], unique=False)
    op.create_index(op.f("ix_operational_outcomes_lead_id"), "operational_outcomes", ["lead_id"], unique=False)
    op.create_index(op.f("ix_operational_outcomes_actor_user_id"), "operational_outcomes", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_operational_outcomes_task_id"), "operational_outcomes", ["task_id"], unique=False)
    op.create_index(op.f("ix_operational_outcomes_risk_alert_id"), "operational_outcomes", ["risk_alert_id"], unique=False)
    op.create_index(op.f("ix_operational_outcomes_message_log_id"), "operational_outcomes", ["message_log_id"], unique=False)
    op.create_index(op.f("ix_operational_outcomes_lead_booking_id"), "operational_outcomes", ["lead_booking_id"], unique=False)
    op.create_index(op.f("ix_operational_outcomes_source"), "operational_outcomes", ["source"], unique=False)
    op.create_index(op.f("ix_operational_outcomes_action_type"), "operational_outcomes", ["action_type"], unique=False)
    op.create_index(op.f("ix_operational_outcomes_status"), "operational_outcomes", ["status"], unique=False)
    op.create_index("ix_operational_outcomes_gym_source_status", "operational_outcomes", ["gym_id", "source", "status"], unique=False)
    op.create_index("ix_operational_outcomes_gym_occurred", "operational_outcomes", ["gym_id", "occurred_at"], unique=False)
    op.create_index("ix_operational_outcomes_actor_user", "operational_outcomes", ["actor_user_id", "occurred_at"], unique=False)
    op.create_index("ix_operational_outcomes_member_status", "operational_outcomes", ["member_id", "status"], unique=False)
    op.create_index("ix_operational_outcomes_lead_status", "operational_outcomes", ["lead_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_operational_outcomes_lead_status", table_name="operational_outcomes")
    op.drop_index("ix_operational_outcomes_member_status", table_name="operational_outcomes")
    op.drop_index("ix_operational_outcomes_actor_user", table_name="operational_outcomes")
    op.drop_index("ix_operational_outcomes_gym_occurred", table_name="operational_outcomes")
    op.drop_index("ix_operational_outcomes_gym_source_status", table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_status"), table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_action_type"), table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_source"), table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_lead_booking_id"), table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_message_log_id"), table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_risk_alert_id"), table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_task_id"), table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_actor_user_id"), table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_lead_id"), table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_member_id"), table_name="operational_outcomes")
    op.drop_index(op.f("ix_operational_outcomes_gym_id"), table_name="operational_outcomes")
    op.drop_table("operational_outcomes")
    op.drop_index("ix_leads_pitch_step", table_name="leads")
    op.drop_column("leads", "pitch_step")
