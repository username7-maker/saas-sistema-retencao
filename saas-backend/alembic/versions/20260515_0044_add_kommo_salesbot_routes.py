"""add kommo salesbot routes

Revision ID: 20260515_0044
Revises: 20260513_0043
Create Date: 2026-05-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260515_0044"
down_revision: str | None = "20260513_0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kommo_domain_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(length=40), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("pipeline_id", sa.String(length=40), nullable=True),
        sa.Column("stage_id", sa.String(length=40), nullable=True),
        sa.Column("salesbot_id", sa.String(length=40), nullable=True),
        sa.Column("channel_source_id", sa.String(length=80), nullable=True),
        sa.Column("responsible_user_id", sa.String(length=40), nullable=True),
        sa.Column("message_field_id", sa.String(length=40), nullable=True),
        sa.Column("pdf_url_field_id", sa.String(length=40), nullable=True),
        sa.Column("source_type_field_id", sa.String(length=40), nullable=True),
        sa.Column("source_id_field_id", sa.String(length=40), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "domain", name="uq_kommo_domain_routes_gym_domain"),
    )
    op.create_index("ix_kommo_domain_routes_gym_id", "kommo_domain_routes", ["gym_id"], unique=False)
    op.create_index("ix_kommo_domain_routes_gym_domain", "kommo_domain_routes", ["gym_id", "domain"], unique=False)
    op.create_index("ix_kommo_domain_routes_gym_enabled", "kommo_domain_routes", ["gym_id", "is_enabled"], unique=False)

    op.create_table(
        "kommo_member_domain_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(length=40), nullable=False),
        sa.Column("kommo_contact_id", sa.String(length=40), nullable=True),
        sa.Column("kommo_lead_id", sa.String(length=40), nullable=True),
        sa.Column("last_salesbot_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_handoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_action_type", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "member_id", "domain", name="uq_kommo_member_domain_links_gym_member_domain"),
    )
    op.create_index("ix_kommo_member_domain_links_gym_id", "kommo_member_domain_links", ["gym_id"], unique=False)
    op.create_index("ix_kommo_member_domain_links_member_id", "kommo_member_domain_links", ["member_id"], unique=False)
    op.create_index(
        "ix_kommo_member_domain_links_gym_domain_lead",
        "kommo_member_domain_links",
        ["gym_id", "domain", "kommo_lead_id"],
        unique=False,
    )
    op.create_index(
        "ix_kommo_member_domain_links_gym_domain_contact",
        "kommo_member_domain_links",
        ["gym_id", "domain", "kommo_contact_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_kommo_member_domain_links_gym_domain_contact", table_name="kommo_member_domain_links")
    op.drop_index("ix_kommo_member_domain_links_gym_domain_lead", table_name="kommo_member_domain_links")
    op.drop_index("ix_kommo_member_domain_links_member_id", table_name="kommo_member_domain_links")
    op.drop_index("ix_kommo_member_domain_links_gym_id", table_name="kommo_member_domain_links")
    op.drop_table("kommo_member_domain_links")

    op.drop_index("ix_kommo_domain_routes_gym_enabled", table_name="kommo_domain_routes")
    op.drop_index("ix_kommo_domain_routes_gym_domain", table_name="kommo_domain_routes")
    op.drop_index("ix_kommo_domain_routes_gym_id", table_name="kommo_domain_routes")
    op.drop_table("kommo_domain_routes")
