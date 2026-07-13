"""work queue concurrency safe effects

Revision ID: 20260713_0050
Revises: 20260707_0049
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260713_0050"
down_revision: str | None = "20260707_0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("work_dedupe_key", sa.String(length=220), nullable=True))
    op.create_index(op.f("ix_tasks_work_dedupe_key"), "tasks", ["work_dedupe_key"], unique=False)
    op.create_index(
        "uq_tasks_active_work_dedupe",
        "tasks",
        ["gym_id", "work_dedupe_key"],
        unique=True,
        postgresql_where=sa.text(
            "work_dedupe_key IS NOT NULL "
            "AND deleted_at IS NULL "
            "AND status NOT IN ('done', 'cancelled') "
            "AND COALESCE(extra_data->'operational_archive'->>'archived_at', '') = ''"
        ),
    )

    op.create_table(
        "work_queue_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claimed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("last_action", sa.String(length=60), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["claimed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "source_type", "source_id", name="uq_work_queue_claim_source"),
    )
    op.create_index("ix_work_queue_claims_claimant", "work_queue_claims", ["gym_id", "claimed_by_user_id"], unique=False)
    op.create_index("ix_work_queue_claims_gym_id", "work_queue_claims", ["gym_id"], unique=False)
    op.create_index(
        "ix_work_queue_claims_gym_source",
        "work_queue_claims",
        ["gym_id", "source_type", "source_id"],
        unique=False,
    )
    op.create_index("ix_work_queue_claims_claimed_by_user_id", "work_queue_claims", ["claimed_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_work_queue_claims_claimed_by_user_id", table_name="work_queue_claims")
    op.drop_index("ix_work_queue_claims_gym_source", table_name="work_queue_claims")
    op.drop_index("ix_work_queue_claims_gym_id", table_name="work_queue_claims")
    op.drop_index("ix_work_queue_claims_claimant", table_name="work_queue_claims")
    op.drop_table("work_queue_claims")
    op.drop_index("uq_tasks_active_work_dedupe", table_name="tasks")
    op.drop_index(op.f("ix_tasks_work_dedupe_key"), table_name="tasks")
    op.drop_column("tasks", "work_dedupe_key")
