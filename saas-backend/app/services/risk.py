import logging
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import case, func, select, text
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.database import get_current_gym_id
from app.models import AuditLog, Checkin, Member, MemberRiskHistory, MemberStatus, RiskAlert, RiskLevel, RoleEnum, Task, TaskPriority, TaskStatus, User
from app.services.audit_service import log_audit_event
from app.services.notification_service import create_notification
from app.services.websocket_manager import websocket_manager
from app.utils.email import send_email_result

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskResult:
    score: int
    level: RiskLevel
    reasons: dict
    days_without_checkin: int


@dataclass(frozen=True)
class PrefetchedCheckinMetrics:
    current_week_count: int = 0
    baseline_total: int = 0
    recent_mode_hour: int | None = None
    previous_mode_hour: int | None = None


def _member_join_datetime(member: Member, now: datetime) -> datetime | None:
    join_date = getattr(member, "join_date", None)
    if join_date is None:
        return None
    if isinstance(join_date, datetime):
        join_dt = join_date
    else:
        join_dt = datetime.combine(join_date, time.min, tzinfo=timezone.utc)
    if join_dt.tzinfo is None:
        join_dt = join_dt.replace(tzinfo=timezone.utc)
    if join_dt > now:
        return now
    return join_dt


def calculate_risk_score(
    db: Session,
    member: Member,
    now: datetime | None = None,
    metrics: PrefetchedCheckinMetrics | None = None,
) -> RiskResult:
    now = now or datetime.now(tz=timezone.utc)
    join_dt = _member_join_datetime(member, now)
    reference_dt = member.last_checkin_at or join_dt or now
    if reference_dt.tzinfo is None:
        reference_dt = reference_dt.replace(tzinfo=timezone.utc)
    days_without_checkin = max(0, (now - reference_dt).days)

    inactivity_points = _inactivity_points(days_without_checkin)
    if metrics is None:
        frequency_points, frequency_drop_pct, baseline_avg_weekly = _frequency_drop_points(db, member.id, now)
        shift_points, shift_change_hours = _shift_change_points(db, member.id, now)
    else:
        frequency_points, frequency_drop_pct, baseline_avg_weekly = _frequency_drop_points_from_metrics(
            metrics.current_week_count,
            metrics.baseline_total,
        )
        shift_points, shift_change_hours = _shift_change_points_from_modes(
            metrics.recent_mode_hour,
            metrics.previous_mode_hour,
        )
    nps_points = _nps_points(member.nps_last_score)
    loyalty_discount = min((member.loyalty_months // 6) * 3, 15)

    # Alunos novos não devem ser penalizados por inatividade durante o onboarding.
    # D0–D7: inactivity_points anulados completamente.
    # D8–D14: inactivity_points reduzidos à metade.
    if join_dt is None:
        onboarding_discount = 0
    else:
        days_since_join = max(0, (now - join_dt).days)
        if days_since_join <= 7:
            onboarding_discount = inactivity_points
        elif days_since_join <= 14:
            onboarding_discount = inactivity_points // 2
        else:
            onboarding_discount = 0

    raw_score = inactivity_points + frequency_points + shift_points + nps_points - loyalty_discount - onboarding_discount
    score = max(0, min(raw_score, 100))
    level = _determine_level(score)

    reasons = {
        "inactivity_points": inactivity_points,
        "frequency_points": frequency_points,
        "frequency_drop_pct": frequency_drop_pct,
        "shift_points": shift_points,
        "shift_change_hours": shift_change_hours,
        "nps_points": nps_points,
        "loyalty_discount": loyalty_discount,
        "onboarding_discount": onboarding_discount,
        "baseline_avg_weekly": round(baseline_avg_weekly, 2),
    }
    return RiskResult(score=score, level=level, reasons=reasons, days_without_checkin=days_without_checkin)


_AUTOMATION_STAGES = ["automation_3d", "automation_7d", "automation_10d", "automation_14d", "automation_21d"]


def run_daily_risk_processing(db: Session) -> dict[str, int]:
    db.execute(text("SET LOCAL statement_timeout = 0"))
    now = datetime.now(tz=timezone.utc)
    members = db.scalars(
        select(Member).where(
            Member.deleted_at.is_(None),
            Member.status.in_([MemberStatus.ACTIVE, MemberStatus.PAUSED]),
        )
    ).all()

    analyzed = len(members)
    if not analyzed:
        return {"members_analyzed": 0, "risk_alerts_processed": 0, "automations_triggered": 0}

    # Prefetch all automation audit records in ONE query to avoid N+1
    metrics_by_member = _prefetch_member_checkin_metrics(db, now)
    ninety_days_ago = now - timedelta(days=90)
    triggered_stages: set[tuple] = set(
        db.execute(
            select(AuditLog.member_id, AuditLog.action).where(
                AuditLog.member_id.is_not(None),
                AuditLog.action.in_(_AUTOMATION_STAGES),
                AuditLog.created_at >= ninety_days_ago,
            )
        ).all()
    )
    current_alerts_by_member = _prefetch_open_risk_alerts(db, deduplicate=True)
    existing_call_tasks = _prefetch_open_call_tasks(db, deduplicate=True)
    manager = _find_manager(db)
    existing_manager_alert_tasks: set[tuple] = set()
    if manager:
        existing_manager_alert_tasks = _prefetch_open_manager_alert_tasks(
            db,
            manager.id,
            deduplicate=True,
        )

    alerts_created = 0
    automations_triggered = 0
    ws_events: list[dict] = []

    BATCH_SIZE = 100
    for batch_start in range(0, analyzed, BATCH_SIZE):
        batch = members[batch_start : batch_start + BATCH_SIZE]
        try:
            db.execute(text("SET LOCAL statement_timeout = 0"))
            for member in batch:
                result = calculate_risk_score(db, member, now, metrics_by_member.get(member.id))
                previous_score = member.risk_score
                previous_level = member.risk_level

                member.risk_score = result.score
                member.risk_level = result.level

                if result.score >= 40:
                    actions = _run_inactivity_automations(
                        db,
                        member,
                        result.days_without_checkin,
                        result.level,
                        triggered_stages,
                        existing_call_tasks=existing_call_tasks,
                        manager=manager,
                        existing_manager_alert_tasks=existing_manager_alert_tasks,
                    )
                    automations_triggered += len(actions)
                    effective_result = _result_from_member_state(member, result)
                    current_alert_obj = current_alerts_by_member.get(member.id)
                    current_alert = _create_or_update_alert(
                        db,
                        member,
                        effective_result,
                        actions,
                        current_alert=current_alert_obj,
                        ws_events=ws_events,
                    )
                    current_alerts_by_member[member.id] = current_alert
                    alerts_created += 1
                else:
                    effective_result = result

                if (
                    effective_result.score != previous_score
                    or effective_result.level != previous_level
                ):
                    member.risk_score = effective_result.score
                    member.risk_level = effective_result.level
                    db.add(member)

                if effective_result.score != previous_score:
                    db.add(MemberRiskHistory(
                        gym_id=member.gym_id,
                        member_id=member.id,
                        score=effective_result.score,
                        level=effective_result.level.value,
                        reasons=effective_result.reasons,
                    ))

            db.commit()
        except Exception:
            logger.exception(
                "Risk batch failed (members %d-%d)", batch_start, batch_start + len(batch),
            )
            db.rollback()

    if analyzed:
        invalidate_dashboard_cache("risk", "tasks")

    # Broadcast a single summary event instead of per-alert broadcasts
    if ws_events:
        gym_id = ws_events[0]["gym_id"]
        websocket_manager.broadcast_event_sync(
            gym_id,
            "risk_processing_complete",
            {
                "members_analyzed": analyzed,
                "alerts_processed": alerts_created,
            },
        )

    # NOTE: run_automation_rules() is intentionally NOT called here.
    # It is executed by daily_automations_job (jobs.py) at 02:30 UTC to avoid double-firing.
    return {
        "members_analyzed": analyzed,
        "risk_alerts_processed": alerts_created,
        "automations_triggered": automations_triggered,
    }


def refresh_member_risk_snapshot(
    db: Session,
    *,
    member_ids: Iterable[uuid.UUID],
    now: datetime | None = None,
    sync_alerts: bool = False,
) -> dict[str, int]:
    normalized_member_ids = tuple(dict.fromkeys(member_ids))
    if not normalized_member_ids:
        return {"members_refreshed": 0}

    now = now or datetime.now(tz=timezone.utc)
    members = db.scalars(
        select(Member).where(
            Member.id.in_(normalized_member_ids),
            Member.deleted_at.is_(None),
            Member.status.in_([MemberStatus.ACTIVE, MemberStatus.PAUSED]),
        )
    ).all()
    if not members:
        return {"members_refreshed": 0}

    metrics_by_member = _prefetch_member_checkin_metrics(db, now, member_ids={member.id for member in members})
    current_alerts_by_member = _prefetch_open_risk_alerts(db, deduplicate=True) if sync_alerts else {}
    refreshed = 0
    alerts_synced = 0
    for member in members:
        result = calculate_risk_score(db, member, now, metrics_by_member.get(member.id))
        if member.risk_score != result.score or member.risk_level != result.level:
            member.risk_score = result.score
            member.risk_level = result.level
            db.add(member)
        if sync_alerts and result.score >= 40:
            current_alert = current_alerts_by_member.get(member.id)
            synced_alert = _create_or_update_alert(
                db,
                member,
                result,
                [],
                current_alert=current_alert,
            )
            current_alerts_by_member[member.id] = synced_alert
            alerts_synced += 1
        refreshed += 1

    invalidate_dashboard_cache("risk")
    return {"members_refreshed": refreshed, "alerts_synced": alerts_synced}


def _result_from_member_state(member: Member, result: RiskResult) -> RiskResult:
    if member.risk_score == result.score and member.risk_level == result.level:
        return result
    reasons = dict(result.reasons)
    reasons["automation_escalation"] = True
    return replace(result, score=member.risk_score, level=member.risk_level, reasons=reasons)


def _inactivity_points(days_without_checkin: int) -> int:
    if days_without_checkin >= 21:
        return 60
    if days_without_checkin >= 14:
        return 45
    if days_without_checkin >= 10:
        return 30
    if days_without_checkin >= 7:
        return 20
    if days_without_checkin >= 3:
        return 10
    return 0


def _prefetch_member_checkin_metrics(
    db: Session,
    now: datetime,
    member_ids: set[uuid.UUID] | None = None,
) -> dict:
    ten_weeks_ago = now - timedelta(weeks=10)
    one_week_ago = now - timedelta(weeks=1)
    recent_start = now - timedelta(days=14)
    prev_start = now - timedelta(days=60)
    prev_end = now - timedelta(days=14)

    # Single SQL query with aggregation — returns O(members) rows instead of O(checkins).
    # PostgreSQL mode() picks arbitrary value on ties (acceptable for shift-change heuristic).
    stmt = (
        select(
            Checkin.member_id,
            func.count(Checkin.id).filter(Checkin.checkin_at >= one_week_ago).label("current_week_count"),
            func.count(Checkin.id).filter(Checkin.checkin_at < one_week_ago).label("baseline_total"),
            func.mode().within_group(Checkin.hour_bucket).filter(
                Checkin.checkin_at >= recent_start,
            ).label("recent_mode_hour"),
            func.mode().within_group(Checkin.hour_bucket).filter(
                Checkin.checkin_at >= prev_start,
                Checkin.checkin_at < prev_end,
            ).label("previous_mode_hour"),
        ).where(
            Checkin.checkin_at >= ten_weeks_ago,
            Checkin.checkin_at < now,
        )
    )
    if member_ids:
        stmt = stmt.where(Checkin.member_id.in_(member_ids))

    rows = db.execute(stmt.group_by(Checkin.member_id)).all()

    metrics_by_member: dict = {}
    for row in rows:
        metrics_by_member[row.member_id] = PrefetchedCheckinMetrics(
            current_week_count=row.current_week_count or 0,
            baseline_total=row.baseline_total or 0,
            recent_mode_hour=int(row.recent_mode_hour) if row.recent_mode_hour is not None else None,
            previous_mode_hour=int(row.previous_mode_hour) if row.previous_mode_hour is not None else None,
        )
    return metrics_by_member


def _prefetch_open_risk_alerts(db: Session, *, deduplicate: bool = False) -> dict:
    alerts = db.scalars(
        select(RiskAlert)
        .where(RiskAlert.resolved.is_(False))
        .order_by(RiskAlert.member_id.asc(), RiskAlert.created_at.desc(), RiskAlert.id.desc())
    ).all()
    alert_by_member: dict = {}
    now = datetime.now(tz=timezone.utc)
    for alert in alerts:
        member_id = getattr(alert, "member_id", None)
        if member_id is None:
            continue
        if member_id in alert_by_member:
            if deduplicate:
                alert.resolved = True
                alert.resolved_at = now
                db.add(alert)
            continue
        alert_by_member[member_id] = alert
    return alert_by_member


def _prefetch_open_call_tasks(db: Session, *, deduplicate: bool = False) -> set:
    tasks = db.scalars(
        select(Task).where(
            Task.member_id.is_not(None),
            Task.title.ilike("Ligar para %"),
            Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
            Task.deleted_at.is_(None),
        ).order_by(Task.member_id.asc(), Task.created_at.asc(), Task.id.asc())
    ).all()
    task_member_ids: set = set()
    now = datetime.now(tz=timezone.utc)
    for task in tasks:
        member_id = getattr(task, "member_id", None)
        if member_id is None:
            continue
        if member_id in task_member_ids:
            if deduplicate:
                task.deleted_at = now
                db.add(task)
            continue
        task_member_ids.add(member_id)
    return task_member_ids


def _prefetch_open_manager_alert_tasks(
    db: Session,
    manager_id,
    *,
    deduplicate: bool = False,
) -> set[tuple]:
    tasks = db.scalars(
        select(Task).where(
            Task.member_id.is_not(None),
            Task.assigned_to_user_id == manager_id,
            Task.title.ilike("%Escalar churn%"),
            Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
            Task.deleted_at.is_(None),
        ).order_by(Task.member_id.asc(), Task.created_at.asc(), Task.id.asc())
    ).all()
    task_keys: set[tuple] = set()
    now = datetime.now(tz=timezone.utc)
    for task in tasks:
        member_id = getattr(task, "member_id", None)
        assigned_to_user_id = getattr(task, "assigned_to_user_id", None)
        if member_id is None or assigned_to_user_id is None:
            continue
        task_key = (member_id, assigned_to_user_id)
        if task_key in task_keys:
            if deduplicate:
                task.deleted_at = now
                db.add(task)
            continue
        task_keys.add(task_key)
    return task_keys


def _frequency_drop_points(db: Session, member_id, now: datetime) -> tuple[int, float, float]:
    one_week_ago = now - timedelta(weeks=1)
    ten_weeks_ago = now - timedelta(weeks=10)

    current_week_count = db.scalar(
        select(func.count()).select_from(Checkin).where(
            Checkin.member_id == member_id,
            Checkin.checkin_at >= one_week_ago,
            Checkin.checkin_at < now,
        )
    ) or 0

    baseline_total = db.scalar(
        select(func.count()).select_from(Checkin).where(
            Checkin.member_id == member_id,
            Checkin.checkin_at >= ten_weeks_ago,
            Checkin.checkin_at < one_week_ago,
        )
    ) or 0

    baseline_avg = baseline_total / 9.0

    if baseline_avg <= 0:
        return (12, 100.0, 0.0) if current_week_count == 0 else (0, 0.0, 0.0)

    drop_pct = max(0.0, ((baseline_avg - current_week_count) / baseline_avg) * 100)
    return _score_frequency_drop(drop_pct, baseline_avg)


def _frequency_drop_points_from_metrics(current_week_count: int, baseline_total: int) -> tuple[int, float, float]:
    baseline_avg = baseline_total / 9.0

    if baseline_avg <= 0:
        return (12, 100.0, 0.0) if current_week_count == 0 else (0, 0.0, 0.0)

    drop_pct = max(0.0, ((baseline_avg - current_week_count) / baseline_avg) * 100)
    return _score_frequency_drop(drop_pct, baseline_avg)


def _score_frequency_drop(drop_pct: float, baseline_avg: float) -> tuple[int, float, float]:
    if drop_pct >= 80:
        return 20, drop_pct, baseline_avg
    if drop_pct >= 50:
        return 12, drop_pct, baseline_avg
    if drop_pct >= 25:
        return 6, drop_pct, baseline_avg
    return 0, drop_pct, baseline_avg


def _shift_change_points(db: Session, member_id, now: datetime) -> tuple[int, int]:
    recent_start = now - timedelta(days=14)
    prev_start = now - timedelta(days=60)
    prev_end = now - timedelta(days=14)

    recent_mode_hour = db.scalar(
        select(Checkin.hour_bucket)
        .where(Checkin.member_id == member_id, Checkin.checkin_at >= recent_start)
        .group_by(Checkin.hour_bucket)
        .order_by(func.count(Checkin.id).desc())
        .limit(1)
    )
    previous_mode_hour = db.scalar(
        select(Checkin.hour_bucket)
        .where(
            Checkin.member_id == member_id,
            Checkin.checkin_at >= prev_start,
            Checkin.checkin_at < prev_end,
        )
        .group_by(Checkin.hour_bucket)
        .order_by(func.count(Checkin.id).desc())
        .limit(1)
    )

    if recent_mode_hour is None or previous_mode_hour is None:
        return 0, 0

    change = abs(int(recent_mode_hour) - int(previous_mode_hour))
    return _score_shift_change(change)


def _shift_change_points_from_modes(recent_mode_hour: int | None, previous_mode_hour: int | None) -> tuple[int, int]:
    if recent_mode_hour is None or previous_mode_hour is None:
        return 0, 0
    change = abs(int(recent_mode_hour) - int(previous_mode_hour))
    return _score_shift_change(change)


def _score_shift_change(change: int) -> tuple[int, int]:
    if change >= 4:
        return 10, change
    if change >= 2:
        return 5, change
    return 0, change


def _nps_points(score: int) -> int:
    if score <= 4:
        return 18
    if score <= 6:
        return 10
    if score <= 8:
        return 4
    return 0


def _determine_level(score: int) -> RiskLevel:
    if score >= 70:
        return RiskLevel.RED
    if score >= 40:
        return RiskLevel.YELLOW
    return RiskLevel.GREEN


def _create_or_update_alert(
    db: Session,
    member: Member,
    risk_result: RiskResult,
    actions: list[dict],
    *,
    current_alert: RiskAlert | None = None,
    ws_events: list[dict] | None = None,
) -> RiskAlert:
    if current_alert:
        current_alert.score = risk_result.score
        current_alert.level = risk_result.level
        current_alert.reasons = risk_result.reasons
        current_alert.automation_stage = f"d{risk_result.days_without_checkin}"
        current_alert.action_history = (current_alert.action_history or []) + actions
        db.add(current_alert)
        _emit_ws_event(ws_events, member.gym_id, "risk_alert_updated", member.id, current_alert.id, current_alert.score, current_alert.level.value)
        return current_alert

    alert = RiskAlert(
        id=uuid.uuid4(),
        member_id=member.id,
        score=risk_result.score,
        level=risk_result.level,
        reasons=risk_result.reasons,
        action_history=actions,
        automation_stage=f"d{risk_result.days_without_checkin}",
    )
    db.add(alert)
    _emit_ws_event(ws_events, member.gym_id, "risk_alert_created", member.id, alert.id, alert.score, alert.level.value)
    return alert


def _emit_ws_event(ws_events: list[dict] | None, gym_id, event_type: str, member_id, alert_id, score: int, level: str) -> None:
    payload = {"member_id": str(member_id), "alert_id": str(alert_id), "score": score, "level": level}
    if ws_events is not None:
        ws_events.append({"gym_id": str(gym_id), "event": event_type, "payload": payload})
    else:
        websocket_manager.broadcast_event_sync(str(gym_id), event_type, payload)


def _run_inactivity_automations(
    db: Session,
    member: Member,
    days_without_checkin: int,
    level: RiskLevel,
    triggered_stages: set[tuple] | None = None,
    *,
    existing_call_tasks: set | None = None,
    manager: User | None = None,
    existing_manager_alert_tasks: set[tuple] | None = None,
) -> list[dict]:
    now = datetime.now(tz=timezone.utc)
    # BLOQUEIO: nao disparar automacoes de retencao para alunos em onboarding ativo (< 14 dias)
    join_dt = _member_join_datetime(member, now)
    join_days = max(0, (now - join_dt).days) if join_dt is not None else None
    if join_days is not None and join_days < 14:
        return []

    actions: list[dict] = []

    def mark_triggered(stage: str) -> None:
        if triggered_stages is not None:
            triggered_stages.add((member.id, stage))
        _record_stage(db, member.id, stage)

    if days_without_checkin >= 3 and _can_trigger_stage(db, member.id, "automation_3d", triggered_stages):
        email_result = None
        if member.email:
            email_result = send_email_result(
                member.email,
                "Volte para o treino hoje",
                "Seu progresso importa. Vamos retomar o ritmo?",
            )
        if email_result and email_result.sent:
            actions.append({"type": "email", "stage": "3d", "timestamp": now.isoformat(), "status": "sent"})
            mark_triggered("automation_3d")
        elif email_result and email_result.blocked:
            actions.append(
                {
                    "type": "email",
                    "stage": "3d",
                    "timestamp": now.isoformat(),
                    "status": "blocked",
                    "reason": email_result.reason,
                }
            )
            mark_triggered("automation_3d")
        else:
            actions.append({"type": "email", "stage": "3d", "timestamp": now.isoformat(), "status": "failed"})

    if days_without_checkin >= 7 and _can_trigger_stage(db, member.id, "automation_7d", triggered_stages):
        if existing_call_tasks is None:
            _ensure_call_task(db, member, "7d")
        else:
            _ensure_call_task(db, member, "7d", existing_task_member_ids=existing_call_tasks)
        actions.append({"type": "task", "stage": "7d", "timestamp": now.isoformat()})
        mark_triggered("automation_7d")

    if days_without_checkin >= 10 and _can_trigger_stage(db, member.id, "automation_10d", triggered_stages):
        email_result = None
        if member.email:
            email_result = send_email_result(
                member.email,
                "Dica personalizada de treino",
                "Separamos uma dica curta para facilitar sua volta. Procure a recepcao para ajustar seu plano.",
            )
        if email_result and email_result.sent:
            actions.append({"type": "email", "stage": "10d", "timestamp": now.isoformat(), "status": "sent"})
            mark_triggered("automation_10d")
        elif email_result and email_result.blocked:
            actions.append(
                {
                    "type": "email",
                    "stage": "10d",
                    "timestamp": now.isoformat(),
                    "status": "blocked",
                    "reason": email_result.reason,
                }
            )
            mark_triggered("automation_10d")
        else:
            actions.append({"type": "email", "stage": "10d", "timestamp": now.isoformat(), "status": "failed"})

    if days_without_checkin >= 14 and _can_trigger_stage(db, member.id, "automation_14d", triggered_stages):
        if level == RiskLevel.YELLOW:
            member.risk_level = RiskLevel.RED
            member.risk_score = max(member.risk_score, 70)
        notification = create_notification(
            db,
            member_id=member.id,
            user_id=member.assigned_user_id,
            title="Aluno sem treino ha 14 dias",
            message=f"{member.full_name} esta sem check-in ha 14 dias. Acionar plano de retencao.",
            category="retention",
            extra_data={"stage": "14d", "risk_level": member.risk_level.value},
            flush=False,
        )
        actions.append(
            {
                "type": "in_app_notification",
                "stage": "14d",
                "timestamp": now.isoformat(),
                "message": "Aluno sem treino ha 14 dias",
                "notification_id": str(notification.id),
            }
        )
        mark_triggered("automation_14d")

    if days_without_checkin >= 21 and _can_trigger_stage(db, member.id, "automation_21d", triggered_stages):
        if manager:
            if existing_manager_alert_tasks is None:
                _ensure_manager_alert_task(db, member, manager.id)
            else:
                _ensure_manager_alert_task(
                    db,
                    member,
                    manager.id,
                    existing_task_pairs=existing_manager_alert_tasks,
                )
        actions.append({"type": "manager_alert", "stage": "21d", "timestamp": now.isoformat()})
        mark_triggered("automation_21d")

    return actions


def _ensure_call_task(
    db: Session,
    member: Member,
    stage: str,
    *,
    existing_task_member_ids: set | None = None,
) -> None:
    if existing_task_member_ids is not None and member.id in existing_task_member_ids:
        return
    if existing_task_member_ids is None:
        existing_task = db.scalar(
            select(Task).where(
                Task.member_id == member.id,
                Task.title.ilike(f"%Ligar para {member.full_name}%"),
                Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
                Task.deleted_at.is_(None),
            )
        )
        if existing_task:
            return

    suggested_message = f"Ola {member.full_name}, sentimos sua falta. Vamos retomar seus treinos esta semana?"
    task = Task(
        member_id=member.id,
        assigned_to_user_id=member.assigned_user_id,
        title=f"Ligar para {member.full_name}",
        description=f"Automacao de retencao ({stage}) para aluno inativo.",
        priority=TaskPriority.HIGH,
        status=TaskStatus.TODO,
        kanban_column=TaskStatus.TODO.value,
        suggested_message=suggested_message,
        extra_data={
            "source": "retention_automation",
            "stage": stage,
            "owner_role": "reception",
        },
    )
    db.add(task)
    if existing_task_member_ids is not None:
        existing_task_member_ids.add(member.id)


def _find_manager(db: Session) -> User | None:
    gym_id = get_current_gym_id()
    filters = [
        User.deleted_at.is_(None),
        User.role.in_([RoleEnum.OWNER, RoleEnum.MANAGER]),
        User.is_active.is_(True),
    ]
    if gym_id:
        filters.append(User.gym_id == gym_id)
    return db.scalar(
        select(User)
        .where(*filters)
        .order_by(
            case((User.role == RoleEnum.OWNER, 0), else_=1),
            User.created_at.asc(),
        )
        .limit(1)
    )


def _ensure_manager_alert_task(
    db: Session,
    member: Member,
    manager_id,
    *,
    existing_task_pairs: set[tuple] | None = None,
) -> None:
    task_key = (member.id, manager_id)
    if existing_task_pairs is not None and task_key in existing_task_pairs:
        return
    if existing_task_pairs is None:
        existing_task = db.scalar(
            select(Task).where(
                Task.member_id == member.id,
                Task.assigned_to_user_id == manager_id,
                Task.title.ilike("%Escalar churn%"),
                Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
                Task.deleted_at.is_(None),
            )
        )
        if existing_task:
            return

    task = Task(
        member_id=member.id,
        assigned_to_user_id=manager_id,
        title=f"Escalar churn - {member.full_name}",
        description="Aluno com 21+ dias sem treino. Acionar gerente responsavel.",
        priority=TaskPriority.URGENT,
        status=TaskStatus.TODO,
        kanban_column=TaskStatus.TODO.value,
        extra_data={
            "source": "retention_automation",
            "stage": "21d",
            "owner_role": "manager",
        },
    )
    db.add(task)
    if existing_task_pairs is not None:
        existing_task_pairs.add(task_key)
    log_audit_event(
        db,
        action="manager_alert_generated",
        entity="member",
        entity_id=member.id,
        member_id=member.id,
        details={"reason": "21_days_without_checkin"},
        flush=False,
    )


def _record_stage(db: Session, member_id, stage_action: str) -> None:
    log_audit_event(
        db,
        action=stage_action,
        entity="member",
        member_id=member_id,
        entity_id=member_id,
        details={"source": "risk_automation"},
        flush=False,
    )


def _can_trigger_stage(
    db: Session,
    member_id,
    stage_action: str,
    triggered_stages: set[tuple] | None = None,
) -> bool:
    if triggered_stages is not None:
        return (member_id, stage_action) not in triggered_stages

    existing_stage = db.scalar(
        select(AuditLog.id).where(
            AuditLog.member_id == member_id,
            AuditLog.action == stage_action,
        )
    )
    return existing_stage is None
