import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, case, desc, distinct, func, literal, or_, select
from sqlalchemy.orm import Session

from app.core.circuit_breaker import claude_circuit_breaker
from app.core.config import settings
from app.database import get_current_gym_id, include_all_tenants
from app.models import Member, MemberStatus
from app.models.assessment import Assessment, MemberConstraints, MemberGoal
from app.schemas import PaginatedResponse
from app.schemas.assessment import AssessmentQueueItemOut

logger = logging.getLogger(__name__)


AssessmentQueueBucket = Literal["all", "overdue", "never", "week", "upcoming", "covered"]
AssessmentMemberBucket = Literal["overdue", "never", "week", "upcoming", "covered"]
OPERATIONAL_FIRST_ASSESSMENT_WINDOW_DAYS = 60
OPERATIONAL_REASSESSMENT_CHECKIN_WINDOW_DAYS = 30


def _resolve_gym_id(gym_id=None):
    return gym_id or get_current_gym_id()


def _scoped_statement(statement, gym_id):
    if gym_id is None:
        return statement
    return include_all_tenants(statement, reason="assessment_analytics.explicit_gym_scope")


def _latest_assessment_subquery():
    ranked_assessments = (
        select(
            Assessment.member_id.label("member_id"),
            Assessment.assessment_date.label("assessment_date"),
            Assessment.next_assessment_due.label("next_assessment_due"),
            func.row_number()
            .over(
                partition_by=Assessment.member_id,
                order_by=(Assessment.assessment_date.desc(), Assessment.updated_at.desc()),
            )
            .label("row_number"),
        )
        .where(Assessment.deleted_at.is_(None))
        .subquery()
    )

    return (
        select(
            ranked_assessments.c.member_id.label("member_id"),
            ranked_assessments.c.assessment_date.label("last_assessment_date"),
            ranked_assessments.c.next_assessment_due.label("next_assessment_due"),
        )
        .where(ranked_assessments.c.row_number == 1)
        .subquery()
    )


def _queue_conditions(last_assessment_date_col, next_assessment_due_col, *, cutoff_90, today, next_7):
    never = last_assessment_date_col.is_(None)
    overdue = and_(
        last_assessment_date_col.is_not(None),
        or_(
            last_assessment_date_col < cutoff_90,
            and_(next_assessment_due_col.is_not(None), next_assessment_due_col < today),
        ),
    )
    week = and_(
        last_assessment_date_col.is_not(None),
        last_assessment_date_col >= cutoff_90,
        next_assessment_due_col.is_not(None),
        next_assessment_due_col >= today,
        next_assessment_due_col <= next_7,
    )
    upcoming = and_(
        last_assessment_date_col.is_not(None),
        last_assessment_date_col >= cutoff_90,
        next_assessment_due_col.is_not(None),
        next_assessment_due_col > next_7,
    )
    covered = and_(
        last_assessment_date_col.is_not(None),
        last_assessment_date_col >= cutoff_90,
        next_assessment_due_col.is_(None),
    )
    return {
        "never": never,
        "overdue": overdue,
        "week": week,
        "upcoming": upcoming,
        "covered": covered,
    }


def _operational_queue_filters(last_assessment_date_col, queue_conditions, *, today, now):
    recent_join_cutoff = today - timedelta(days=OPERATIONAL_FIRST_ASSESSMENT_WINDOW_DAYS)
    recent_checkin_cutoff = now - timedelta(days=OPERATIONAL_REASSESSMENT_CHECKIN_WINDOW_DAYS)

    first_assessment_operational = and_(
        queue_conditions["never"],
        Member.join_date.is_not(None),
        Member.join_date >= recent_join_cutoff,
    )
    reassessment_operational = and_(
        last_assessment_date_col.is_not(None),
        Member.last_checkin_at.is_not(None),
        Member.last_checkin_at >= recent_checkin_cutoff,
    )

    return {
        "never": first_assessment_operational,
        "overdue": and_(queue_conditions["overdue"], reassessment_operational),
        "week": and_(queue_conditions["week"], reassessment_operational),
        "upcoming": and_(queue_conditions["upcoming"], reassessment_operational),
        "covered": and_(queue_conditions["covered"], reassessment_operational),
    }


def _coverage_label(bucket: AssessmentMemberBucket) -> str:
    if bucket == "never":
        return "Nenhuma avaliacao registrada"
    if bucket == "overdue":
        return "Cobertura vencida"
    if bucket == "week":
        return "Avaliacao prevista nesta semana"
    if bucket == "upcoming":
        return "Planejamento futuro"
    return "Base coberta recentemente"


def _due_label(bucket: AssessmentMemberBucket, next_assessment_due, today):
    if bucket == "never":
        return "Primeira avaliacao pendente"
    if next_assessment_due:
        if next_assessment_due < today:
            return f"Atrasada desde {next_assessment_due.strftime('%d/%m/%Y')}"
        if next_assessment_due == today:
            return "Vence hoje"
        if next_assessment_due <= today + timedelta(days=7):
            return f"Janela ate {next_assessment_due.strftime('%d/%m/%Y')}"
        return f"Proxima janela em {next_assessment_due.strftime('%d/%m/%Y')}"
    if bucket == "overdue":
        return "Fora da janela ideal de 90 dias"
    return "Sem proxima janela definida"


def _serialize_queue_item(row, today) -> AssessmentQueueItemOut:
    bucket = getattr(row, "queue_bucket")
    next_assessment_due = getattr(row, "next_assessment_due")
    return AssessmentQueueItemOut(
        id=getattr(row, "id"),
        full_name=getattr(row, "full_name"),
        email=getattr(row, "email"),
        plan_name=getattr(row, "plan_name"),
        risk_level=getattr(row, "risk_level"),
        risk_score=int(getattr(row, "risk_score") or 0),
        last_checkin_at=getattr(row, "last_checkin_at"),
        next_assessment_due=next_assessment_due,
        queue_bucket=bucket,
        coverage_label=_coverage_label(bucket),
        due_label=_due_label(bucket, next_assessment_due, today),
        urgency_score=int(getattr(row, "urgency_score") or 0),
    )


def get_assessments_queue(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    bucket: AssessmentQueueBucket = "all",
    gym_id=None,
) -> PaginatedResponse[AssessmentQueueItemOut]:
    now = datetime.now(tz=timezone.utc)
    cutoff_90 = now - timedelta(days=90)
    today = now.date()
    next_7 = today + timedelta(days=7)
    resolved_gym_id = _resolve_gym_id(gym_id)

    latest_assessment_subquery = _latest_assessment_subquery()
    last_assessment_date_col = latest_assessment_subquery.c.last_assessment_date
    next_assessment_due_col = latest_assessment_subquery.c.next_assessment_due
    queue_conditions = _queue_conditions(
        last_assessment_date_col,
        next_assessment_due_col,
        cutoff_90=cutoff_90,
        today=today,
        next_7=next_7,
    )
    operational_filters = _operational_queue_filters(
        last_assessment_date_col,
        queue_conditions,
        today=today,
        now=now,
    )

    queue_bucket_expr = case(
        (queue_conditions["never"], literal("never")),
        (queue_conditions["overdue"], literal("overdue")),
        (queue_conditions["week"], literal("week")),
        (queue_conditions["upcoming"], literal("upcoming")),
        else_=literal("covered"),
    )
    bucket_priority_expr = case(
        (queue_conditions["never"], 0),
        (queue_conditions["overdue"], 1),
        (queue_conditions["week"], 2),
        (queue_conditions["upcoming"], 3),
        else_=4,
    )
    urgency_score_expr = func.coalesce(Member.risk_score, 0) + case(
        (queue_conditions["never"], 300),
        (queue_conditions["overdue"], 240),
        (queue_conditions["week"], 180),
        (queue_conditions["upcoming"], 120),
        else_=60,
    )

    filters = [Member.deleted_at.is_(None), Member.status == MemberStatus.ACTIVE]
    if resolved_gym_id is not None:
        filters.append(Member.gym_id == resolved_gym_id)
    if search:
        search_value = f"%{search.strip()}%"
        filters.append(
            or_(
                Member.full_name.ilike(search_value),
                Member.email.ilike(search_value),
                Member.plan_name.ilike(search_value),
            )
        )
    if bucket == "all":
        filters.append(or_(*operational_filters.values()))
    else:
        filters.append(operational_filters[bucket])

    base_stmt = (
        select(
            Member.id.label("id"),
            Member.full_name.label("full_name"),
            Member.email.label("email"),
            Member.plan_name.label("plan_name"),
            Member.risk_level.label("risk_level"),
            Member.risk_score.label("risk_score"),
            Member.last_checkin_at.label("last_checkin_at"),
            Member.updated_at.label("updated_at"),
            next_assessment_due_col.label("next_assessment_due"),
            queue_bucket_expr.label("queue_bucket"),
            urgency_score_expr.label("urgency_score"),
        )
        .select_from(Member)
        .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
        .where(and_(*filters))
    )

    total_stmt = _scoped_statement(
        select(func.count(Member.id))
        .select_from(Member)
        .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
        .where(and_(*filters)),
        resolved_gym_id,
    )
    total = int(db.scalar(total_stmt) or 0)

    offset = (page - 1) * page_size
    stmt = _scoped_statement(
        base_stmt
        .order_by(bucket_priority_expr, Member.risk_score.desc(), Member.updated_at.desc(), Member.full_name.asc())
        .offset(offset)
        .limit(page_size),
        resolved_gym_id,
    )
    rows = db.execute(stmt).all()
    items = [_serialize_queue_item(row, today) for row in rows]
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


def get_assessments_dashboard(db: Session) -> dict:
    now = datetime.now(tz=timezone.utc)
    cutoff_90 = now - timedelta(days=90)
    today = now.date()
    next_7 = today + timedelta(days=7)
    resolved_gym_id = _resolve_gym_id()

    base_member_filters = [Member.deleted_at.is_(None), Member.status == MemberStatus.ACTIVE]
    if resolved_gym_id is not None:
        base_member_filters.append(Member.gym_id == resolved_gym_id)

    total_members = db.scalar(
        _scoped_statement(select(func.count(Member.id)).where(and_(*base_member_filters)), resolved_gym_id)
    ) or 0
    assessed_last_90_days = db.scalar(
        _scoped_statement(
            select(func.count(distinct(Assessment.member_id)))
            .select_from(Assessment)
            .join(Member, Member.id == Assessment.member_id)
            .where(
                Assessment.deleted_at.is_(None),
                Assessment.assessment_date >= cutoff_90,
                *base_member_filters,
            ),
            resolved_gym_id,
        )
    ) or 0
    assessed_total = db.scalar(
        _scoped_statement(
            select(func.count(distinct(Assessment.member_id)))
            .select_from(Assessment)
            .join(Member, Member.id == Assessment.member_id)
            .where(
                Assessment.deleted_at.is_(None),
                *base_member_filters,
            ),
            resolved_gym_id,
        )
    ) or 0
    never_assessed = max(int(total_members) - int(assessed_total), 0)

    latest_assessment_subquery = _latest_assessment_subquery()
    queue_conditions = _queue_conditions(
        latest_assessment_subquery.c.last_assessment_date,
        latest_assessment_subquery.c.next_assessment_due,
        cutoff_90=cutoff_90,
        today=today,
        next_7=next_7,
    )
    operational_filters = _operational_queue_filters(
        latest_assessment_subquery.c.last_assessment_date,
        queue_conditions,
        today=today,
        now=now,
    )

    operational_overdue_assessments = db.scalar(
        _scoped_statement(
            select(func.count(Member.id))
            .select_from(Member)
            .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
            .where(and_(*base_member_filters, operational_filters["overdue"])),
            resolved_gym_id,
        )
    ) or 0
    operational_never_assessed = db.scalar(
        _scoped_statement(
            select(func.count(Member.id))
            .select_from(Member)
            .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
            .where(and_(*base_member_filters, operational_filters["never"])),
            resolved_gym_id,
        )
    ) or 0

    operational_upcoming_7_days = db.scalar(
        _scoped_statement(
            select(func.count(Member.id))
            .select_from(Member)
            .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
            .where(and_(*base_member_filters, operational_filters["week"])),
            resolved_gym_id,
        )
    ) or 0

    historical_never_assessed = max(int(never_assessed) - int(operational_never_assessed), 0)
    historical_overdue_assessments = db.scalar(
        _scoped_statement(
            select(func.count(Member.id))
            .select_from(Member)
            .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
            .where(and_(*base_member_filters, queue_conditions["overdue"], ~operational_filters["overdue"])),
            resolved_gym_id,
        )
    ) or 0
    historical_backlog_total = int(historical_never_assessed) + int(historical_overdue_assessments)

    member_ordering = (Member.risk_score.desc(), Member.updated_at.desc())

    total_members_items = list(
        db.scalars(
            _scoped_statement(
                select(Member)
                .where(and_(*base_member_filters))
                .order_by(*member_ordering)
                .limit(20),
                resolved_gym_id,
            )
        ).all()
    )

    assessed_members = list(
        db.scalars(
            _scoped_statement(
                select(Member)
                .join(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
                .where(
                    and_(
                        *base_member_filters,
                        latest_assessment_subquery.c.last_assessment_date >= cutoff_90,
                    )
                )
                .order_by(latest_assessment_subquery.c.last_assessment_date.desc(), *member_ordering)
                .limit(20),
                resolved_gym_id,
            )
        ).all()
    )

    overdue_members = list(
        db.scalars(
            _scoped_statement(
                select(Member)
                .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
                .where(and_(*base_member_filters, operational_filters["overdue"]))
                .order_by(*member_ordering)
                .limit(20),
                resolved_gym_id,
            )
        ).all()
    )

    never_assessed_members = list(
        db.scalars(
            _scoped_statement(
                select(Member)
                .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
                .where(and_(*base_member_filters, operational_filters["never"]))
                .order_by(*member_ordering)
                .limit(20),
                resolved_gym_id,
            )
        ).all()
    )

    upcoming_members = list(
        db.scalars(
            _scoped_statement(
                select(Member)
                .outerjoin(latest_assessment_subquery, latest_assessment_subquery.c.member_id == Member.id)
                .where(and_(*base_member_filters, operational_filters["week"]))
                .order_by(*member_ordering)
                .limit(20),
                resolved_gym_id,
            )
        ).all()
    )

    return {
        "total_members": int(total_members),
        "assessed_last_90_days": int(assessed_last_90_days),
        "overdue_assessments": int(operational_overdue_assessments),
        "never_assessed": int(operational_never_assessed),
        "upcoming_7_days": int(operational_upcoming_7_days),
        "historical_backlog_total": historical_backlog_total,
        "historical_never_assessed": int(historical_never_assessed),
        "historical_overdue_assessments": int(historical_overdue_assessments),
        "attention_now": get_assessments_queue(db, page=1, page_size=6, bucket="all", gym_id=resolved_gym_id).items,
        "total_members_items": total_members_items,
        "assessed_members": assessed_members,
        "overdue_members": overdue_members,
        "never_assessed_members": never_assessed_members,
        "upcoming_members": upcoming_members,
    }


def generate_ai_insights(db: Session, current: Assessment, *, commit: bool = True) -> None:
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

        if not settings.claude_api_key or claude_circuit_breaker.is_open():
            _apply_fallback_analysis(current, previous_assessments)
            db.add(current)
            if commit:
                db.commit()
            else:
                db.flush()
            return

        import anthropic
        from app.utils.claude import _parse_claude_json

        prompt = _build_comprehensive_assessment_prompt(current, previous_assessments, goals, constraints)
        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        try:
            response = client.messages.create(
                model=settings.claude_model,
                max_tokens=800,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            claude_circuit_breaker.record_success()
        except Exception:
            claude_circuit_breaker.record_failure()
            raise
        text = response.content[0].text.strip()
        parsed = _parse_claude_json(text)
        current.ai_analysis = (parsed.get("analysis") or "")[:2000]
        current.ai_recommendations = (parsed.get("recommendations") or "")[:2000]
        current.ai_risk_flags = (parsed.get("risk_flags") or "")[:2000]
        db.add(current)
        if commit:
            db.commit()
        else:
            db.flush()
    except Exception:
        logger.exception("Erro ao gerar insights de avaliacao - usando fallback")
        try:
            _apply_fallback_analysis(current, [])
            db.add(current)
            if commit:
                db.commit()
            else:
                db.flush()
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
