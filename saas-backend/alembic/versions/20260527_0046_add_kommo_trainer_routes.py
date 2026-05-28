"""add kommo trainer routes

Revision ID: 20260527_0046
Revises: 20260515_0045
Create Date: 2026-05-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260527_0046"
down_revision: str | None = "20260515_0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kommo_trainer_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trainer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("pipeline_id", sa.String(length=40), nullable=True),
        sa.Column("stage_id", sa.String(length=40), nullable=True),
        sa.Column("salesbot_id", sa.String(length=40), nullable=True),
        sa.Column("channel_source_id", sa.String(length=80), nullable=True),
        sa.Column("responsible_user_id", sa.String(length=40), nullable=True),
        sa.Column("message_field_id", sa.String(length=40), nullable=True),
        sa.Column("pdf_url_field_id", sa.String(length=40), nullable=True),
        sa.Column("pdf_delivery_mode", sa.String(length=40), server_default="native_file_required", nullable=False),
        sa.Column("file_uuid_field_id", sa.String(length=40), nullable=True),
        sa.Column("file_name_field_id", sa.String(length=40), nullable=True),
        sa.Column("file_attachment_note_field_id", sa.String(length=40), nullable=True),
        sa.Column("source_type_field_id", sa.String(length=40), nullable=True),
        sa.Column("source_id_field_id", sa.String(length=40), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trainer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "trainer_user_id", name="uq_kommo_trainer_routes_gym_trainer"),
    )
    op.create_index("ix_kommo_trainer_routes_gym_id", "kommo_trainer_routes", ["gym_id"], unique=False)
    op.create_index("ix_kommo_trainer_routes_trainer_user_id", "kommo_trainer_routes", ["trainer_user_id"], unique=False)
    op.create_index("ix_kommo_trainer_routes_gym_trainer", "kommo_trainer_routes", ["gym_id", "trainer_user_id"], unique=False)
    op.create_index("ix_kommo_trainer_routes_gym_enabled", "kommo_trainer_routes", ["gym_id", "is_enabled"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_kommo_trainer_routes_gym_enabled", table_name="kommo_trainer_routes")
    op.drop_index("ix_kommo_trainer_routes_gym_trainer", table_name="kommo_trainer_routes")
    op.drop_index("ix_kommo_trainer_routes_trainer_user_id", table_name="kommo_trainer_routes")
    op.drop_index("ix_kommo_trainer_routes_gym_id", table_name="kommo_trainer_routes")
    op.drop_table("kommo_trainer_routes")
