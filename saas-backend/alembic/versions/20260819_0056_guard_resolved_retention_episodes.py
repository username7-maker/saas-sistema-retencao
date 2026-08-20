"""guard resolved retention episodes against accidental reopening

Revision ID: 20260819_0056
Revises: 20260812_0055
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260819_0056"
down_revision: str | None = "20260812_0055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The application already suppresses resolved absence episodes. Keep the
    # same invariant at the database boundary so an operational rebuild or a
    # one-off bulk insert cannot reopen an episode behind the service layer.
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
                         AND resolved_alert.id <> NEW.id
                   )
                THEN
                    NEW.resolved := TRUE;
                    NEW.resolved_at := COALESCE(NEW.resolved_at, CURRENT_TIMESTAMP);
                    NEW.resolved_by_user_id := NULL;
                    NEW.action_history := COALESCE(NEW.action_history, '[]'::jsonb) ||
                        jsonb_build_array(
                            jsonb_build_object(
                                'type', 'automatic_resolution',
                                'timestamp', CURRENT_TIMESTAMP,
                                'reason', 'suppressed_reopened_resolved_absence_episode'
                            )
                        );
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_guard_resolved_retention_episode
            BEFORE INSERT OR UPDATE OF resolved, episode_key
            ON risk_alerts
            FOR EACH ROW
            EXECUTE FUNCTION guard_resolved_retention_episode()
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TRIGGER IF EXISTS trg_guard_resolved_retention_episode ON risk_alerts"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS guard_resolved_retention_episode()"))
