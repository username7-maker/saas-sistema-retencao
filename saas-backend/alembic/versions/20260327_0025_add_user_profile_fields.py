"""add user profile fields

Revision ID: 20260327_0025
Revises: 20260325_0024
Create Date: 2026-03-27 00:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260327_0025"
down_revision = "20260325_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("job_title", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "job_title")
