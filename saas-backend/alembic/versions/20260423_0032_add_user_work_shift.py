"""add user work shift

Revision ID: 20260423_0032
Revises: 20260418_0031
Create Date: 2026-04-23 11:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260423_0032"
down_revision = "20260418_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("work_shift", sa.String(length=24), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "work_shift")
