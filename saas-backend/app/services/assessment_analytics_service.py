import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import desc, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Member
from app.models.assessment import Assessment, MemberConstraints, MemberGoal

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

    member_ordering = (Member.risk_score.desc(), Member.updated_at.desc())

    total_members_items = list(
        db.scalars(
            select(Member)
            .where(Member.deleted_at.is_(None))
            .order_by(*member_ordering)
            .limit(20)
        ).all()
    )

    assessed_members = list(
        db.scalars(
            select(Member)
            .join(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
            .where(
                Member.deleted_at.is_(None),
                latest_assessment_subquery.c.last_assessment_date >= cutoff_90,
            )
            .order_by(latest_assessment_subquery.c.last_assessment_date.desc(), *member_ordering)
            .limit(20)
        ).all()
    )

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
            .order_by(*member_ordering)
            .limit(20)
        ).all()
    )

    never_assessed_members = list(
        db.scalars(
            select(Member)
            .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
            .where(
                Member.deleted_at.is_(None),
                latest_assessment_subquery.c.last_assessment_date.is_(None),
            )
            .order_by(*member_ordering)
            .limit(20)
        ).all()
    )

    upcoming_members_subquery = (
        select(distinct(Assessment.member_id).label("member_id"))
        .where(
            Assessment.deleted_at.is_(None),
            Assessment.next_assessment_due.is_not(None),
            Assessment.next_assessment_due >= today,
            Assessment.next_assessment_due <= next_7,
        )
        .subquery()
    )
    upcoming_members = list(
        db.scalars(
            select(Member)
            .join(upcoming_members_subquery, upcoming_members_subquery.c.member_id == Member.id)
            .where(Member.deleted_at.is_(None))
            .order_by(*member_ordering)
            .limit(20)
        ).all()
    )

    return {
        "total_members": int(total_members),
        "assessed_last_90_days": int(assessed_last_90_days),
        "overdue_assessments": int(overdue_assessments),
        "never_assessed": int(never_assessed),
        "upcoming_7_days": int(upcoming_7_days),
        "total_members_items": total_members_items,
        "assessed_members": assessed_members,
        "overdue_members": overdue_members,
        "never_assessed_members": never_assessed_members,
        "upcoming_members": upcoming_members,
    }


def generate_ai_insights(db: Session, current: Assessment) -> None:
    try:
        previous_assessments = list(
            db.scalars(
                select(Assessment)
                .where(
                    Assessment.member_id == current.member_id,
                    Assessment.deleted_at.is_(None),
                    Assessment.assessment_date < current.assessment_date,
                )
                .order_by(desc(Assessment.assessment_date))
                .limit(3)
            ).all()
        )

        goals = list(
            db.scalars(
                select(MemberGoal).where(
                    MemberGoal.member_id == current.member_id,
                    MemberGoal.deleted_at.is_(None),
                    MemberGoal.status == "active",
                )
            ).all()
        )

        constraints = db.scalar(
            select(MemberConstraints).where(
                MemberConstraints.member_id == current.member_id,
                MemberConstraints.deleted_at.is_(None),
            )
        )

        if not settings.claude_api_key:
            _apply_fallback_analysis(current, previous_assessments)
            db.add(current)
            db.commit()
            return

        import anthropic
        from app.utils.claude import _parse_claude_json

        prompt = _build_comprehensive_assessment_prompt(current, previous_assessments, goals, constraints)
        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=800,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        parsed = _parse_claude_json(text)
        current.ai_analysis = (parsed.get("analysis") or "")[:2000]
        current.ai_recommendations = (parsed.get("recommendations") or "")[:2000]
        current.ai_risk_flags = (parsed.get("risk_flags") or "")[:2000]
        db.add(current)
        db.commit()
    except Exception:
        logger.exception("Erro ao gerar insights de avaliacao - usando fallback")
        try:
            _apply_fallback_analysis(current, [])
            db.add(current)
            db.commit()
        except Exception:
            logger.exception("Fallback de analise tambem falhou")


def _build_comprehensive_assessment_prompt(
    current: Assessment,
    previous: list[Assessment],
    goals: list[MemberGoal],
    constraints: MemberConstraints | None,
) -> str:
    if previous:
        prev = previous[0]
        evolution_lines = [
            f"Peso: {current.weight_kg}kg (anterior: {prev.weight_kg}kg)",
            f"BF: {current.body_fat_pct}% (anterior: {prev.body_fat_pct}%)",
            f"IMC: {current.bmi} (anterior: {prev.bmi})",
            f"Forca: {current.strength_score} (anterior: {prev.strength_score})",
            f"Flexibilidade: {current.flexibility_score} (anterior: {prev.flexibility_score})",
            f"Cardio: {current.cardio_score} (anterior: {prev.cardio_score})",
        ]
    else:
        evolution_lines = [
            f"Peso: {current.weight_kg}kg",
            f"BF: {current.body_fat_pct}%",
            f"IMC: {current.bmi}",
            f"Forca: {current.strength_score}",
            f"Flexibilidade: {current.flexibility_score}",
            f"Cardio: {current.cardio_score}",
        ]

    goals_text = "Nenhuma meta ativa."
    if goals:
        goals_text = "; ".join(
            f"{g.title} (alvo: {g.target_value} {g.unit or ''}, progresso: {g.progress_pct}%)"
            for g in goals
        )

    constraints_text = "Nenhuma restricao registrada."
    if constraints:
        parts = []
        if constraints.medical_conditions:
            parts.append(f"Condicoes: {constraints.medical_conditions}")
        if constraints.injuries:
            parts.append(f"Lesoes: {constraints.injuries}")
        if constraints.medications:
            parts.append(f"Medicamentos: {constraints.medications}")
        if constraints.contraindications:
            parts.append(f"Contraindicacoes: {constraints.contraindications}")
        if parts:
            constraints_text = "; ".join(parts)

    return (
        "Voce e um especialista em avaliacao fisica para academias. "
        "Retorne um JSON com tres campos: analysis, recommendations, risk_flags.\n"
        "- analysis: resumo da evolucao do aluno (max 150 palavras)\n"
        "- recommendations: recomendacoes praticas de treino e nutricao (max 150 palavras)\n"
        "- risk_flags: alertas de saude ou riscos identificados, ou string vazia se nenhum\n\n"
        f"Dados atuais:\n" + "\n".join(evolution_lines) + "\n\n"
        f"Metas ativas: {goals_text}\n"
        f"Restricoes: {constraints_text}\n"
        f"Avaliacao numero: {current.assessment_number}\n"
        "Responda em portugues brasileiro."
    )


def _apply_fallback_analysis(current: Assessment, previous: list[Assessment]) -> None:
    parts = []
    if current.body_fat_pct and current.body_fat_pct > 30:
        parts.append("Percentual de gordura elevado.")
    if current.bmi and current.bmi > 30:
        parts.append("IMC acima de 30 indica obesidade.")
    if current.resting_hr and current.resting_hr > 90:
        parts.append("Frequencia cardiaca de repouso elevada.")
    if previous:
        prev = previous[0]
        if prev.weight_kg and current.weight_kg and current.weight_kg > prev.weight_kg:
            parts.append(f"Ganho de {float(current.weight_kg - prev.weight_kg):.1f}kg desde ultima avaliacao.")

    current.ai_analysis = " ".join(parts) if parts else "Avaliacao registrada. Analise de IA indisponivel."
    current.ai_recommendations = "Recomendamos consultar o educador fisico para orientacoes personalizadas."
    if parts:
        current.ai_risk_flags = " ".join(parts)


def _safe_delta_value(before: Decimal | int | None, after: Decimal | int | None) -> str:
    if before is None or after is None:
        return "n/a"
    delta = float(after) - float(before)
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.2f}"
