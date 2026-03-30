"""add kommo settings and links

Revision ID: 20260330_0026
Revises: 20260327_0025
Create Date: 2026-03-30 20:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260330_0026"
down_revision = "20260327_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gyms", sa.Column("kommo_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("gyms", sa.Column("kommo_base_url", sa.String(length=255), nullable=True))
    op.add_column("gyms", sa.Column("kommo_access_token_encrypted", sa.Text(), nullable=True))
    op.add_column("gyms", sa.Column("kommo_default_pipeline_id", sa.String(length=40), nullable=True))
    op.add_column("gyms", sa.Column("kommo_default_stage_id", sa.String(length=40), nullable=True))
    op.add_column("gyms", sa.Column("kommo_default_responsible_user_id", sa.String(length=40), nullable=True))

    op.create_table(
        "kommo_member_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kommo_contact_id", sa.String(length=40), nullable=True),
        sa.Column("kommo_lead_id", sa.String(length=40), nullable=True),
        sa.Column("last_handoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_action_type", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "member_id", name="uq_kommo_member_links_gym_member"),
    )
    op.create_index("ix_kommo_member_links_gym_id", "kommo_member_links", ["gym_id"], unique=False)
    op.create_index("ix_kommo_member_links_member_id", "kommo_member_links", ["member_id"], unique=False)
    op.create_index("ix_kommo_member_links_gym_lead", "kommo_member_links", ["gym_id", "kommo_lead_id"], unique=False)
    op.create_index("ix_kommo_member_links_gym_contact", "kommo_member_links", ["gym_id", "kommo_contact_id"], unique=False)

    op.alter_column("gyms", "kommo_enabled", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_kommo_member_links_gym_contact", table_name="kommo_member_links")
    op.drop_index("ix_kommo_member_links_gym_lead", table_name="kommo_member_links")
    op.drop_index("ix_kommo_member_links_member_id", table_name="kommo_member_links")
    op.drop_index("ix_kommo_member_links_gym_id", table_name="kommo_member_links")
    op.drop_table("kommo_member_links")

    op.drop_column("gyms", "kommo_default_responsible_user_id")
    op.drop_column("gyms", "kommo_default_stage_id")
    op.drop_column("gyms", "kommo_default_pipeline_id")
    op.drop_column("gyms", "kommo_access_token_encrypted")
    op.drop_column("gyms", "kommo_base_url")
    op.drop_column("gyms", "kommo_enabled")
