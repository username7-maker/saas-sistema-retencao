"""message templates, on-demand AI composition, and WhatsApp outbound gate

Revision ID: 20260904_0060
Revises: 20260901_0059
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260904_0060"
down_revision = "20260901_0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gyms",
        sa.Column("whatsapp_outbound_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_table(
        "gym_message_template_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_key", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "template_key", name="uq_gym_message_template_override_key"),
    )
    op.create_index("ix_gym_message_template_override_gym_active", "gym_message_template_overrides", ["gym_id", "is_active"])
    op.create_index("ix_gym_message_template_overrides_gym_id", "gym_message_template_overrides", ["gym_id"])
    op.create_table(
        "message_composition_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=180), nullable=False),
        sa.Column("template_key", sa.String(length=100), nullable=False),
        sa.Column("objective", sa.String(length=280), nullable=False),
        sa.Column("base_message", sa.Text(), nullable=False),
        sa.Column("improved_message", sa.Text(), nullable=True),
        sa.Column("base_hash", sa.String(length=64), nullable=False),
        sa.Column("improved_hash", sa.String(length=64), nullable=True),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'previewed'"), nullable=False),
        sa.Column("provider", sa.String(length=32), server_default=sa.text("'system'"), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("prompt_key", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fallback_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("warnings_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "idempotency_key", name="uq_message_composition_gym_idempotency"),
    )
    op.create_index("ix_message_composition_gym_created", "message_composition_requests", ["gym_id", "created_at"])
    op.create_index("ix_message_composition_gym_status", "message_composition_requests", ["gym_id", "status"])
    op.create_index("ix_message_composition_requests_gym_id", "message_composition_requests", ["gym_id"])
    op.create_index("ix_message_composition_requests_requested_by_user_id", "message_composition_requests", ["requested_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_message_composition_requests_requested_by_user_id", table_name="message_composition_requests")
    op.drop_index("ix_message_composition_requests_gym_id", table_name="message_composition_requests")
    op.drop_index("ix_message_composition_gym_status", table_name="message_composition_requests")
    op.drop_index("ix_message_composition_gym_created", table_name="message_composition_requests")
    op.drop_table("message_composition_requests")
    op.drop_index("ix_gym_message_template_overrides_gym_id", table_name="gym_message_template_overrides")
    op.drop_index("ix_gym_message_template_override_gym_active", table_name="gym_message_template_overrides")
    op.drop_table("gym_message_template_overrides")
    op.drop_column("gyms", "whatsapp_outbound_enabled")
