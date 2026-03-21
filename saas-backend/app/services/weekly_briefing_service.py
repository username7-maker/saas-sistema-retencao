import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Checkin, Member, MemberStatus, RiskLevel, User
from app.models.enums import RoleEnum
from app.services.whatsapp_service import get_gym_instance, send_whatsapp_sync


logger = logging.getLogger(__name__)


def generate_and_send_weekly_briefing(db: Session, gym_id: UUID) -> dict:
    now = datetime.now(tz=timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    metrics = _collect_weekly_metrics(db, gym_id, now, week_ago, two_weeks_ago)
    briefing_text = _generate_briefing_text(metrics)

    recipients = list(
        db.scalars(
            select(User).where(
                User.gym_id == gym_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.role.in_([RoleEnum.OWNER, RoleEnum.MANAGER]),
                User.phone.is_not(None),
                User.phone != "",
            )
        ).all()
    )

    instance = get_gym_instance(db, gym_id)
    sent_count = 0
    for user in recipients:
        try:
            send_whatsapp_sync(
                db,
                phone=user.phone,
                message=briefing_text,
                instance=instance,
                template_name="weekly_briefing",
            )
            sent_count += 1
        except Exception:
            logger.exception("Falha ao enviar briefing para user %s", user.id)

    db.commit()
    return {"briefing_sent_to": sent_count, "total_recipients": len(recipients)}


def _collect_weekly_metrics(
    db: Session,
    gym_id: UUID,
    now: datetime,
    week_ago: datetime,
    two_weeks_ago: datetime,
) -> dict:
    checkins_this_week = db.scalar(
        select(func.count()).select_from(Checkin).where(
            Checkin.gym_id == gym_id,
            Checkin.checkin_at >= week_ago,
            Checkin.checkin_at < now,
        )
    ) or 0

    checkins_last_week = db.scalar(
        select(func.count()).select_from(Checkin).where(
            Checkin.gym_id == gym_id,
            Checkin.checkin_at >= two_weeks_ago,
            Checkin.checkin_at < week_ago,
        )
    ) or 0

    new_at_risk = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.gym_id == gym_id,
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.risk_level.in_([RiskLevel.YELLOW, RiskLevel.RED]),
            Member.updated_at >= week_ago,
        )
    ) or 0

    mrr_at_risk = db.scalar(
        select(func.sum(Member.monthly_fee)).where(
            Member.gym_id == gym_id,
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.risk_level == RiskLevel.RED,
        )
    ) or Decimal("0.00")

    total_active = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.gym_id == gym_id,
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
        )
    ) or 0

    return {
        "checkins_this_week": checkins_this_week,
        "checkins_last_week": checkins_last_week,
        "checkins_delta_pct": _delta_pct(checkins_last_week, checkins_this_week),
        "new_at_risk": new_at_risk,
        "mrr_at_risk": float(mrr_at_risk),
        "total_active": total_active,
    }


def _delta_pct(previous: int, current: int) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _generate_briefing_text(metrics: dict) -> str:
    if settings.claude_api_key:
        try:
            return _generate_ai_briefing(metrics)
        except Exception:
            logger.exception("Fallback para briefing regra-based")

    return _generate_rule_based_briefing(metrics)


def _generate_ai_briefing(metrics: dict) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.claude_api_key)
    prompt = (
        "Voce e o assistente de inteligencia de uma academia. "
        "Gere um briefing semanal executivo em portugues brasileiro, tom profissional e direto, "
        "maximo 200 palavras. Use emojis de forma moderada. "
        "Dados da semana:\n"
        f"- Check-ins: {metrics['checkins_this_week']} (variacao: {metrics['checkins_delta_pct']:+.1f}% vs semana anterior)\n"
        f"- Novos alunos em risco: {metrics['new_at_risk']}\n"
        f"- MRR em risco (alunos vermelhos): R$ {metrics['mrr_at_risk']:,.2f}\n"
        f"- Total de alunos ativos: {metrics['total_active']}\n"
        "Destaque os pontos positivos e negativos. Termine com 1-2 recomendacoes acionaveis."
    )
    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()[:1000]


def _generate_rule_based_briefing(metrics: dict) -> str:
    lines = [
        "*Briefing Semanal da Academia*\n",
        f"Check-ins: {metrics['checkins_this_week']} ({metrics['checkins_delta_pct']:+.1f}% vs semana anterior)",
        f"Novos alunos em risco: {metrics['new_at_risk']}",
        f"MRR em risco: R$ {metrics['mrr_at_risk']:,.2f}",
        f"Alunos ativos: {metrics['total_active']}",
    ]
    if metrics["checkins_delta_pct"] < -10:
        lines.append("\nQueda significativa nos check-ins. Recomendamos acionar campanha de reengajamento.")
    if metrics["new_at_risk"] > 5:
        lines.append("\nAumento de alunos em risco. Priorize ligacoes de retencao esta semana.")
    return "\n".join(lines)
