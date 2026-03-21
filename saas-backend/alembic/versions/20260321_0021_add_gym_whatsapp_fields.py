"""add whatsapp fields to gyms

Revision ID: 20260321_0021
Revises: 20260317_0020
"""
from alembic import op
import sqlalchemy as sa


revision = "20260321_0021"
down_revision = "20260317_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gyms",
        sa.Column(
            "whatsapp_instance",
            sa.String(120),
            nullable=True,
            comment="Nome da instancia na Evolution API: gym_{uuid_sem_hifens}",
        ),
    )
    op.add_column(
        "gyms",
        sa.Column(
            "whatsapp_status",
            sa.String(30),
            nullable=False,
            server_default="disconnected",
            comment="disconnected | connecting | connected | error",
        ),
    )
    op.add_column(
        "gyms",
        sa.Column(
            "whatsapp_phone",
            sa.String(30),
            nullable=True,
            comment="Numero conectado, ex: 5511999999999",
        ),
    )
    op.add_column(
        "gyms",
        sa.Column("whatsapp_connected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_gyms_whatsapp_instance", "gyms", ["whatsapp_instance"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_gyms_whatsapp_instance", table_name="gyms")
    op.drop_column("gyms", "whatsapp_connected_at")
    op.drop_column("gyms", "whatsapp_phone")
    op.drop_column("gyms", "whatsapp_status")
    op.drop_column("gyms", "whatsapp_instance")
