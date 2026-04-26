"""add financial entries

Revision ID: 20260426_0034
Revises: 20260426_0033
Create Date: 2026-04-26 19:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260426_0034"
down_revision: str | None = "20260426_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "financial_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("external_ref", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount >= 0", name="financial_entry_amount_non_negative"),
        sa.CheckConstraint(
            "entry_type in ('receivable', 'payable', 'cash_in', 'cash_out')",
            name="financial_entry_type_check",
        ),
        sa.CheckConstraint(
            "status in ('open', 'paid', 'overdue', 'cancelled')",
            name="financial_entry_status_check",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_entries_gym_id", "financial_entries", ["gym_id"])
    op.create_index(
        "ix_financial_entries_gym_type_status",
        "financial_entries",
        ["gym_id", "entry_type", "status"],
    )
    op.create_index("ix_financial_entries_gym_due", "financial_entries", ["gym_id", "due_date"])
    op.create_index("ix_financial_entries_gym_occurred", "financial_entries", ["gym_id", "occurred_at"])
    op.create_index("ix_financial_entries_member", "financial_entries", ["member_id"])
    op.create_index("ix_financial_entries_lead", "financial_entries", ["lead_id"])
    op.create_index("ix_financial_entries_created_by_user_id", "financial_entries", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_financial_entries_created_by_user_id", table_name="financial_entries")
    op.drop_index("ix_financial_entries_lead", table_name="financial_entries")
    op.drop_index("ix_financial_entries_member", table_name="financial_entries")
    op.drop_index("ix_financial_entries_gym_occurred", table_name="financial_entries")
    op.drop_index("ix_financial_entries_gym_due", table_name="financial_entries")
    op.drop_index("ix_financial_entries_gym_type_status", table_name="financial_entries")
    op.drop_index("ix_financial_entries_gym_id", table_name="financial_entries")
    op.drop_table("financial_entries")
