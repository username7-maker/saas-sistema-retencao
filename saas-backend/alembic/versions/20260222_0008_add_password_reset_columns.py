"""add password reset columns to users

Revision ID: 20260222_0008
Revises: 20260217_0007
Create Date: 2026-02-22 10:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260222_0008"
down_revision = "20260217_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_reset_token_hash", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_reset_expires_at")
    op.drop_column("users", "password_reset_token_hash")
