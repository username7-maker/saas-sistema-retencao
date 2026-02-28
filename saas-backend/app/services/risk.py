from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.database import get_current_gym_id
from app.models import AuditLog, Checkin, Member, MemberStatus, RiskAlert, RiskLevel, RoleEnum, Task, TaskPriority, TaskStatus, User
from app.services.audit_service import log_audit_event
from app.services.automation_engine import run_automation_rules
from app.services.notification_service import create_notification
from app.services.websocket_manager import websocket_manager
from app.utils.email import send_email


@dataclass(frozen=True)
class RiskResult:
    score: int
    level: RiskLevel
    reasons: dict
    days_without_checkin: int


def calculate_risk_score(db: Session, member: Member) -> RiskResult:
    now = datetime.now(tz=timezone.utc)
    reference_dt = member.last_checkin_at or datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)
    if reference_dt.tzinfo is None:
        reference_dt = reference_dt.replace(tzinfo=timezone.utc)
    days_without_checkin = max(0, (now - reference_dt).days)

    inactivity_points = _inactivity_points(days_without_checkin)
    frequency_points, frequency_drop_pct = _frequency_drop_points(db, member.id, now)
    shift_points, shift_change_hours = _shift_change_points(db, member.id, now)
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
    }
    return RiskResult(score=score, level=level, reasons=reasons, days_without_checkin=days_without_checkin)


_AUTOMATION_STAGES = ["automation_3d", "automation_7d", "automation_10d", "automation_14d", "automation_21d"]


def run_daily_risk_processing(db: Session) -> dict[str, int]:
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
    member_ids = [m.id for m in members]
    triggered_stages: set[tuple] = set(
        db.execute(
            select(AuditLog.member_id, AuditLog.action).where(
                AuditLog.member_id.in_(member_ids),
                AuditLog.action.in_(_AUTOMATION_STAGES),
            )
        ).all()
    )

    alerts_created = 0
    automations_triggered = 0

    for member in members:
        result = calculate_risk_score(db, member)
        member.risk_score = result.score
        member.risk_level = result.level

        if result.score >= 40:
            actions = _run_inactivity_automations(db, member, result.days_without_checkin, result.level, triggered_stages)
            automations_triggered += len(actions)
            _create_or_update_alert(db, member, result, actions)
            alerts_created += 1

        db.add(member)

    db.commit()
    if analyzed:
        invalidate_dashboard_cache("risk", "tasks")

    try:
        rule_results = run_automation_rules(db)
        automations_triggered += len([r for r in rule_results if r.get("status") not in ("skipped", "error")])
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Erro ao executar regras de automacao apos processamento de risco")

    return {
        "members_analyzed": analyzed,
        "risk_alerts_processed": alerts_created,
        "automations_triggered": automations_triggered,
    }


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


def _frequency_drop_points(db: Session, member_id, now: datetime) -> tuple[int, float]:
    recent_start = now - timedelta(days=14)
    prev_start = now - timedelta(days=28)

    recent = db.scalar(
        select(func.count()).select_from(Checkin).where(
            Checkin.member_id == member_id,
            Checkin.checkin_at >= recent_start,
            Checkin.checkin_at < now,
        )
    ) or 0

    previous = db.scalar(
        select(func.count()).select_from(Checkin).where(
            Checkin.member_id == member_id,
            Checkin.checkin_at >= prev_start,
            Checkin.checkin_at < recent_start,
        )
    ) or 0

    if previous <= 0:
        return (12, 100.0) if recent == 0 else (0, 0.0)

    drop_pct = max(0.0, ((previous - recent) / previous) * 100)
    if drop_pct >= 70:
        return 20, drop_pct
    if drop_pct >= 40:
        return 12, drop_pct
    if drop_pct >= 20:
        return 6, drop_pct
    return 0, drop_pct


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


def _create_or_update_alert(db: Session, member: Member, risk_result: RiskResult, actions: list[dict]) -> None:
    current_alert = db.scalar(
        select(RiskAlert)
        .where(
            RiskAlert.member_id == member.id,
            RiskAlert.resolved.is_(False),
        )
        .order_by(RiskAlert.created_at.desc())
        .limit(1)
    )

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
        return

    alert = RiskAlert(
        member_id=member.id,
        score=risk_result.score,
        level=risk_result.level,
        reasons=risk_result.reasons,
        action_history=actions,
        automation_stage=f"d{risk_result.days_without_checkin}",
    )
    db.add(alert)
    db.flush()
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


def _run_inactivity_automations(
    db: Session,
    member: Member,
    days_without_checkin: int,
    level: RiskLevel,
    triggered_stages: set[tuple],
) -> list[dict]:
    now = datetime.now(tz=timezone.utc)
    actions: list[dict] = []

    def already_triggered(stage: str) -> bool:
        return (member.id, stage) in triggered_stages

    def mark_triggered(stage: str) -> None:
        triggered_stages.add((member.id, stage))
        _record_stage(db, member.id, stage)

    if days_without_checkin >= 3 and not already_triggered("automation_3d"):
        sent = False
        if member.email:
            sent = send_email(member.email, "Volte para o treino hoje", "Seu progresso importa. Vamos retomar o ritmo?")
        if sent:
            actions.append({"type": "email", "stage": "3d", "timestamp": now.isoformat(), "status": "sent"})
            mark_triggered("automation_3d")
        else:
            actions.append({"type": "email", "stage": "3d", "timestamp": now.isoformat(), "status": "failed"})

    if days_without_checkin >= 7 and not already_triggered("automation_7d"):
        _ensure_call_task(db, member, "7d")
        actions.append({"type": "task", "stage": "7d", "timestamp": now.isoformat()})
        mark_triggered("automation_7d")

    if days_without_checkin >= 10 and not already_triggered("automation_10d"):
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

    if days_without_checkin >= 14 and not already_triggered("automation_14d"):
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

    if days_without_checkin >= 21 and not already_triggered("automation_21d"):
        manager = _find_manager(db)
        if manager:
            _ensure_manager_alert_task(db, member, manager.id)
        actions.append({"type": "manager_alert", "stage": "21d", "timestamp": now.isoformat()})
        mark_triggered("automation_21d")

    return actions


def _ensure_call_task(db: Session, member: Member, stage: str) -> None:
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


def _ensure_manager_alert_task(db: Session, member: Member, manager_id) -> None:
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
    log_audit_event(
        db,
        action="manager_alert_generated",
        entity="member",
        entity_id=member.id,
        member_id=member.id,
        details={"reason": "21_days_without_checkin"},
    )


def _record_stage(db: Session, member_id, stage_action: str) -> None:
    log_audit_event(
        db,
        action=stage_action,
        entity="member",
        member_id=member_id,
        entity_id=member_id,
        details={"source": "risk_automation"},
    )
