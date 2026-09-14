from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import AuditLog, Member, MemberStatus, RiskAlert
from app.services.audit_service import log_audit_event
from app.services.retention_stage_service import calculate_member_retention_stage, days_without_checkin_from_dates
from app.services.risk import _retention_episode_key, sync_retention_alerts_from_member_activity


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
                                'reason', 'suppressed_reopened_resolved_retention_stage'
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


def repair_retention_stage_resolutions_for_current_gym(db: Session) -> dict[str, int]:
    """Repair legacy/reopened alerts without deleting their operational history."""
    now = datetime.now(tz=timezone.utc)
    members = {
        member.id: member
        for member in db.scalars(select(Member).where(Member.deleted_at.is_(None))).all()
    }
    if not members:
        return {"resolved_repaired": 0, "open_deduplicated": 0, "keys_updated": 0}

    alerts = list(
        db.scalars(
            select(RiskAlert)
            .where(RiskAlert.member_id.in_(members))
            .order_by(RiskAlert.member_id.asc(), RiskAlert.created_at.desc(), RiskAlert.id.desc())
        ).all()
    )
    manually_resolved_keys: set[tuple] = set()
    keys_updated = 0

    for alert in alerts:
        if not alert.resolved or alert.resolved_by_user_id is None:
            continue
        member = members.get(alert.member_id)
        if member is None:
            continue
        last_checkin_at = member.last_checkin_at
        resolved_at = alert.resolved_at
        if last_checkin_at is not None and resolved_at is not None:
            normalized_checkin = last_checkin_at if last_checkin_at.tzinfo else last_checkin_at.replace(tzinfo=timezone.utc)
            normalized_resolution = resolved_at if resolved_at.tzinfo else resolved_at.replace(tzinfo=timezone.utc)
            if normalized_checkin > normalized_resolution:
                continue

        days_without_checkin = _days_from_automation_stage(alert.automation_stage)
        if days_without_checkin is None:
            days_without_checkin = days_without_checkin_from_dates(
                last_checkin_at=member.last_checkin_at,
                join_date=member.join_date,
                now=resolved_at or alert.created_at,
            )
        stage_key = _retention_episode_key(member, days_without_checkin=days_without_checkin)
        if alert.episode_key != stage_key:
            alert.episode_key = stage_key
            db.add(alert)
            keys_updated += 1
        manually_resolved_keys.add((alert.member_id, stage_key))

    latest_open_by_member: dict = {}
    open_deduplicated = 0
    resolved_repaired = 0
    for alert in alerts:
        if alert.resolved:
            continue
        if alert.member_id in latest_open_by_member:
            _resolve_repaired_alert(alert, now=now, reason="deduplicated_open_retention_alert")
            db.add(alert)
            open_deduplicated += 1
            continue
        latest_open_by_member[alert.member_id] = alert

    for member_id, alert in latest_open_by_member.items():
        member = members.get(member_id)
        if member is None:
            continue
        stage, days_without_checkin = calculate_member_retention_stage(member, now=now)
        stage_key = _retention_episode_key(member, days_without_checkin=days_without_checkin)
        member.retention_stage = stage
        db.add(member)
        if (member_id, stage_key) in manually_resolved_keys:
            _resolve_repaired_alert(
                alert,
                now=now,
                reason="repaired_reopened_resolved_retention_stage",
            )
            resolved_repaired += 1
        elif alert.episode_key != stage_key:
            alert.episode_key = stage_key
            keys_updated += 1
        db.add(alert)

    db.commit()
    if resolved_repaired or open_deduplicated or keys_updated:
        invalidate_dashboard_cache("risk")
    return {
        "resolved_repaired": resolved_repaired,
        "open_deduplicated": open_deduplicated,
        "keys_updated": keys_updated,
    }


def _days_from_automation_stage(value: str | None) -> int | None:
    normalized = (value or "").strip().lower()
    if len(normalized) < 2 or not normalized.startswith("d") or not normalized[1:].isdigit():
        return None
    return max(0, int(normalized[1:]))


def _resolve_repaired_alert(alert: RiskAlert, *, now: datetime, reason: str) -> None:
    alert.resolved = True
    alert.resolved_at = alert.resolved_at or now
    alert.resolved_by_user_id = None
    alert.action_history = list(alert.action_history or []) + [
        {
            "type": "automatic_resolution",
            "timestamp": now.isoformat(),
            "reason": reason,
        }
    ]


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
