"""Add durable risk recalculation requests

Revision ID: 20260325_0024
Revises: 20260323_0023
Create Date: 2026-03-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260325_0024"
down_revision = "20260323_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_recalculation_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="risk_recalculation_requests_status_valid",
        ),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_recalculation_requests")),
    )
    op.create_index(
        "ix_risk_recalc_requests_gym_status_created",
        "risk_recalculation_requests",
        ["gym_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_risk_recalc_requests_status_locked",
        "risk_recalculation_requests",
        ["status", "locked_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_recalculation_requests_gym_id"),
        "risk_recalculation_requests",
        ["gym_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_recalculation_requests_requested_by_user_id"),
        "risk_recalculation_requests",
        ["requested_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_risk_recalculation_requests_requested_by_user_id"), table_name="risk_recalculation_requests")
    op.drop_index(op.f("ix_risk_recalculation_requests_gym_id"), table_name="risk_recalculation_requests")
    op.drop_index("ix_risk_recalc_requests_status_locked", table_name="risk_recalculation_requests")
    op.drop_index("ix_risk_recalc_requests_gym_status_created", table_name="risk_recalculation_requests")
    op.drop_table("risk_recalculation_requests")
