"""Actuar sync v2 for body composition operational flow.

Revision ID: 20260323_0022
Revises: 20260321_0021
Create Date: 2026-03-23 15:20:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260323_0022"
down_revision = "20260321_0021"
branch_labels = None
depends_on = None
_ACTUAR_SYNC_JOB_FK = "fk_bce_actuar_sync_job_id"


def _drop_actuar_sync_status_constraints() -> None:
    op.execute(
        """
        DO $$
        DECLARE constraint_record record;
        BEGIN
            FOR constraint_record IN
                SELECT c.conname
                FROM pg_constraint AS c
                JOIN pg_class AS t ON t.oid = c.conrelid
                WHERE t.relname = 'body_composition_evaluations'
                  AND c.contype = 'c'
                  AND pg_get_constraintdef(c.oid) ILIKE '%actuar_sync_status%'
            LOOP
                EXECUTE format(
                    'ALTER TABLE body_composition_evaluations DROP CONSTRAINT IF EXISTS %I',
                    constraint_record.conname
                );
            END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    op.add_column("members", sa.Column("birthdate", sa.Date(), nullable=True))

    op.add_column("gyms", sa.Column("actuar_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("gyms", sa.Column("actuar_base_url", sa.String(length=255), nullable=True))
    op.add_column("gyms", sa.Column("actuar_username", sa.String(length=120), nullable=True))
    op.add_column("gyms", sa.Column("actuar_password_encrypted", sa.Text(), nullable=True))
    op.add_column("gyms", sa.Column("actuar_auto_sync_body_composition", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("gyms", sa.Column("actuar_notes_template", sa.Text(), nullable=True))
    op.add_column("gyms", sa.Column("actuar_required_match_strategy", sa.String(length=40), nullable=True))

    op.create_table(
        "actuar_member_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actuar_external_id", sa.String(length=120), nullable=True),
        sa.Column("actuar_search_name", sa.String(length=160), nullable=True),
        sa.Column("actuar_search_document", sa.Text(), nullable=True),
        sa.Column("actuar_search_birthdate", sa.Date(), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("match_confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_actuar_member_links_gym_member", "actuar_member_links", ["gym_id", "member_id"], unique=True)
    op.create_index(
        "ix_actuar_member_links_gym_external_active",
        "actuar_member_links",
        ["gym_id", "actuar_external_id"],
        unique=True,
        postgresql_where=sa.text("actuar_external_id IS NOT NULL"),
    )
    op.create_index("ix_actuar_member_links_gym_active", "actuar_member_links", ["gym_id", "is_active"])

    op.create_table(
        "actuar_sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body_composition_evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(length=40), nullable=False, server_default="body_composition_push"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("mapped_fields_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("critical_fields_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("non_critical_fields_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("job_type IN ('body_composition_push')", name="actuar_sync_jobs_job_type_valid"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'synced', 'failed', 'needs_review', 'cancelled')", name="actuar_sync_jobs_status_valid"),
        sa.ForeignKeyConstraint(["body_composition_evaluation_id"], ["body_composition_evaluations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_actuar_sync_jobs_gym_status_retry", "actuar_sync_jobs", ["gym_id", "status", "next_retry_at"])
    op.create_index("ix_actuar_sync_jobs_eval_created", "actuar_sync_jobs", ["body_composition_evaluation_id", "created_at"])
    op.create_index("ix_actuar_sync_jobs_member_created", "actuar_sync_jobs", ["member_id", "created_at"])

    op.create_table(
        "actuar_sync_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sync_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="started"),
        sa.Column("action_log_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("screenshot_path", sa.String(length=500), nullable=True),
        sa.Column("page_html_path", sa.String(length=500), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(length=120), nullable=True),
        sa.CheckConstraint("status IN ('started', 'succeeded', 'failed')", name="actuar_sync_attempts_status_valid"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sync_job_id"], ["actuar_sync_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_actuar_sync_attempts_job_started", "actuar_sync_attempts", ["sync_job_id", "started_at"])

    op.add_column("body_composition_evaluations", sa.Column("sync_required_for_training", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("body_composition_evaluations", sa.Column("sync_last_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("sync_last_success_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("sync_last_error_code", sa.String(length=80), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("sync_last_error_message", sa.Text(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("actuar_sync_job_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.alter_column("body_composition_evaluations", "actuar_sync_status", existing_type=sa.String(length=20), type_=sa.String(length=30), existing_nullable=False, server_default="saved")
    _drop_actuar_sync_status_constraints()

    op.execute(
        """
        UPDATE body_composition_evaluations
        SET actuar_sync_status = CASE actuar_sync_status
            WHEN 'pending' THEN 'sync_pending'
            WHEN 'synced' THEN 'synced_to_actuar'
            WHEN 'exported' THEN 'synced_to_actuar'
            WHEN 'failed' THEN 'sync_failed'
            WHEN 'disabled' THEN 'saved'
            WHEN 'skipped' THEN 'saved'
            ELSE 'saved'
        END,
        sync_last_success_at = actuar_last_synced_at,
        sync_last_error_message = actuar_last_error,
        sync_last_error_code = CASE WHEN actuar_last_error IS NOT NULL THEN 'legacy_sync_error' ELSE NULL END
        """
    )

    op.create_check_constraint(
        "ck_body_composition_evaluations_bce_actuar_sync_status_valid",
        "body_composition_evaluations",
        "actuar_sync_status IN ('draft', 'saved', 'sync_pending', 'syncing', 'synced_to_actuar', 'sync_failed', 'needs_review', 'manual_sync_required')",
    )
    op.create_foreign_key(
        _ACTUAR_SYNC_JOB_FK,
        "body_composition_evaluations",
        "actuar_sync_jobs",
        ["actuar_sync_job_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(_ACTUAR_SYNC_JOB_FK, "body_composition_evaluations", type_="foreignkey")
    _drop_actuar_sync_status_constraints()
    op.create_check_constraint(
        "ck_body_composition_evaluations_bce_actuar_sync_status_valid",
        "body_composition_evaluations",
        "actuar_sync_status IN ('disabled', 'pending', 'exported', 'synced', 'failed', 'skipped')",
    )
    op.alter_column("body_composition_evaluations", "actuar_sync_status", existing_type=sa.String(length=30), type_=sa.String(length=20), existing_nullable=False, server_default="disabled")
    op.drop_column("body_composition_evaluations", "actuar_sync_job_id")
    op.drop_column("body_composition_evaluations", "sync_last_error_message")
    op.drop_column("body_composition_evaluations", "sync_last_error_code")
    op.drop_column("body_composition_evaluations", "sync_last_success_at")
    op.drop_column("body_composition_evaluations", "sync_last_attempt_at")
    op.drop_column("body_composition_evaluations", "sync_required_for_training")

    op.drop_index("ix_actuar_sync_attempts_job_started", table_name="actuar_sync_attempts")
    op.drop_table("actuar_sync_attempts")
    op.drop_index("ix_actuar_sync_jobs_member_created", table_name="actuar_sync_jobs")
    op.drop_index("ix_actuar_sync_jobs_eval_created", table_name="actuar_sync_jobs")
    op.drop_index("ix_actuar_sync_jobs_gym_status_retry", table_name="actuar_sync_jobs")
    op.drop_table("actuar_sync_jobs")
    op.drop_index("ix_actuar_member_links_gym_active", table_name="actuar_member_links")
    op.drop_index("ix_actuar_member_links_gym_external_active", table_name="actuar_member_links")
    op.drop_index("ix_actuar_member_links_gym_member", table_name="actuar_member_links")
    op.drop_table("actuar_member_links")

    op.drop_column("gyms", "actuar_required_match_strategy")
    op.drop_column("gyms", "actuar_notes_template")
    op.drop_column("gyms", "actuar_auto_sync_body_composition")
    op.drop_column("gyms", "actuar_password_encrypted")
    op.drop_column("gyms", "actuar_username")
    op.drop_column("gyms", "actuar_base_url")
    op.drop_column("gyms", "actuar_enabled")

    op.drop_column("members", "birthdate")
