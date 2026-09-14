"""Keep manually resolved retention alerts closed until the next stage.

Revision ID: 20260914_0064
Revises: 20260911_0063
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260914_0064"
down_revision: str | None = "20260911_0063"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_guard_resolved_retention_episode ON risk_alerts")
    op.drop_index("ux_risk_alerts_retention_episode", table_name="risk_alerts")

    # Re-key only the current absence. Historical resolutions that already have a
    # later check-in must not suppress the new absence.
    op.execute(
        sa.text(
            """
            WITH keyed AS (
                SELECT
                    alert.id,
                    CASE
                        WHEN member.last_checkin_at IS NOT NULL THEN
                            'absence:last-checkin:' || to_char(
                                date_trunc('minute', member.last_checkin_at AT TIME ZONE 'UTC'),
                                'YYYY-MM-DD"T"HH24:MI:00.000000'
                            ) || '+00:00'
                        ELSE 'absence:never-checked-in'
                    END AS absence_anchor,
                    CASE
                        WHEN alert.resolved = FALSE THEN GREATEST(
                            0,
                            floor(extract(epoch FROM (
                                CURRENT_TIMESTAMP - COALESCE(
                                    member.last_checkin_at,
                                    member.join_date::timestamp AT TIME ZONE 'UTC'
                                )
                            )) / 86400)::integer
                        )
                        WHEN alert.automation_stage ~ '^d[0-9]+$' THEN
                            substring(alert.automation_stage FROM 2)::integer
                        ELSE GREATEST(
                            0,
                            floor(extract(epoch FROM (
                                COALESCE(alert.resolved_at, alert.created_at) - COALESCE(
                                    member.last_checkin_at,
                                    member.join_date::timestamp AT TIME ZONE 'UTC'
                                )
                            )) / 86400)::integer
                        )
                    END AS days_without_checkin
                FROM risk_alerts AS alert
                JOIN members AS member ON member.id = alert.member_id
                WHERE alert.resolved = FALSE
                   OR (
                       alert.resolved = TRUE
                       AND alert.resolved_by_user_id IS NOT NULL
                       AND (
                           member.last_checkin_at IS NULL
                           OR member.last_checkin_at <= alert.resolved_at
                       )
                   )
            )
            UPDATE risk_alerts AS alert
            SET episode_key = keyed.absence_anchor || ':stage:' || (
                CASE
                    WHEN days_without_checkin >= 60 THEN 'cold_base'
                    WHEN days_without_checkin >= 45 THEN 'manager_escalation'
                    WHEN days_without_checkin >= 30 THEN 'reactivation'
                    WHEN days_without_checkin >= 14 THEN 'recovery'
                    WHEN days_without_checkin >= 7 THEN 'attention'
                    ELSE 'monitoring'
                END
            )
            FROM keyed
            WHERE keyed.id = alert.id
            """
        )
    )

    # Repair alerts that were reopened inside a stage already closed by a person.
    op.execute(
        sa.text(
            """
            UPDATE risk_alerts AS open_alert
            SET resolved = TRUE,
                resolved_at = COALESCE(open_alert.resolved_at, CURRENT_TIMESTAMP),
                resolved_by_user_id = NULL,
                action_history = COALESCE(open_alert.action_history, '[]'::jsonb) ||
                    jsonb_build_array(jsonb_build_object(
                        'type', 'automatic_resolution',
                        'timestamp', CURRENT_TIMESTAMP,
                        'reason', 'repaired_reopened_resolved_retention_stage'
                    ))
            WHERE open_alert.resolved = FALSE
              AND open_alert.episode_key IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM risk_alerts AS resolved_alert
                  WHERE resolved_alert.gym_id = open_alert.gym_id
                    AND resolved_alert.member_id = open_alert.member_id
                    AND resolved_alert.episode_key = open_alert.episode_key
                    AND resolved_alert.resolved = TRUE
                    AND resolved_alert.resolved_by_user_id IS NOT NULL
                    AND resolved_alert.id <> open_alert.id
              )
            """
        )
    )

    # Keep one operational alert per member if legacy data contains duplicates.
    op.execute(
        sa.text(
            """
            WITH duplicates AS (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY gym_id, member_id
                           ORDER BY created_at DESC, id DESC
                       ) AS position
                FROM risk_alerts
                WHERE resolved = FALSE
            )
            UPDATE risk_alerts AS alert
            SET resolved = TRUE,
                resolved_at = COALESCE(alert.resolved_at, CURRENT_TIMESTAMP),
                resolved_by_user_id = NULL,
                action_history = COALESCE(alert.action_history, '[]'::jsonb) ||
                    jsonb_build_array(jsonb_build_object(
                        'type', 'automatic_resolution',
                        'timestamp', CURRENT_TIMESTAMP,
                        'reason', 'deduplicated_open_retention_alert'
                    ))
            FROM duplicates
            WHERE duplicates.id = alert.id
              AND duplicates.position > 1
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

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION guard_resolved_retention_episode()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.resolved = FALSE
                   AND NEW.episode_key IS NOT NULL
                   AND EXISTS (
                       SELECT 1
                       FROM risk_alerts AS resolved_alert
                       WHERE resolved_alert.gym_id = NEW.gym_id
                         AND resolved_alert.member_id = NEW.member_id
                         AND resolved_alert.episode_key = NEW.episode_key
                         AND resolved_alert.resolved = TRUE
                         AND resolved_alert.resolved_by_user_id IS NOT NULL
                         AND resolved_alert.id <> NEW.id
                   )
                THEN
                    NEW.resolved := TRUE;
                    NEW.resolved_at := COALESCE(NEW.resolved_at, CURRENT_TIMESTAMP);
                    NEW.resolved_by_user_id := NULL;
                    NEW.action_history := COALESCE(NEW.action_history, '[]'::jsonb) ||
                        jsonb_build_array(jsonb_build_object(
                            'type', 'automatic_resolution',
                            'timestamp', CURRENT_TIMESTAMP,
                            'reason', 'suppressed_reopened_resolved_retention_stage'
                        ));
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
    )
    op.execute(
        """
        CREATE TRIGGER trg_guard_resolved_retention_episode
        BEFORE INSERT OR UPDATE OF resolved, episode_key
        ON risk_alerts
        FOR EACH ROW
        EXECUTE FUNCTION guard_resolved_retention_episode()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_guard_resolved_retention_episode ON risk_alerts")
    op.drop_index("ux_risk_alerts_retention_episode", table_name="risk_alerts")
    op.execute(
        """
        UPDATE risk_alerts
        SET episode_key = regexp_replace(episode_key, ':stage:[a-z_]+$', '')
        WHERE episode_key ~ ':stage:[a-z_]+$'
        """
    )
    op.create_index(
        "ux_risk_alerts_retention_episode",
        "risk_alerts",
        ["gym_id", "member_id", "episode_key"],
        unique=True,
        postgresql_where=sa.text("episode_key IS NOT NULL AND resolved = FALSE"),
    )
