"""persist retention absence episodes and suppress repeated resolved cases

Revision ID: 20260812_0055
Revises: 20260811_0054
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260812_0055"
down_revision: str | None = "20260811_0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("risk_alerts", sa.Column("episode_key", sa.String(length=96), nullable=True))

    # Current open alerts always belong to the member's current absence episode.
    # A resolved alert is safe to backfill only while no later check-in exists.
    op.execute(
        sa.text(
            """
            UPDATE risk_alerts AS alert
            SET episode_key = CASE
                WHEN member.last_checkin_at IS NOT NULL THEN
                    'absence:last-checkin:' || to_char(
                        member.last_checkin_at AT TIME ZONE 'UTC',
                        'YYYY-MM-DD"T"HH24:MI:SS.US+00:00'
                    )
                ELSE 'absence:never-checked-in'
            END
            FROM members AS member
            WHERE member.id = alert.member_id
              AND (
                  alert.resolved = FALSE
                  OR COALESCE(
                      member.last_checkin_at,
                      member.join_date::timestamp AT TIME ZONE 'UTC'
                  ) <= alert.resolved_at
              )
            """
        )
    )

    # Historical/concurrent processing may have left multiple open alerts for
    # the same episode even without a manual resolution. Keep the oldest one
    # open and close the later duplicates before installing the unique index.
    op.execute(
        sa.text(
            """
            UPDATE risk_alerts AS duplicate_open
            SET resolved = TRUE,
                resolved_at = CURRENT_TIMESTAMP,
                resolved_by_user_id = NULL,
                action_history = COALESCE(duplicate_open.action_history, '[]'::jsonb) ||
                    jsonb_build_array(
                        jsonb_build_object(
                            'type', 'automatic_resolution',
                            'timestamp', CURRENT_TIMESTAMP,
                            'reason', 'duplicate_open_absence_episode_backfill'
                        )
                    )
            WHERE duplicate_open.resolved = FALSE
              AND duplicate_open.episode_key IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM risk_alerts AS canonical_open
                  WHERE canonical_open.gym_id = duplicate_open.gym_id
                    AND canonical_open.member_id = duplicate_open.member_id
                    AND canonical_open.episode_key = duplicate_open.episode_key
                    AND canonical_open.resolved = FALSE
                    AND (
                        canonical_open.created_at < duplicate_open.created_at
                        OR (
                            canonical_open.created_at = duplicate_open.created_at
                            AND canonical_open.id < duplicate_open.id
                        )
                    )
              )
            """
        )
    )

    # Repair the already-observed production shape without exposing PII: an
    # open alert created after a resolved alert for the same unchanged absence.
    op.execute(
        sa.text(
            """
            UPDATE risk_alerts AS open_alert
            SET resolved = TRUE,
                resolved_at = CURRENT_TIMESTAMP,
                resolved_by_user_id = NULL,
                action_history = COALESCE(open_alert.action_history, '[]'::jsonb) ||
                    jsonb_build_array(
                        jsonb_build_object(
                            'type', 'automatic_resolution',
                            'timestamp', CURRENT_TIMESTAMP,
                            'reason', 'duplicate_resolved_absence_episode_backfill'
                        )
                    )
            WHERE open_alert.resolved = FALSE
              AND open_alert.episode_key IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM risk_alerts AS resolved_alert
                  WHERE resolved_alert.gym_id = open_alert.gym_id
                    AND resolved_alert.member_id = open_alert.member_id
                    AND resolved_alert.resolved = TRUE
                    AND resolved_alert.id <> open_alert.id
                    AND resolved_alert.episode_key = open_alert.episode_key
                    AND resolved_alert.resolved_at <= open_alert.created_at
              )
            """
        )
    )

    op.create_index(
        "ux_risk_alerts_retention_episode",
        "risk_alerts",
        ["gym_id", "member_id", "episode_key"],
        unique=True,
        postgresql_where=sa.text("episode_key IS NOT NULL AND resolved = FALSE"),
    )


def downgrade() -> None:
    op.drop_index("ux_risk_alerts_retention_episode", table_name="risk_alerts")
    op.drop_column("risk_alerts", "episode_key")
