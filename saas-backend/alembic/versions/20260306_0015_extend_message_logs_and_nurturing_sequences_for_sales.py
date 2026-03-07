"""extend message logs and nurturing sequences for sales

Revision ID: 20260306_0015
Revises: 20260306_0014
Create Date: 2026-03-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision = "20260306_0015"
down_revision = "20260306_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("message_logs", sa.Column("lead_id", UUID(as_uuid=True), nullable=True))
    op.add_column("message_logs", sa.Column("direction", sa.String(length=20), nullable=True))
    op.add_column("message_logs", sa.Column("event_type", sa.String(length=80), nullable=True))
    op.add_column("message_logs", sa.Column("provider_message_id", sa.String(length=120), nullable=True))
    op.create_foreign_key(
        "fk_message_logs_lead_id_leads",
        "message_logs",
        "leads",
        ["lead_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_message_logs_lead_id", "message_logs", ["lead_id"])
    op.create_index("ix_message_logs_lead_channel", "message_logs", ["lead_id", "channel"])

    op.add_column("nurturing_sequences", sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("nurturing_sequences", sa.Column("paused_reason", sa.Text(), nullable=True))
    op.create_index("ix_nurturing_sequences_paused", "nurturing_sequences", ["paused_at"])


def downgrade() -> None:
    op.drop_index("ix_nurturing_sequences_paused", table_name="nurturing_sequences")
    op.drop_column("nurturing_sequences", "paused_reason")
    op.drop_column("nurturing_sequences", "paused_at")

    op.drop_index("ix_message_logs_lead_channel", table_name="message_logs")
    op.drop_index("ix_message_logs_lead_id", table_name="message_logs")
    op.drop_constraint("fk_message_logs_lead_id_leads", "message_logs", type_="foreignkey")
    op.drop_column("message_logs", "provider_message_id")
    op.drop_column("message_logs", "event_type")
    op.drop_column("message_logs", "direction")
    op.drop_column("message_logs", "lead_id")
