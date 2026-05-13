"""expand user avatar url

Revision ID: 20260513_0043
Revises: 20260512_0042
Create Date: 2026-05-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260513_0043"
down_revision: str | None = "20260512_0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "avatar_url", existing_type=sa.String(length=500), type_=sa.Text(), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "avatar_url", existing_type=sa.Text(), type_=sa.String(length=500), nullable=True)
