"""fix actuar bridge device timestamps

Revision ID: 20260331_0028
Revises: 20260330_0027
Create Date: 2026-03-31 12:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260331_0028"
down_revision = "20260330_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE actuar_bridge_devices
        SET created_at = COALESCE(created_at, NOW()),
            updated_at = COALESCE(updated_at, NOW())
        WHERE created_at IS NULL OR updated_at IS NULL
        """
    )
    op.alter_column(
        "actuar_bridge_devices",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("NOW()"),
        existing_nullable=False,
    )
    op.alter_column(
        "actuar_bridge_devices",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("NOW()"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "actuar_bridge_devices",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False,
    )
    op.alter_column(
        "actuar_bridge_devices",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False,
    )
