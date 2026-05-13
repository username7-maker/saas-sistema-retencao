"""add movement video reviews

Revision ID: 20260507_0041
Revises: 20260506_0040
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260507_0041"
down_revision: str | None = "20260506_0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "movement_video_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trainer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("exercise_name", sa.String(length=120), nullable=False),
        sa.Column("video_asset_url", sa.Text(), nullable=True),
        sa.Column("video_asset_hash", sa.String(length=128), nullable=True),
        sa.Column("media_type", sa.String(length=80), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("original_video_stored", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("analysis_status", sa.String(length=32), nullable=False),
        sa.Column("safety_level", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("detected_points", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("suggested_feedback", sa.Text(), nullable=True),
        sa.Column("coach_feedback", sa.Text(), nullable=True),
        sa.Column("blocked_reasons", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trainer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_movement_video_reviews_gym_id", "movement_video_reviews", ["gym_id"])
    op.create_index("ix_movement_video_reviews_member_id", "movement_video_reviews", ["member_id"])
    op.create_index("ix_movement_video_reviews_trainer_user_id", "movement_video_reviews", ["trainer_user_id"])
    op.create_index("ix_movement_video_reviews_status", "movement_video_reviews", ["status"])
    op.create_index("ix_movement_video_reviews_analysis_status", "movement_video_reviews", ["analysis_status"])
    op.create_index(
        "ix_movement_video_reviews_gym_member_created",
        "movement_video_reviews",
        ["gym_id", "member_id", "created_at"],
    )
    op.create_index("ix_movement_video_reviews_gym_status", "movement_video_reviews", ["gym_id", "status"])
    op.create_index(
        "ix_movement_video_reviews_trainer_status",
        "movement_video_reviews",
        ["trainer_user_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_movement_video_reviews_trainer_status", table_name="movement_video_reviews")
    op.drop_index("ix_movement_video_reviews_gym_status", table_name="movement_video_reviews")
    op.drop_index("ix_movement_video_reviews_gym_member_created", table_name="movement_video_reviews")
    op.drop_index("ix_movement_video_reviews_analysis_status", table_name="movement_video_reviews")
    op.drop_index("ix_movement_video_reviews_status", table_name="movement_video_reviews")
    op.drop_index("ix_movement_video_reviews_trainer_user_id", table_name="movement_video_reviews")
    op.drop_index("ix_movement_video_reviews_member_id", table_name="movement_video_reviews")
    op.drop_index("ix_movement_video_reviews_gym_id", table_name="movement_video_reviews")
    op.drop_table("movement_video_reviews")
