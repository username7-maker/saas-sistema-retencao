"""add nurturing_sequences table

Revision ID: 20260305_0011
Revises: 20260305_0010
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "20260305_0011"
down_revision = "20260305_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nurturing_sequences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("gym_id", UUID(as_uuid=True), sa.ForeignKey("gyms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("prospect_email", sa.String(length=255), nullable=False),
        sa.Column("prospect_whatsapp", sa.String(length=32), nullable=False),
        sa.Column("prospect_name", sa.String(length=120), nullable=False),
        sa.Column("diagnosis_data", JSONB(), nullable=False, server_default="{}"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_send_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_nurturing_sequences_completed", "nurturing_sequences", ["completed"])
    op.create_index("ix_nurturing_sequences_gym_id", "nurturing_sequences", ["gym_id"])
    op.create_index("ix_nurturing_sequences_lead_id", "nurturing_sequences", ["lead_id"])
    op.create_index("ix_nurturing_sequences_next_send_at", "nurturing_sequences", ["next_send_at"])
    op.create_index(
        "ix_nurturing_sequences_due_open",
        "nurturing_sequences",
        ["completed", "next_send_at"],
    )
    op.create_index(
        "ix_nurturing_sequences_gym_due",
        "nurturing_sequences",
        ["gym_id", "next_send_at"],
    )
    op.create_index("ix_nurturing_sequences_lead", "nurturing_sequences", ["lead_id"])


def downgrade() -> None:
    op.drop_index("ix_nurturing_sequences_lead", table_name="nurturing_sequences")
    op.drop_index("ix_nurturing_sequences_gym_due", table_name="nurturing_sequences")
    op.drop_index("ix_nurturing_sequences_due_open", table_name="nurturing_sequences")
    op.drop_index("ix_nurturing_sequences_next_send_at", table_name="nurturing_sequences")
    op.drop_index("ix_nurturing_sequences_lead_id", table_name="nurturing_sequences")
    op.drop_index("ix_nurturing_sequences_gym_id", table_name="nurturing_sequences")
    op.drop_index("ix_nurturing_sequences_completed", table_name="nurturing_sequences")
    op.drop_table("nurturing_sequences")
