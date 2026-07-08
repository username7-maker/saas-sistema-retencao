"""Funil comercial semanal esforço→resultado (spec 053 / slot M1/funnel-api).

Contatos feitos → respostas recebidas → conversões (vendas + novos alunos +
alunos recuperados do risco). Só leitura de tabelas existentes — sem migração.
Semana vazia retorna zeros; nunca 404/null. Sem cache (dado operacional).
"""
from datetime import datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Lead, Member, Task
from app.models.enums import LeadStage, TaskStatus
from app.models.member_risk_history import MemberRiskHistory
from app.models.message_log import MessageLog
from app.schemas.commercial_funnel import (
    ConversionBreakdown,
    FunnelStage,
    WeeklyFunnelResponse,
)

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")

_RECOVERED_FROM_LEVELS = ("red", "yellow")


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _week_window(now: datetime, week_offset: int) -> tuple[datetime, datetime]:
    """Segunda 00:00 (America/Sao_Paulo) até min(now, fim da semana), em UTC."""
    sp_now = now.astimezone(SAO_PAULO_TZ)
    monday = sp_now.date() - timedelta(days=sp_now.weekday())
    start_sp = datetime.combine(monday + timedelta(weeks=week_offset), time(0, 0), tzinfo=SAO_PAULO_TZ)
    end_sp = start_sp + timedelta(days=7)
    start = start_sp.astimezone(timezone.utc)
    end = min(now, end_sp.astimezone(timezone.utc))
    return start, end


def _count_contacts(db: Session, *, gym_id: UUID, start: datetime, end: datetime) -> int:
    messages = db.scalar(
        select(func.count())
        .select_from(MessageLog)
        .where(
            MessageLog.gym_id == gym_id,
            MessageLog.created_at >= start,
            MessageLog.created_at < end,
            or_(MessageLog.direction.is_(None), MessageLog.direction != "inbound"),
            MessageLog.status != "failed",
        )
    ) or 0
    tasks_done = db.scalar(
        select(func.count())
        .select_from(Task)
        .where(
            Task.gym_id == gym_id,
            Task.deleted_at.is_(None),
            Task.status == TaskStatus.DONE,
            Task.completed_at.is_not(None),
            Task.completed_at >= start,
            Task.completed_at < end,
            or_(Task.member_id.is_not(None), Task.lead_id.is_not(None)),
        )
    ) or 0
    return int(messages) + int(tasks_done)


def _count_responses(db: Session, *, gym_id: UUID, start: datetime, end: datetime) -> int:
    total = db.scalar(
        select(func.count())
        .select_from(MessageLog)
        .where(
            MessageLog.gym_id == gym_id,
            MessageLog.created_at >= start,
            MessageLog.created_at < end,
            MessageLog.direction == "inbound",
        )
    )
    return int(total or 0)


def _count_risk_recovered(db: Session, *, gym_id: UUID, start: datetime, end: datetime) -> int:
    """Membros cujo registro green na janela sucede imediatamente um red/yellow."""
    green_member_ids = db.scalars(
        select(MemberRiskHistory.member_id)
        .where(
            MemberRiskHistory.gym_id == gym_id,
            MemberRiskHistory.recorded_at >= start,
            MemberRiskHistory.recorded_at < end,
            MemberRiskHistory.level == "green",
        )
        .distinct()
    ).all()
    if not green_member_ids:
        return 0
    rows = db.scalars(
        select(MemberRiskHistory)
        .where(
            MemberRiskHistory.gym_id == gym_id,
            MemberRiskHistory.member_id.in_(green_member_ids),
            MemberRiskHistory.recorded_at < end,
        )
        .order_by(MemberRiskHistory.member_id, MemberRiskHistory.recorded_at)
    ).all()
    recovered: set[UUID] = set()
    previous_by_member: dict[UUID, str] = {}
    for row in rows:
        recorded_at = row.recorded_at
        if recorded_at is not None and recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)
        previous = previous_by_member.get(row.member_id)
        in_window = recorded_at is not None and start <= recorded_at < end
        if in_window and row.level == "green" and previous in _RECOVERED_FROM_LEVELS:
            recovered.add(row.member_id)
        previous_by_member[row.member_id] = row.level
    return len(recovered)


def _count_conversions(db: Session, *, gym_id: UUID, start: datetime, end: datetime) -> ConversionBreakdown:
    leads_won = db.scalar(
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.gym_id == gym_id,
            Lead.deleted_at.is_(None),
            Lead.stage == LeadStage.WON,
            Lead.updated_at >= start,
            Lead.updated_at < end,
        )
    ) or 0
    start_date = start.astimezone(SAO_PAULO_TZ).date()
    end_date = end.astimezone(SAO_PAULO_TZ).date()
    members_joined = db.scalar(
        select(func.count())
        .select_from(Member)
        .where(
            Member.gym_id == gym_id,
            Member.deleted_at.is_(None),
            Member.join_date.is_not(None),
            Member.join_date >= start_date,
            Member.join_date <= end_date,
        )
    ) or 0
    return ConversionBreakdown(
        leads_won=int(leads_won),
        members_joined=int(members_joined),
        risk_recovered=_count_risk_recovered(db, gym_id=gym_id, start=start, end=end),
    )


def get_weekly_funnel(db: Session, *, gym_id: UUID, week_offset: int = 0) -> WeeklyFunnelResponse:
    now = _utcnow()
    start, end = _week_window(now, week_offset)
    prev_start, prev_end = _week_window(now, week_offset - 1)

    contacts = _count_contacts(db, gym_id=gym_id, start=start, end=end)
    responses = _count_responses(db, gym_id=gym_id, start=start, end=end)
    breakdown = _count_conversions(db, gym_id=gym_id, start=start, end=end)
    conversions = breakdown.leads_won + breakdown.members_joined + breakdown.risk_recovered

    prev_contacts = _count_contacts(db, gym_id=gym_id, start=prev_start, end=prev_end)
    prev_responses = _count_responses(db, gym_id=gym_id, start=prev_start, end=prev_end)
    prev_breakdown = _count_conversions(db, gym_id=gym_id, start=prev_start, end=prev_end)
    prev_conversions = (
        prev_breakdown.leads_won + prev_breakdown.members_joined + prev_breakdown.risk_recovered
    )

    return WeeklyFunnelResponse(
        week_start=start,
        week_end=end,
        week_offset=week_offset,
        contacts=FunnelStage(
            key="contacts", label="Contatos feitos", value=contacts, previous_value=prev_contacts
        ),
        responses=FunnelStage(
            key="responses", label="Respostas recebidas", value=responses, previous_value=prev_responses
        ),
        conversions=FunnelStage(
            key="conversions", label="Conversões", value=conversions, previous_value=prev_conversions
        ),
        conversion_breakdown=breakdown,
    )
