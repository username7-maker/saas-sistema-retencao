from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Checkin, Member, MemberStatus, RiskAlert, RiskLevel, RoleEnum, Task, TaskPriority, TaskStatus, User
from app.services.audit_service import log_audit_event
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


def run_daily_risk_processing(db: Session) -> dict[str, int]:
    members = db.scalars(
        select(Member).where(
            Member.deleted_at.is_(None),
            Member.status.in_([MemberStatus.ACTIVE, MemberStatus.PAUSED]),
        )
    ).all()

    analyzed = len(members)
    alerts_created = 0
    automations_triggered = 0

    for member in members:
        result = calculate_risk_score(db, member)
        member.risk_score = result.score
        member.risk_level = result.level

        if result.score >= 40:
            actions = _run_inactivity_automations(db, member, result.days_without_checkin, result.level)
            automations_triggered += len(actions)
            _create_or_update_alert(db, member, result, actions)
            alerts_created += 1

        db.add(member)

    db.commit()
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
    today_start = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    current_alert = db.scalar(
        select(RiskAlert).where(
            RiskAlert.member_id == member.id,
            RiskAlert.resolved.is_(False),
            RiskAlert.created_at >= today_start,
        )
    )

    if current_alert:
        current_alert.score = risk_result.score
        current_alert.level = risk_result.level
        current_alert.reasons = risk_result.reasons
        current_alert.action_history = (current_alert.action_history or []) + actions
        db.add(current_alert)
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


def _run_inactivity_automations(db: Session, member: Member, days_without_checkin: int, level: RiskLevel) -> list[dict]:
    now = datetime.now(tz=timezone.utc)
    actions: list[dict] = []

    if days_without_checkin >= 3 and _can_trigger_stage(db, member.id, "automation_3d"):
        if member.email:
            send_email(member.email, "Volte para o treino hoje", "Seu progresso importa. Vamos retomar o ritmo?")
        actions.append({"type": "email", "stage": "3d", "timestamp": now.isoformat()})
        _record_stage(db, member.id, "automation_3d")

    if days_without_checkin >= 7 and _can_trigger_stage(db, member.id, "automation_7d"):
        _ensure_call_task(db, member, "7d")
        actions.append({"type": "task", "stage": "7d", "timestamp": now.isoformat()})
        _record_stage(db, member.id, "automation_7d")

    if days_without_checkin >= 10 and _can_trigger_stage(db, member.id, "automation_10d"):
        if member.email:
            send_email(
                member.email,
                "Dica personalizada de treino",
                "Separamos uma dica curta para facilitar sua volta. Procure a recepcao para ajustar seu plano.",
            )
        actions.append({"type": "email", "stage": "10d", "timestamp": now.isoformat()})
        _record_stage(db, member.id, "automation_10d")

    if days_without_checkin >= 14 and _can_trigger_stage(db, member.id, "automation_14d"):
        if level == RiskLevel.YELLOW:
            member.risk_level = RiskLevel.RED
            member.risk_score = max(member.risk_score, 70)
        actions.append(
            {
                "type": "in_app_notification",
                "stage": "14d",
                "timestamp": now.isoformat(),
                "message": "Aluno sem treino ha 14 dias",
            }
        )
        _record_stage(db, member.id, "automation_14d")

    if days_without_checkin >= 21 and _can_trigger_stage(db, member.id, "automation_21d"):
        manager = _find_manager(db)
        if manager:
            _ensure_manager_alert_task(db, member, manager.id)
        actions.append({"type": "manager_alert", "stage": "21d", "timestamp": now.isoformat()})
        _record_stage(db, member.id, "automation_21d")

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
    return db.scalar(
        select(User)
        .where(
            User.deleted_at.is_(None),
            User.role.in_([RoleEnum.OWNER, RoleEnum.MANAGER]),
            User.is_active.is_(True),
        )
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


def _can_trigger_stage(db: Session, member_id, stage_action: str) -> bool:
    existing = db.scalar(
        select(AuditLog).where(
            AuditLog.member_id == member_id,
            AuditLog.action == stage_action,
        )
    )
    return existing is None


def _record_stage(db: Session, member_id, stage_action: str) -> None:
    log_audit_event(
        db,
        action=stage_action,
        entity="member",
        member_id=member_id,
        entity_id=member_id,
        details={"source": "risk_automation"},
    )
