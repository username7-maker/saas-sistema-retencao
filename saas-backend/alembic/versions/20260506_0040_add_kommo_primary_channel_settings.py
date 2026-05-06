"""add kommo primary channel settings

Revision ID: 20260506_0040
Revises: 20260505_0039
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260506_0040"
down_revision: str | None = "20260505_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("gyms", sa.Column("primary_message_channel", sa.String(length=20), server_default="whatsapp", nullable=False))
    op.add_column("gyms", sa.Column("kommo_operator_confirmed_send_enabled", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("gyms", sa.Column("kommo_auto_close_enabled", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("gyms", sa.Column("kommo_fallback_channel", sa.String(length=20), server_default="whatsapp", nullable=False))


def downgrade() -> None:
    op.drop_column("gyms", "kommo_fallback_channel")
    op.drop_column("gyms", "kommo_auto_close_enabled")
    op.drop_column("gyms", "kommo_operator_confirmed_send_enabled")
    op.drop_column("gyms", "primary_message_channel")
