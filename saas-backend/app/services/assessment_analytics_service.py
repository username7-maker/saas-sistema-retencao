import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import desc, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Member
from app.models.assessment import Assessment

logger = logging.getLogger(__name__)


def get_assessments_dashboard(db: Session) -> dict:
    now = datetime.now(tz=timezone.utc)
    cutoff_90 = now - timedelta(days=90)
    today = now.date()
    next_7 = today + timedelta(days=7)

    total_members = db.scalar(select(func.count(Member.id)).where(Member.deleted_at.is_(None))) or 0
    assessed_last_90_days = db.scalar(
        select(func.count(distinct(Assessment.member_id))).where(
            Assessment.deleted_at.is_(None),
            Assessment.assessment_date >= cutoff_90,
        )
    ) or 0
    assessed_total = db.scalar(
        select(func.count(distinct(Assessment.member_id))).where(Assessment.deleted_at.is_(None))
    ) or 0
    never_assessed = max(int(total_members) - int(assessed_total), 0)

    latest_assessment_subquery = (
        select(
            Assessment.member_id.label("member_id"),
            func.max(Assessment.assessment_date).label("last_assessment_date"),
        )
        .where(Assessment.deleted_at.is_(None))
        .group_by(Assessment.member_id)
        .subquery()
    )

    overdue_assessments = db.scalar(
        select(func.count(Member.id))
        .select_from(Member)
        .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
        .where(
            Member.deleted_at.is_(None),
            or_(
                latest_assessment_subquery.c.last_assessment_date.is_(None),
                latest_assessment_subquery.c.last_assessment_date < cutoff_90,
            ),
        )
    ) or 0

    upcoming_7_days = db.scalar(
        select(func.count(distinct(Assessment.member_id))).where(
            Assessment.deleted_at.is_(None),
            Assessment.next_assessment_due.is_not(None),
            Assessment.next_assessment_due >= today,
            Assessment.next_assessment_due <= next_7,
        )
    ) or 0

    overdue_members = list(
        db.scalars(
            select(Member)
            .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
            .where(
                Member.deleted_at.is_(None),
                or_(
                    latest_assessment_subquery.c.last_assessment_date.is_(None),
                    latest_assessment_subquery.c.last_assessment_date < cutoff_90,
                ),
            )
            .order_by(Member.risk_score.desc(), Member.updated_at.desc())
            .limit(20)
        ).all()
    )

    return {
        "total_members": int(total_members),
        "assessed_last_90_days": int(assessed_last_90_days),
        "overdue_assessments": int(overdue_assessments),
        "never_assessed": int(never_assessed),
        "upcoming_7_days": int(upcoming_7_days),
        "overdue_members": overdue_members,
    }


def generate_ai_insights(db: Session, current: Assessment) -> None:
    try:
        if not settings.claude_api_key:
            return

        previous = db.scalar(
            select(Assessment)
            .where(
                Assessment.member_id == current.member_id,
                Assessment.deleted_at.is_(None),
                Assessment.assessment_date < current.assessment_date,
            )
            .order_by(desc(Assessment.assessment_date))
            .limit(1)
        )
        if not previous:
            return

        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        prompt = _build_assessment_prompt(previous, current)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        insight = response.content[0].text.strip()
        if not insight:
            return

        current.ai_analysis = insight
        current.ai_recommendations = insight
        if "risco" in insight.lower():
            current.ai_risk_flags = insight
        db.add(current)
        db.commit()
    except Exception:
        logger.exception("Erro ao gerar insights de avaliacao")


def _build_assessment_prompt(previous: Assessment, current: Assessment) -> str:
    weight_delta = _safe_delta_value(previous.weight_kg, current.weight_kg)
    body_fat_delta = _safe_delta_value(previous.body_fat_pct, current.body_fat_pct)
    bmi_delta = _safe_delta_value(previous.bmi, current.bmi)
    strength_delta = _safe_delta_value(previous.strength_score, current.strength_score)
    flexibility_delta = _safe_delta_value(previous.flexibility_score, current.flexibility_score)
    cardio_delta = _safe_delta_value(previous.cardio_score, current.cardio_score)

    return (
        "Voce e um especialista em avaliacao fisica para academias. "
        "Gere um resumo objetivo (ate 120 palavras) contendo evolucao, risco e recomendacoes praticas.\n\n"
        f"Peso atual: {current.weight_kg} kg | variacao: {weight_delta}\n"
        f"BF atual: {current.body_fat_pct}% | variacao: {body_fat_delta}\n"
        f"BMI atual: {current.bmi} | variacao: {bmi_delta}\n"
        f"Forca atual: {current.strength_score} | variacao: {strength_delta}\n"
        f"Flexibilidade atual: {current.flexibility_score} | variacao: {flexibility_delta}\n"
        f"Cardio atual: {current.cardio_score} | variacao: {cardio_delta}\n"
        "Responda em portugues brasileiro."
    )


def _safe_delta_value(before: Decimal | int | None, after: Decimal | int | None) -> str:
    if before is None or after is None:
        return "n/a"
    delta = float(after) - float(before)
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.2f}"
