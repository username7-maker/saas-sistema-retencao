"""add member consent records

Revision ID: 20260426_0033
Revises: 20260423_0032
Create Date: 2026-04-26 15:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260426_0033"
down_revision = "20260423_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member_consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="accepted", nullable=False),
        sa.Column("source", sa.String(length=80), server_default="manual", nullable=False),
        sa.Column("document_title", sa.String(length=160), nullable=True),
        sa.Column("document_version", sa.String(length=80), nullable=True),
        sa.Column("evidence_ref", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_member_consent_records_gym_id", "member_consent_records", ["gym_id"], unique=False)
    op.create_index("ix_member_consent_records_member_id", "member_consent_records", ["member_id"], unique=False)
    op.create_index(
        "ix_member_consent_records_gym_member",
        "member_consent_records",
        ["gym_id", "member_id"],
        unique=False,
    )
    op.create_index(
        "ix_member_consent_records_member_type_created",
        "member_consent_records",
        ["member_id", "consent_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_member_consent_records_expiration",
        "member_consent_records",
        ["gym_id", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_member_consent_records_expiration", table_name="member_consent_records")
    op.drop_index("ix_member_consent_records_member_type_created", table_name="member_consent_records")
    op.drop_index("ix_member_consent_records_gym_member", table_name="member_consent_records")
    op.drop_index("ix_member_consent_records_member_id", table_name="member_consent_records")
    op.drop_index("ix_member_consent_records_gym_id", table_name="member_consent_records")
    op.drop_table("member_consent_records")
