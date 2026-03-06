"""add member_risk_history table and user phone column

Revision ID: 20260305_0010
Revises: 20260225_0009
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260305_0010"
down_revision = "20260225_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member_risk_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("gym_id", UUID(as_uuid=True), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", UUID(as_uuid=True), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("reasons", JSONB(), nullable=False, server_default="{}"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_member_risk_history_member_recorded", "member_risk_history", ["member_id", "recorded_at"])
    op.create_index("ix_member_risk_history_gym_recorded", "member_risk_history", ["gym_id", "recorded_at"])
    op.create_index("ix_member_risk_history_gym_id", "member_risk_history", ["gym_id"])
    op.create_index("ix_member_risk_history_member_id", "member_risk_history", ["member_id"])

    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone")
    op.drop_index("ix_member_risk_history_member_id", table_name="member_risk_history")
    op.drop_index("ix_member_risk_history_gym_id", table_name="member_risk_history")
    op.drop_index("ix_member_risk_history_gym_recorded", table_name="member_risk_history")
    op.drop_index("ix_member_risk_history_member_recorded", table_name="member_risk_history")
    op.drop_table("member_risk_history")
