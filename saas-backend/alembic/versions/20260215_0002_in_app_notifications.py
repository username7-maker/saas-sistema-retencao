"""add in_app_notifications table

Revision ID: 20260215_0002
Revises: 20260214_0001
Create Date: 2026-02-15 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260215_0002"
down_revision = "20260214_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "in_app_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False, server_default=sa.text("'retention'")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_in_app_notifications_member_id", "in_app_notifications", ["member_id"], unique=False)
    op.create_index("ix_in_app_notifications_user_id", "in_app_notifications", ["user_id"], unique=False)
    op.create_index(
        "ix_in_app_notifications_user_read",
        "in_app_notifications",
        ["user_id", "read_at"],
        unique=False,
    )
    op.create_index(
        "ix_in_app_notifications_member_created",
        "in_app_notifications",
        ["member_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_in_app_notifications_member_created", table_name="in_app_notifications")
    op.drop_index("ix_in_app_notifications_user_read", table_name="in_app_notifications")
    op.drop_index("ix_in_app_notifications_user_id", table_name="in_app_notifications")
    op.drop_index("ix_in_app_notifications_member_id", table_name="in_app_notifications")
    op.drop_table("in_app_notifications")
