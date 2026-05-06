"""add member notes

Revision ID: 20260505_0039
Revises: 20260504_0038
Create Date: 2026-05-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260505_0039"
down_revision: str | None = "20260504_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "member_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note_type", sa.String(length=40), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(length=40), nullable=False),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_member_notes_author_created", "member_notes", ["author_user_id", "created_at"])
    op.create_index("ix_member_notes_author_user_id", "member_notes", ["author_user_id"])
    op.create_index("ix_member_notes_deleted_at", "member_notes", ["deleted_at"])
    op.create_index("ix_member_notes_gym_id", "member_notes", ["gym_id"])
    op.create_index("ix_member_notes_gym_member_created", "member_notes", ["gym_id", "member_id", "created_at"])
    op.create_index("ix_member_notes_gym_type_created", "member_notes", ["gym_id", "note_type", "created_at"])
    op.create_index("ix_member_notes_member_id", "member_notes", ["member_id"])


def downgrade() -> None:
    op.drop_index("ix_member_notes_member_id", table_name="member_notes")
    op.drop_index("ix_member_notes_gym_type_created", table_name="member_notes")
    op.drop_index("ix_member_notes_gym_member_created", table_name="member_notes")
    op.drop_index("ix_member_notes_gym_id", table_name="member_notes")
    op.drop_index("ix_member_notes_deleted_at", table_name="member_notes")
    op.drop_index("ix_member_notes_author_user_id", table_name="member_notes")
    op.drop_index("ix_member_notes_author_created", table_name="member_notes")
    op.drop_table("member_notes")
