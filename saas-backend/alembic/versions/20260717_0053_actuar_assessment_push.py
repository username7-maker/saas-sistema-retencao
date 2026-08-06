"""Allow Actuar sync jobs for manual anthropometric assessments.

Revision ID: 20260717_0053
Revises: 20260716_0051
Create Date: 2026-07-17 11:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260717_0053"
down_revision = "20260716_0051"
branch_labels = None
depends_on = None


def _columns() -> dict[str, dict]:
    bind = op.get_bind()
    return {column["name"]: column for column in sa.inspect(bind).get_columns("actuar_sync_jobs")}


def _index_names() -> set[str]:
    bind = op.get_bind()
    return {index["name"] for index in sa.inspect(bind).get_indexes("actuar_sync_jobs")}


def _foreign_key_names() -> set[str]:
    bind = op.get_bind()
    return {fk["name"] for fk in sa.inspect(bind).get_foreign_keys("actuar_sync_jobs")}


def _drop_actuar_sync_job_type_constraints() -> None:
    op.execute(
        """
        DO $$
        DECLARE constraint_record record;
        BEGIN
            FOR constraint_record IN
                SELECT c.conname
                FROM pg_constraint AS c
                JOIN pg_class AS t ON t.oid = c.conrelid
                WHERE t.relname = 'actuar_sync_jobs'
                  AND c.contype = 'c'
                  AND pg_get_constraintdef(c.oid) ILIKE '%job_type%'
            LOOP
                EXECUTE format('ALTER TABLE actuar_sync_jobs DROP CONSTRAINT IF EXISTS %I', constraint_record.conname);
            END LOOP;
        END $$;
        """
    )


def _drop_actuar_sync_source_constraints() -> None:
    op.execute(
        """
        DO $$
        DECLARE constraint_record record;
        BEGIN
            FOR constraint_record IN
                SELECT c.conname
                FROM pg_constraint AS c
                JOIN pg_class AS t ON t.oid = c.conrelid
                WHERE t.relname = 'actuar_sync_jobs'
                  AND c.contype = 'c'
                  AND pg_get_constraintdef(c.oid) ILIKE '%body_composition_evaluation_id%'
                  AND (
                    pg_get_constraintdef(c.oid) ILIKE '%assessment_id%'
                    OR pg_get_constraintdef(c.oid) ILIKE '%payload_version%'
                  )
            LOOP
                EXECUTE format('ALTER TABLE actuar_sync_jobs DROP CONSTRAINT IF EXISTS %I', constraint_record.conname);
            END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    columns = _columns()
    if "assessment_id" not in columns:
        op.add_column("actuar_sync_jobs", sa.Column("assessment_id", postgresql.UUID(as_uuid=True), nullable=True))
        columns = _columns()
    if columns.get("body_composition_evaluation_id", {}).get("nullable") is False:
        op.alter_column(
            "actuar_sync_jobs",
            "body_composition_evaluation_id",
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True,
        )
    if "fk_actuar_sync_jobs_assessment_id" not in _foreign_key_names() and "fk_actuar_sync_jobs_assessment_id_assessments" not in _foreign_key_names():
        op.create_foreign_key(
            "fk_actuar_sync_jobs_assessment_id",
            "actuar_sync_jobs",
            "assessments",
            ["assessment_id"],
            ["id"],
            ondelete="CASCADE",
        )
    _drop_actuar_sync_job_type_constraints()
    _drop_actuar_sync_source_constraints()
    op.create_check_constraint(
        "actuar_sync_jobs_job_type_valid",
        "actuar_sync_jobs",
        "job_type IN ('body_composition_push', 'assessment_push')",
    )
    op.create_check_constraint(
        "actuar_sync_jobs_source_valid",
        "actuar_sync_jobs",
        """
        (
            job_type = 'body_composition_push'
            AND body_composition_evaluation_id IS NOT NULL
            AND assessment_id IS NULL
        )
        OR
        (
            job_type = 'assessment_push'
            AND assessment_id IS NOT NULL
            AND body_composition_evaluation_id IS NULL
        )
        """,
    )
    indexes = _index_names()
    if "ix_actuar_sync_jobs_assessment_id" not in indexes:
        op.create_index("ix_actuar_sync_jobs_assessment_id", "actuar_sync_jobs", ["assessment_id"], unique=False)
    if "ix_actuar_sync_jobs_assessment_created" not in indexes:
        op.create_index("ix_actuar_sync_jobs_assessment_created", "actuar_sync_jobs", ["assessment_id", "created_at"], unique=False)
    if "uq_actuar_sync_jobs_gym_assessment_job_type" not in indexes:
        op.create_index(
            "uq_actuar_sync_jobs_gym_assessment_job_type",
            "actuar_sync_jobs",
            ["gym_id", "assessment_id", "job_type"],
            unique=True,
            postgresql_where=sa.text("assessment_id IS NOT NULL"),
        )


def downgrade() -> None:
    op.drop_index("uq_actuar_sync_jobs_gym_assessment_job_type", table_name="actuar_sync_jobs")
    op.drop_index("ix_actuar_sync_jobs_assessment_created", table_name="actuar_sync_jobs")
    op.drop_index("ix_actuar_sync_jobs_assessment_id", table_name="actuar_sync_jobs")
    op.drop_constraint("actuar_sync_jobs_source_valid", "actuar_sync_jobs", type_="check")
    op.drop_constraint("actuar_sync_jobs_job_type_valid", "actuar_sync_jobs", type_="check")
    op.create_check_constraint(
        "actuar_sync_jobs_job_type_valid",
        "actuar_sync_jobs",
        "job_type IN ('body_composition_push')",
    )
    op.drop_constraint("fk_actuar_sync_jobs_assessment_id", "actuar_sync_jobs", type_="foreignkey")
    op.alter_column(
        "actuar_sync_jobs",
        "body_composition_evaluation_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("actuar_sync_jobs", "assessment_id")
