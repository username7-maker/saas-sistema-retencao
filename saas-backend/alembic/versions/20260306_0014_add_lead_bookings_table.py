"""add lead_bookings table

Revision ID: 20260306_0014
Revises: 20260305_0013
Create Date: 2026-03-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "20260306_0014"
down_revision = "20260305_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_bookings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("gym_id", UUID(as_uuid=True), sa.ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_name", sa.String(length=40), nullable=True),
        sa.Column("provider_booking_id", sa.String(length=120), nullable=True),
        sa.Column("prospect_name", sa.String(length=120), nullable=False),
        sa.Column("prospect_email", sa.String(length=255), nullable=True),
        sa.Column("prospect_whatsapp", sa.String(length=32), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="confirmed"),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", JSONB(), nullable=False, server_default="{}"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_lead_bookings_gym_id", "lead_bookings", ["gym_id"])
    op.create_index("ix_lead_bookings_lead_id", "lead_bookings", ["lead_id"])
    op.create_index("ix_lead_bookings_provider_booking_id", "lead_bookings", ["provider_booking_id"])
    op.create_index("ix_lead_bookings_prospect_email", "lead_bookings", ["prospect_email"])
    op.create_index("ix_lead_bookings_scheduled_for", "lead_bookings", ["scheduled_for"])
    op.create_index("ix_lead_bookings_gym_scheduled", "lead_bookings", ["gym_id", "scheduled_for"])
    op.create_index("ix_lead_bookings_lead_status", "lead_bookings", ["lead_id", "status"])
    op.create_index("ix_lead_bookings_status_reminder", "lead_bookings", ["status", "reminder_sent_at"])


def downgrade() -> None:
    op.drop_index("ix_lead_bookings_status_reminder", table_name="lead_bookings")
    op.drop_index("ix_lead_bookings_lead_status", table_name="lead_bookings")
    op.drop_index("ix_lead_bookings_gym_scheduled", table_name="lead_bookings")
    op.drop_index("ix_lead_bookings_scheduled_for", table_name="lead_bookings")
    op.drop_index("ix_lead_bookings_prospect_email", table_name="lead_bookings")
    op.drop_index("ix_lead_bookings_provider_booking_id", table_name="lead_bookings")
    op.drop_index("ix_lead_bookings_lead_id", table_name="lead_bookings")
    op.drop_index("ix_lead_bookings_gym_id", table_name="lead_bookings")
    op.drop_table("lead_bookings")
