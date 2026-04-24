"""add core async jobs

Revision ID: 20260401_0029
Revises: 20260331_0028
Create Date: 2026-04-01 09:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260401_0029"
down_revision = "20260331_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "core_async_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_entity_type", sa.String(length=64), nullable=True),
        sa.Column("job_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("payload_blob", sa.Text(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message_redacted", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'retry_scheduled')",
            name="core_async_jobs_status_valid",
        ),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_core_async_jobs")),
    )
    op.create_index("ix_core_async_jobs_gym_status_created", "core_async_jobs", ["gym_id", "status", "created_at"], unique=False)
    op.create_index("ix_core_async_jobs_status_retry_created", "core_async_jobs", ["status", "next_retry_at", "created_at"], unique=False)
    op.create_index("ix_core_async_jobs_type_entity", "core_async_jobs", ["job_type", "related_entity_type", "related_entity_id"], unique=False)
    op.create_index("ix_core_async_jobs_type_idempotency", "core_async_jobs", ["job_type", "idempotency_key"], unique=False)
    op.create_index(op.f("ix_core_async_jobs_gym_id"), "core_async_jobs", ["gym_id"], unique=False)
    op.create_index(op.f("ix_core_async_jobs_job_type"), "core_async_jobs", ["job_type"], unique=False)
    op.create_index(op.f("ix_core_async_jobs_related_entity_id"), "core_async_jobs", ["related_entity_id"], unique=False)
    op.create_index(op.f("ix_core_async_jobs_requested_by_user_id"), "core_async_jobs", ["requested_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_core_async_jobs_requested_by_user_id"), table_name="core_async_jobs")
    op.drop_index(op.f("ix_core_async_jobs_related_entity_id"), table_name="core_async_jobs")
    op.drop_index(op.f("ix_core_async_jobs_job_type"), table_name="core_async_jobs")
    op.drop_index(op.f("ix_core_async_jobs_gym_id"), table_name="core_async_jobs")
    op.drop_index("ix_core_async_jobs_type_idempotency", table_name="core_async_jobs")
    op.drop_index("ix_core_async_jobs_type_entity", table_name="core_async_jobs")
    op.drop_index("ix_core_async_jobs_status_retry_created", table_name="core_async_jobs")
    op.drop_index("ix_core_async_jobs_gym_status_created", table_name="core_async_jobs")
    op.drop_table("core_async_jobs")
