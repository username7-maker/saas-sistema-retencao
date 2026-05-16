"""add kommo native file upload

Revision ID: 20260515_0045
Revises: 20260515_0044
Create Date: 2026-05-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260515_0045"
down_revision: str | None = "20260515_0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "kommo_domain_routes",
        sa.Column("pdf_delivery_mode", sa.String(length=40), server_default="native_file_required", nullable=False),
    )
    op.add_column("kommo_domain_routes", sa.Column("file_uuid_field_id", sa.String(length=40), nullable=True))
    op.add_column("kommo_domain_routes", sa.Column("file_name_field_id", sa.String(length=40), nullable=True))
    op.add_column("kommo_domain_routes", sa.Column("file_attachment_note_field_id", sa.String(length=40), nullable=True))

    op.create_table(
        "kommo_file_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("domain", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("kommo_lead_id", sa.String(length=40), nullable=True),
        sa.Column("kommo_contact_id", sa.String(length=40), nullable=True),
        sa.Column("file_uuid", sa.String(length=120), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("upload_status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("attach_status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("delivery_status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "domain", "source_type", "source_id", name="uq_kommo_file_attachments_source"),
    )
    op.create_index("ix_kommo_file_attachments_gym_id", "kommo_file_attachments", ["gym_id"], unique=False)
    op.create_index("ix_kommo_file_attachments_member_id", "kommo_file_attachments", ["member_id"], unique=False)
    op.create_index("ix_kommo_file_attachments_gym_member", "kommo_file_attachments", ["gym_id", "member_id"], unique=False)
    op.create_index("ix_kommo_file_attachments_gym_lead", "kommo_file_attachments", ["gym_id", "kommo_lead_id"], unique=False)
    op.create_index(
        "ix_kommo_file_attachments_gym_status",
        "kommo_file_attachments",
        ["gym_id", "upload_status", "attach_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_kommo_file_attachments_gym_status", table_name="kommo_file_attachments")
    op.drop_index("ix_kommo_file_attachments_gym_lead", table_name="kommo_file_attachments")
    op.drop_index("ix_kommo_file_attachments_gym_member", table_name="kommo_file_attachments")
    op.drop_index("ix_kommo_file_attachments_member_id", table_name="kommo_file_attachments")
    op.drop_index("ix_kommo_file_attachments_gym_id", table_name="kommo_file_attachments")
    op.drop_table("kommo_file_attachments")

    op.drop_column("kommo_domain_routes", "file_attachment_note_field_id")
    op.drop_column("kommo_domain_routes", "file_name_field_id")
    op.drop_column("kommo_domain_routes", "file_uuid_field_id")
    op.drop_column("kommo_domain_routes", "pdf_delivery_mode")
