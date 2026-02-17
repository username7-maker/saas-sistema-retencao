"""add automation rules and message logs

Revision ID: 20260216_0003
Revises: 20260215_0002
Create Date: 2026-02-16 00:03:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260216_0003"
down_revision = "20260215_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger_type", sa.String(length=40), nullable=False),
        sa.Column("trigger_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("action_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("executions_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_automation_rules_trigger_active", "automation_rules", ["trigger_type", "is_active"], unique=False)

    op.create_table(
        "message_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("automation_rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("template_name", sa.String(length=100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'sent'")),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["automation_rule_id"], ["automation_rules.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_message_logs_member_id", "message_logs", ["member_id"], unique=False)
    op.create_index("ix_message_logs_member_channel", "message_logs", ["member_id", "channel"], unique=False)
    op.create_index("ix_message_logs_status_created", "message_logs", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_message_logs_status_created", table_name="message_logs")
    op.drop_index("ix_message_logs_member_channel", table_name="message_logs")
    op.drop_index("ix_message_logs_member_id", table_name="message_logs")
    op.drop_table("message_logs")

    op.drop_index("ix_automation_rules_trigger_active", table_name="automation_rules")
    op.drop_table("automation_rules")
