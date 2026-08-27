from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import AuditLog, Member, MemberStatus
from app.services.audit_service import log_audit_event
from app.services.risk import sync_retention_alerts_from_member_activity


RETENTION_ALERT_BACKFILL_ACTION = "retention_alerts_backfilled_20260820_v2"
RETENTION_ALERT_BACKFILL_BATCH_SIZE = 500


def repair_retention_episode_guard(db: Session) -> None:
    db.execute(
        text(
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
    db.commit()


def backfill_retention_alerts_for_current_gym(db: Session) -> dict[str, int | bool]:
    already_completed = db.scalar(
        select(AuditLog.id).where(AuditLog.action == RETENTION_ALERT_BACKFILL_ACTION).limit(1)
    )
    if already_completed is not None:
        return {"members_refreshed": 0, "alerts_synced": 0, "already_completed": True}

    member_ids = list(
        db.scalars(
            select(Member.id).where(
                Member.deleted_at.is_(None),
                Member.status.in_([MemberStatus.ACTIVE, MemberStatus.PAUSED]),
            )
        ).all()
    )
    totals = {"members_refreshed": 0, "alerts_synced": 0}
    for offset in range(0, len(member_ids), RETENTION_ALERT_BACKFILL_BATCH_SIZE):
        result = sync_retention_alerts_from_member_activity(
            db,
            member_ids=member_ids[offset : offset + RETENTION_ALERT_BACKFILL_BATCH_SIZE],
        )
        totals["members_refreshed"] += int(result.get("members_refreshed", 0))
        totals["alerts_synced"] += int(result.get("alerts_synced", 0))

    log_audit_event(
        db,
        action=RETENTION_ALERT_BACKFILL_ACTION,
        entity="member",
        details=totals,
    )
    db.commit()
    return {**totals, "already_completed": False}
