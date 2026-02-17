"""add goals table

Revision ID: 20260217_0005
Revises: 20260217_0004
Create Date: 2026-02-17 00:05:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260217_0005"
down_revision = "20260217_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("metric_type", sa.String(length=40), nullable=False),
        sa.Column("comparator", sa.String(length=3), nullable=False, server_default=sa.text("'gte'")),
        sa.Column("target_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("alert_threshold_pct", sa.SmallInteger(), nullable=False, server_default=sa.text("80")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("target_value >= 0", name="ck_goals_goal_target_non_negative"),
        sa.CheckConstraint("alert_threshold_pct >= 1 AND alert_threshold_pct <= 100", name="ck_goals_goal_alert_threshold_range"),
        sa.CheckConstraint("comparator IN ('gte', 'lte')", name="ck_goals_goal_comparator_allowed"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_goals_gym_id", "goals", ["gym_id"], unique=False)
    op.create_index("ix_goals_gym_period", "goals", ["gym_id", "period_start", "period_end"], unique=False)
    op.create_index("ix_goals_active_metric", "goals", ["is_active", "metric_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_goals_active_metric", table_name="goals")
    op.drop_index("ix_goals_gym_period", table_name="goals")
    op.drop_index("ix_goals_gym_id", table_name="goals")
    op.drop_table("goals")
