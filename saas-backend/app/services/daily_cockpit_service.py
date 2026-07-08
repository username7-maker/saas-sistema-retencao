"""Agregado "rotina do dia" do cockpit comercial (spec 053 / slot M1/cockpit-api).

Responde, numa chamada, as três primeiras perguntas da manhã da equipe:
quais leads precisam de follow-up, quais alunos estão em atenção e quais
ações vencem hoje — cada item com deep-link pra tela de execução existente.

Sem cache de propósito: cockpit é operacional, dado fresco na recepção.
"""
from datetime import datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Lead, Member, Task
from app.models.ai_triage_recommendation import AITriageRecommendation
from app.models.enums import LeadStage, MemberStatus, RiskLevel, TaskPriority, TaskStatus
from app.schemas.daily_cockpit import (
    CockpitActionToday,
    CockpitCounts,
    CockpitLeadFollowup,
    CockpitMemberAttention,
    DailyCockpitResponse,
)

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")
FOLLOWUP_STALE_HOURS = 48
OPEN_LEAD_STAGES = (
    LeadStage.NEW,
    LeadStage.CONTACT,
    LeadStage.VISIT,
    LeadStage.TRIAL,
    LeadStage.PROPOSAL,
    LeadStage.MEETING_SCHEDULED,
    LeadStage.PROPOSAL_SENT,
)
LIST_CAP = 10

_RETENTION_STAGE_LABELS = {
    "monitoring": "monitoramento",
    "attention": "atenção",
    "recovery": "recuperação",
    "reactivation": "reativação",
    "manager_escalation": "escalada ao gestor",
    "cold_base": "base fria",
}


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _days_between(now: datetime, past: datetime | None) -> int | None:
    if past is None:
        return None
    if past.tzinfo is None:
        past = past.replace(tzinfo=timezone.utc)
    return max(0, (now - past).days)


def _end_of_today_utc(now: datetime) -> datetime:
    today_sp = now.astimezone(SAO_PAULO_TZ).date()
    return datetime.combine(today_sp, time(23, 59, 59), tzinfo=SAO_PAULO_TZ).astimezone(timezone.utc)


def _followup_reason(days_since_contact: int | None) -> str:
    if days_since_contact is None:
        return "Nunca contatado"
    if days_since_contact < 1:
        return "Último contato há menos de 1 dia"
    unit = "dia" if days_since_contact == 1 else "dias"
    return f"Sem contato há {days_since_contact} {unit}"


def _attention_reason(risk_level: str, retention_stage: str | None, days_without_checkin: int | None) -> str:
    parts: list[str] = []
    if days_without_checkin is not None and days_without_checkin > 0:
        unit = "dia" if days_without_checkin == 1 else "dias"
        parts.append(f"{days_without_checkin} {unit} sem treinar")
    elif days_without_checkin is None:
        parts.append("Sem check-in registrado")
    if retention_stage:
        label = _RETENTION_STAGE_LABELS.get(retention_stage, retention_stage)
        parts.append(f"estágio {label}")
    if not parts:
        parts.append("Risco alto" if risk_level == RiskLevel.RED.value else "Risco moderado")
    return " · ".join(parts)


def _leads_needing_followup(
    db: Session, *, gym_id: UUID, now: datetime
) -> tuple[list[CockpitLeadFollowup], int]:
    stale_cutoff = now - timedelta(hours=FOLLOWUP_STALE_HOURS)
    criteria = [
        Lead.gym_id == gym_id,
        Lead.deleted_at.is_(None),
        Lead.stage.in_(OPEN_LEAD_STAGES),
        or_(Lead.last_contact_at.is_(None), Lead.last_contact_at < stale_cutoff),
    ]
    total = db.scalar(select(func.count()).select_from(Lead).where(*criteria)) or 0
    leads = db.scalars(
        select(Lead)
        .where(*criteria)
        .order_by(Lead.last_contact_at.asc().nulls_first())
        .limit(LIST_CAP)
    ).all()
    items = []
    for lead in leads:
        days = _days_between(now, lead.last_contact_at)
        items.append(
            CockpitLeadFollowup(
                lead_id=lead.id,
                full_name=lead.full_name,
                phone=lead.phone,
                stage=_enum_value(lead.stage),
                days_since_contact=days,
                reason=_followup_reason(days),
                href="/crm",
            )
        )
    return items, int(total)


def _members_attention(
    db: Session, *, gym_id: UUID, now: datetime
) -> tuple[list[CockpitMemberAttention], int]:
    criteria = [
        Member.gym_id == gym_id,
        Member.deleted_at.is_(None),
        Member.status == MemberStatus.ACTIVE,
        Member.risk_level.in_((RiskLevel.RED, RiskLevel.YELLOW)),
    ]
    total = db.scalar(select(func.count()).select_from(Member).where(*criteria)) or 0
    red_first = case((Member.risk_level == RiskLevel.RED, 0), else_=1)
    members = db.scalars(
        select(Member)
        .where(*criteria)
        .order_by(red_first, Member.risk_score.desc())
        .limit(LIST_CAP)
    ).all()
    items = []
    for member in members:
        days = _days_between(now, member.last_checkin_at)
        risk_level = _enum_value(member.risk_level)
        items.append(
            CockpitMemberAttention(
                member_id=member.id,
                full_name=member.full_name,
                risk_level=risk_level,
                retention_stage=member.retention_stage,
                days_without_checkin=days,
                reason=_attention_reason(risk_level, member.retention_stage, days),
                href="/dashboard/retention",
            )
        )
    return items, int(total)


def _actions_today(
    db: Session, *, gym_id: UUID, now: datetime
) -> tuple[list[CockpitActionToday], int]:
    end_of_today = _end_of_today_utc(now)
    criteria = [
        Task.gym_id == gym_id,
        Task.deleted_at.is_(None),
        Task.status.in_((TaskStatus.TODO, TaskStatus.DOING)),
        Task.due_date.is_not(None),
        Task.due_date <= end_of_today,
    ]
    total = db.scalar(select(func.count()).select_from(Task).where(*criteria)) or 0
    overdue_rank = case((Task.due_date < now, 0), else_=1)
    priority_rank = case(
        (Task.priority == TaskPriority.URGENT, 0),
        (Task.priority == TaskPriority.HIGH, 1),
        (Task.priority == TaskPriority.MEDIUM, 2),
        else_=3,
    )
    tasks = db.scalars(
        select(Task)
        .options(selectinload(Task.member), selectinload(Task.lead))
        .where(*criteria)
        .order_by(overdue_rank, priority_rank, Task.due_date.asc())
        .limit(LIST_CAP)
    ).all()
    items = []
    for task in tasks:
        due = task.due_date
        if due is not None and due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        target_name = None
        if task.member is not None:
            target_name = task.member.full_name
        elif task.lead is not None:
            target_name = task.lead.full_name
        items.append(
            CockpitActionToday(
                task_id=task.id,
                title=task.title,
                priority=_enum_value(task.priority),
                due_date=due,
                overdue=bool(due is not None and due < now),
                target_name=target_name,
                href="/tasks",
            )
        )
    return items, int(total)


def _triage_pending_count(db: Session, *, gym_id: UUID) -> int:
    total = db.scalar(
        select(func.count())
        .select_from(AITriageRecommendation)
        .where(
            AITriageRecommendation.gym_id == gym_id,
            AITriageRecommendation.approval_state == "pending",
        )
    )
    return int(total or 0)


def get_daily_cockpit(db: Session, *, gym_id: UUID) -> DailyCockpitResponse:
    now = _utcnow()
    leads, leads_total = _leads_needing_followup(db, gym_id=gym_id, now=now)
    members, members_total = _members_attention(db, gym_id=gym_id, now=now)
    actions, actions_total = _actions_today(db, gym_id=gym_id, now=now)
    return DailyCockpitResponse(
        generated_at=now,
        leads_followup=leads,
        members_attention=members,
        actions_today=actions,
        triage_pending_count=_triage_pending_count(db, gym_id=gym_id),
        counts=CockpitCounts(
            leads_followup=leads_total,
            members_attention=members_total,
            actions_today=actions_total,
        ),
    )
