import uuid
from collections import Counter, defaultdict
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
from app.utils.email import send_email


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


def calculate_risk_score(
    db: Session,
    member: Member,
    now: datetime | None = None,
    metrics: PrefetchedCheckinMetrics | None = None,
) -> RiskResult:
    now = now or datetime.now(tz=timezone.utc)
    reference_dt = member.last_checkin_at or datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)
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

    raw_score = inactivity_points + frequency_points + shift_points + nps_points - loyalty_discount
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
    triggered_stages: set[tuple] = set(
        db.execute(
            select(AuditLog.member_id, AuditLog.action).where(
                AuditLog.member_id.is_not(None),
                AuditLog.action.in_(_AUTOMATION_STAGES),
            )
        ).all()
    )
    current_alerts_by_member = _prefetch_open_risk_alerts(db)
    existing_call_task_rows = db.scalars(
        select(Task.member_id).where(
            Task.member_id.is_not(None),
            Task.title.ilike("Ligar para %"),
            Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
            Task.deleted_at.is_(None),
        )
    ).all()
    existing_call_tasks = {
        row for row in existing_call_task_rows if isinstance(row, (str, int, uuid.UUID))
    }
    manager = _find_manager(db)
    existing_manager_alert_tasks: set[tuple] = set()
    if manager:
        existing_manager_alert_tasks = set(
            db.execute(
                select(Task.member_id, Task.assigned_to_user_id).where(
                    Task.member_id.is_not(None),
                    Task.assigned_to_user_id == manager.id,
                    Task.title.ilike("%Escalar churn%"),
                    Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
                    Task.deleted_at.is_(None),
                )
            ).all()
        )

    alerts_created = 0
    automations_triggered = 0

    for member in members:
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
            if current_alert_obj is None:
                current_alert = _create_or_update_alert(
                    db,
                    member,
                    effective_result,
                    actions,
                )
            else:
                current_alert = _create_or_update_alert(
                    db,
                    member,
                    effective_result,
                    actions,
                    current_alert=current_alert_obj,
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
    if analyzed:
        invalidate_dashboard_cache("risk", "tasks")

    # NOTE: run_automation_rules() is intentionally NOT called here.
    # It is executed by daily_automations_job (jobs.py) at 02:30 UTC to avoid double-firing.
    return {
        "members_analyzed": analyzed,
        "risk_alerts_processed": alerts_created,
        "automations_triggered": automations_triggered,
    }


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


def _prefetch_member_checkin_metrics(db: Session, now: datetime) -> dict:
    ten_weeks_ago = now - timedelta(weeks=10)
    one_week_ago = now - timedelta(weeks=1)
    recent_start = now - timedelta(days=14)
    prev_start = now - timedelta(days=60)

    raw_metrics: dict = defaultdict(
        lambda: {
            "current_week_count": 0,
            "baseline_total": 0,
            "recent_hours": Counter(),
            "previous_hours": Counter(),
        }
    )

    rows = db.execute(
        select(Checkin.member_id, Checkin.checkin_at, Checkin.hour_bucket).where(
            Checkin.checkin_at >= ten_weeks_ago,
            Checkin.checkin_at < now,
        )
    ).all()

    for member_id, checkin_at, hour_bucket in rows:
        bucket = raw_metrics[member_id]
        if checkin_at >= one_week_ago:
            bucket["current_week_count"] += 1
        else:
            bucket["baseline_total"] += 1

        if checkin_at >= recent_start:
            bucket["recent_hours"][int(hour_bucket)] += 1
        elif checkin_at >= prev_start:
            bucket["previous_hours"][int(hour_bucket)] += 1

    metrics_by_member: dict = {}
    for member_id, values in raw_metrics.items():
        metrics_by_member[member_id] = PrefetchedCheckinMetrics(
            current_week_count=values["current_week_count"],
            baseline_total=values["baseline_total"],
            recent_mode_hour=_most_common_hour(values["recent_hours"]),
            previous_mode_hour=_most_common_hour(values["previous_hours"]),
        )
    return metrics_by_member


def _most_common_hour(counter: Counter) -> int | None:
    if not counter:
        return None
    return min(counter.items(), key=lambda item: (-item[1], item[0]))[0]


def _prefetch_open_risk_alerts(db: Session) -> dict:
    alerts = db.scalars(
        select(RiskAlert)
        .where(RiskAlert.resolved.is_(False))
        .order_by(RiskAlert.member_id.asc(), RiskAlert.created_at.desc())
    ).all()
    alert_by_member: dict = {}
    for alert in alerts:
        member_id = getattr(alert, "member_id", None)
        if member_id is None:
            continue
        alert_by_member.setdefault(member_id, alert)
    return alert_by_member


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
) -> RiskAlert:
    if current_alert:
        current_alert.score = risk_result.score
        current_alert.level = risk_result.level
        current_alert.reasons = risk_result.reasons
        current_alert.automation_stage = f"d{risk_result.days_without_checkin}"
        current_alert.action_history = (current_alert.action_history or []) + actions
        db.add(current_alert)
        websocket_manager.broadcast_event_sync(
            str(member.gym_id),
            "risk_alert_updated",
            {
                "member_id": str(member.id),
                "alert_id": str(current_alert.id),
                "score": current_alert.score,
                "level": current_alert.level.value,
            },
        )
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
    websocket_manager.broadcast_event_sync(
        str(member.gym_id),
        "risk_alert_created",
        {
            "member_id": str(member.id),
            "alert_id": str(alert.id),
            "score": alert.score,
            "level": alert.level.value,
        },
    )
    return alert


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
    actions: list[dict] = []

    def mark_triggered(stage: str) -> None:
        if triggered_stages is not None:
            triggered_stages.add((member.id, stage))
        _record_stage(db, member.id, stage)

    if days_without_checkin >= 3 and _can_trigger_stage(db, member.id, "automation_3d", triggered_stages):
        sent = False
        if member.email:
            sent = send_email(member.email, "Volte para o treino hoje", "Seu progresso importa. Vamos retomar o ritmo?")
        if sent:
            actions.append({"type": "email", "stage": "3d", "timestamp": now.isoformat(), "status": "sent"})
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
        sent = False
        if member.email:
            sent = send_email(
                member.email,
                "Dica personalizada de treino",
                "Separamos uma dica curta para facilitar sua volta. Procure a recepcao para ajustar seu plano.",
            )
        if sent:
            actions.append({"type": "email", "stage": "10d", "timestamp": now.isoformat(), "status": "sent"})
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
