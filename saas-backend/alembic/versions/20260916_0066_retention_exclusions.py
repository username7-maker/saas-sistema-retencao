"""Add reversible retention exclusions.

Revision ID: 20260916_0066
Revises: 20260915_0065
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260916_0066"
down_revision: str | None = "20260915_0065"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retention_exclusions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("plan_name", sa.String(length=100), nullable=True),
        sa.Column("normalized_plan_name", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "(scope = 'member' AND member_id IS NOT NULL AND plan_name IS NULL AND normalized_plan_name IS NULL) OR "
            "(scope = 'plan' AND member_id IS NULL AND plan_name IS NOT NULL AND normalized_plan_name IS NOT NULL)",
            name="ck_retention_exclusions_target",
        ),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_retention_exclusions_gym_id", "retention_exclusions", ["gym_id"])
    op.create_index("ix_retention_exclusions_member_id", "retention_exclusions", ["member_id"])
    op.create_index("ix_retention_exclusions_gym_active", "retention_exclusions", ["gym_id", "revoked_at"])
    op.create_index(
        "ux_retention_exclusions_active_member",
        "retention_exclusions",
        ["gym_id", "member_id"],
        unique=True,
        postgresql_where=sa.text("scope = 'member' AND revoked_at IS NULL"),
    )
    op.create_index(
        "ux_retention_exclusions_active_plan",
        "retention_exclusions",
        ["gym_id", "normalized_plan_name"],
        unique=True,
        postgresql_where=sa.text("scope = 'plan' AND revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("retention_exclusions")
