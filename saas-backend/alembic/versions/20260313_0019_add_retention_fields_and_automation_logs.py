"""add retention fields to members and automation execution logs

Revision ID: 20260313_0019
Revises: 20260311_0018
Create Date: 2026-03-13
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "20260313_0019"
down_revision = "20260311_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "members",
        sa.Column("onboarding_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "members",
        sa.Column("onboarding_status", sa.String(length=20), nullable=False, server_default="active"),
    )
    op.add_column("members", sa.Column("churn_type", sa.String(length=40), nullable=True))
    op.add_column(
        "members",
        sa.Column("is_vip", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("members", sa.Column("retention_stage", sa.String(length=30), nullable=True))

    op.create_table(
        "automation_execution_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("gym_id", UUID(as_uuid=True), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", UUID(as_uuid=True), sa.ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", UUID(as_uuid=True), sa.ForeignKey("members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("details", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_automation_execution_logs_gym_id",
        "automation_execution_logs",
        ["gym_id"],
    )
    op.create_index(
        "ix_automation_execution_logs_rule_id",
        "automation_execution_logs",
        ["rule_id"],
    )
    op.create_index(
        "ix_automation_execution_logs_member_id",
        "automation_execution_logs",
        ["member_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_automation_execution_logs_member_id", table_name="automation_execution_logs")
    op.drop_index("ix_automation_execution_logs_rule_id", table_name="automation_execution_logs")
    op.drop_index("ix_automation_execution_logs_gym_id", table_name="automation_execution_logs")
    op.drop_table("automation_execution_logs")

    op.drop_column("members", "retention_stage")
    op.drop_column("members", "is_vip")
    op.drop_column("members", "churn_type")
    op.drop_column("members", "onboarding_status")
    op.drop_column("members", "onboarding_score")
