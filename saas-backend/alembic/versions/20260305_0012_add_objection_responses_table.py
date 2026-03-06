"""add objection_responses table

Revision ID: 20260305_0012
Revises: 20260305_0011
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "20260305_0012"
down_revision = "20260305_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "objection_responses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("gym_id", UUID(as_uuid=True), sa.ForeignKey("gyms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("trigger_keywords", JSONB(), nullable=False, server_default="[]"),
        sa.Column("objection_summary", sa.Text(), nullable=False),
        sa.Column("response_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_objection_responses_gym_id", "objection_responses", ["gym_id"])
    op.create_index(
        "ix_objection_responses_gym_active",
        "objection_responses",
        ["gym_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_objection_responses_gym_active", table_name="objection_responses")
    op.drop_index("ix_objection_responses_gym_id", table_name="objection_responses")
    op.drop_table("objection_responses")
