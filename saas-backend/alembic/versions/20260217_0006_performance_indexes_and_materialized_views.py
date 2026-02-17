"""add performance indexes and dashboard materialized view

Revision ID: 20260217_0006
Revises: 20260217_0005
Create Date: 2026-02-17 01:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260217_0006"
down_revision = "20260217_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_members_gym_risk_status_deleted_score",
        "members",
        ["gym_id", "risk_level", "status", "deleted_at", "risk_score"],
        unique=False,
    )
    op.create_index(
        "ix_members_active_last_checkin",
        "members",
        ["gym_id", "last_checkin_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND status = 'active'"),
    )
    op.create_index(
        "ix_checkins_gym_weekday_hour_checkin_at",
        "checkins",
        ["gym_id", "weekday", "hour_bucket", "checkin_at"],
        unique=False,
    )
    op.create_index(
        "ix_leads_gym_stage_last_contact_deleted",
        "leads",
        ["gym_id", "stage", "last_contact_at", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_gym_status_deleted_member",
        "tasks",
        ["gym_id", "status", "deleted_at", "member_id"],
        unique=False,
    )
    op.create_index(
        "ix_tasks_gym_status_deleted_lead",
        "tasks",
        ["gym_id", "status", "deleted_at", "lead_id"],
        unique=False,
    )
    op.create_index(
        "ix_nps_responses_gym_date_score",
        "nps_responses",
        ["gym_id", "response_date", "score"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_monthly_member_kpis AS
            WITH bounds AS (
                SELECT
                    COALESCE(date_trunc('month', MIN(m.join_date)::timestamp), date_trunc('month', NOW())) AS min_month,
                    date_trunc('month', NOW()) AS max_month
                FROM members m
            ),
            months AS (
                SELECT generate_series(
                    (SELECT min_month FROM bounds),
                    (SELECT max_month FROM bounds),
                    interval '1 month'
                )::date AS month_start
            )
            SELECT
                g.id AS gym_id,
                months.month_start,
                COUNT(m.id) FILTER (
                    WHERE m.deleted_at IS NULL
                      AND m.join_date <= (months.month_start + interval '1 month - 1 day')::date
                      AND (m.cancellation_date IS NULL OR m.cancellation_date >= months.month_start)
                )::int AS active_members,
                COUNT(m.id) FILTER (
                    WHERE m.deleted_at IS NULL
                      AND m.cancellation_date >= months.month_start
                      AND m.cancellation_date < (months.month_start + interval '1 month')
                )::int AS cancelled_members,
                COALESCE(
                    SUM(m.monthly_fee) FILTER (
                        WHERE m.deleted_at IS NULL
                          AND m.join_date <= (months.month_start + interval '1 month - 1 day')::date
                          AND (m.cancellation_date IS NULL OR m.cancellation_date >= months.month_start)
                    ),
                    0
                )::numeric(12,2) AS total_mrr
            FROM gyms g
            CROSS JOIN months
            LEFT JOIN members m
                ON m.gym_id = g.id
               AND m.join_date <= (months.month_start + interval '1 month - 1 day')::date
            WHERE g.is_active IS TRUE
            GROUP BY g.id, months.month_start
            WITH DATA
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_monthly_member_kpis_gym_month
            ON mv_monthly_member_kpis (gym_id, month_start)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_mv_monthly_member_kpis_month
            ON mv_monthly_member_kpis (month_start)
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_monthly_member_kpis_month"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mv_monthly_member_kpis_gym_month"))
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS mv_monthly_member_kpis"))

    op.drop_index("ix_nps_responses_gym_date_score", table_name="nps_responses")
    op.drop_index("ix_tasks_gym_status_deleted_lead", table_name="tasks")
    op.drop_index("ix_tasks_gym_status_deleted_member", table_name="tasks")
    op.drop_index("ix_leads_gym_stage_last_contact_deleted", table_name="leads")
    op.drop_index("ix_checkins_gym_weekday_hour_checkin_at", table_name="checkins")
    op.drop_index("ix_members_active_last_checkin", table_name="members")
    op.drop_index("ix_members_gym_risk_status_deleted_score", table_name="members")
