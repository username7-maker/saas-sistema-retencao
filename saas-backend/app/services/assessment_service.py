import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Member
from app.models.assessment import Assessment, MemberConstraints, MemberGoal, TrainingPlan


logger = logging.getLogger(__name__)


def get_member_or_404(db: Session, member_id: UUID) -> Member:
    member = db.scalar(select(Member).where(Member.id == member_id, Member.deleted_at.is_(None)))
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")
    return member


def create_assessment(db: Session, member_id: UUID, evaluator_id: UUID, data: dict) -> Assessment:
    get_member_or_404(db, member_id)
    previous_count = db.scalar(
        select(func.count(Assessment.id)).where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
    ) or 0

    assessment_date = _normalize_datetime(data.get("assessment_date"))
    height_cm = _to_decimal(data.get("height_cm"))
    weight_kg = _to_decimal(data.get("weight_kg"))
    bmi_value = _calculate_bmi(height_cm, weight_kg)
    if bmi_value is None:
        bmi_value = _to_decimal(data.get("bmi"))

    assessment = Assessment(
        member_id=member_id,
        evaluator_id=evaluator_id,
        assessment_number=int(previous_count) + 1,
        assessment_date=assessment_date,
        next_assessment_due=(assessment_date + timedelta(days=90)).date(),
        height_cm=height_cm,
        weight_kg=weight_kg,
        bmi=bmi_value,
        body_fat_pct=_to_decimal(data.get("body_fat_pct")),
        lean_mass_kg=_to_decimal(data.get("lean_mass_kg")),
        waist_cm=_to_decimal(data.get("waist_cm")),
        hip_cm=_to_decimal(data.get("hip_cm")),
        chest_cm=_to_decimal(data.get("chest_cm")),
        arm_cm=_to_decimal(data.get("arm_cm")),
        thigh_cm=_to_decimal(data.get("thigh_cm")),
        resting_hr=data.get("resting_hr"),
        blood_pressure_systolic=data.get("blood_pressure_systolic"),
        blood_pressure_diastolic=data.get("blood_pressure_diastolic"),
        vo2_estimated=_to_decimal(data.get("vo2_estimated")),
        strength_score=data.get("strength_score"),
        flexibility_score=data.get("flexibility_score"),
        cardio_score=data.get("cardio_score"),
        observations=data.get("observations"),
        extra_data=data.get("extra_data") or {},
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    if previous_count > 0:
        _generate_ai_insights(db, assessment)

    return assessment


def list_assessments(db: Session, member_id: UUID) -> list[Assessment]:
    get_member_or_404(db, member_id)
    return list(
        db.scalars(
            select(Assessment)
            .where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
            .order_by(desc(Assessment.assessment_date))
        ).all()
    )


def get_assessment(db: Session, assessment_id: UUID) -> Assessment:
    assessment = db.scalar(select(Assessment).where(Assessment.id == assessment_id, Assessment.deleted_at.is_(None)))
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avaliacao nao encontrada")
    return assessment


def get_member_profile_360(db: Session, member_id: UUID) -> dict:
    member = get_member_or_404(db, member_id)

    latest_assessment = db.scalar(
        select(Assessment)
        .where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
        .order_by(desc(Assessment.assessment_date))
        .limit(1)
    )
    constraints = db.scalar(
        select(MemberConstraints)
        .where(MemberConstraints.member_id == member_id, MemberConstraints.deleted_at.is_(None))
        .order_by(desc(MemberConstraints.created_at))
        .limit(1)
    )
    goals = list(
        db.scalars(
            select(MemberGoal)
            .where(MemberGoal.member_id == member_id, MemberGoal.deleted_at.is_(None))
            .order_by(MemberGoal.achieved.asc(), MemberGoal.target_date.asc().nullslast(), MemberGoal.created_at.desc())
        ).all()
    )
    active_training_plan = db.scalar(
        select(TrainingPlan)
        .where(
            TrainingPlan.member_id == member_id,
            TrainingPlan.deleted_at.is_(None),
            TrainingPlan.is_active.is_(True),
        )
        .order_by(desc(TrainingPlan.start_date))
        .limit(1)
    )

    return {
        "member": member,
        "latest_assessment": latest_assessment,
        "constraints": constraints,
        "goals": goals,
        "active_training_plan": active_training_plan,
        "insight_summary": latest_assessment.ai_analysis if latest_assessment else None,
    }


def get_evolution_data(db: Session, member_id: UUID) -> dict:
    get_member_or_404(db, member_id)
    assessments = list(
        db.scalars(
            select(Assessment)
            .where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
            .order_by(Assessment.assessment_date.asc())
        ).all()
    )

    labels = [item.assessment_date.date().isoformat() for item in assessments]
    weight = [_decimal_to_float(item.weight_kg) for item in assessments]
    body_fat = [_decimal_to_float(item.body_fat_pct) for item in assessments]
    bmi = [_decimal_to_float(item.bmi) for item in assessments]
    strength = [item.strength_score for item in assessments]
    flexibility = [item.flexibility_score for item in assessments]
    cardio = [item.cardio_score for item in assessments]

    return {
        "labels": labels,
        "weight": weight,
        "body_fat": body_fat,
        "bmi": bmi,
        "strength": strength,
        "flexibility": flexibility,
        "cardio": cardio,
        "deltas": {
            "weight": _calculate_delta(weight),
            "body_fat": _calculate_delta(body_fat),
            "bmi": _calculate_delta(bmi),
            "strength": _calculate_delta(strength),
            "flexibility": _calculate_delta(flexibility),
            "cardio": _calculate_delta(cardio),
        },
    }


def upsert_constraints(db: Session, member_id: UUID, data: dict) -> MemberConstraints:
    get_member_or_404(db, member_id)

    current = db.scalar(
        select(MemberConstraints)
        .where(MemberConstraints.member_id == member_id)
        .order_by(desc(MemberConstraints.created_at))
        .limit(1)
    )
    if not current:
        current = MemberConstraints(member_id=member_id)
    elif current.deleted_at is not None:
        current.deleted_at = None

    for field in (
        "medical_conditions",
        "injuries",
        "medications",
        "contraindications",
        "preferred_training_times",
        "notes",
    ):
        if field in data:
            setattr(current, field, data.get(field))
    if "restrictions" in data:
        current.restrictions = data.get("restrictions") or {}

    db.add(current)
    db.commit()
    db.refresh(current)
    return current


def create_goal(db: Session, member_id: UUID, data: dict) -> MemberGoal:
    get_member_or_404(db, member_id)
    assessment_id = data.get("assessment_id")
    if assessment_id:
        _validate_assessment_belongs_to_member(db, member_id, assessment_id)

    target_value = _to_decimal(data.get("target_value"))
    current_value = _to_decimal(data.get("current_value")) or Decimal("0")
    progress_pct = int(data.get("progress_pct") or _calculate_progress_pct(current_value, target_value))
    achieved = bool(data.get("achieved"))
    achieved_at = _normalize_datetime(data.get("achieved_at")) if achieved else None
    if achieved and progress_pct < 100:
        progress_pct = 100

    goal = MemberGoal(
        member_id=member_id,
        assessment_id=assessment_id,
        title=data.get("title"),
        description=data.get("description"),
        category=data.get("category") or "general",
        target_value=target_value,
        current_value=current_value,
        unit=data.get("unit"),
        target_date=data.get("target_date"),
        status=data.get("status") or "active",
        progress_pct=max(0, min(progress_pct, 100)),
        achieved=achieved,
        achieved_at=achieved_at,
        notes=data.get("notes"),
        extra_data=data.get("extra_data") or {},
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def list_goals(db: Session, member_id: UUID) -> list[MemberGoal]:
    get_member_or_404(db, member_id)
    return list(
        db.scalars(
            select(MemberGoal)
            .where(MemberGoal.member_id == member_id, MemberGoal.deleted_at.is_(None))
            .order_by(MemberGoal.achieved.asc(), MemberGoal.target_date.asc().nullslast(), MemberGoal.created_at.desc())
        ).all()
    )


def create_training_plan(db: Session, member_id: UUID, created_by: UUID, data: dict) -> TrainingPlan:
    get_member_or_404(db, member_id)
    assessment_id = data.get("assessment_id")
    if assessment_id:
        _validate_assessment_belongs_to_member(db, member_id, assessment_id)

    make_active = bool(data.get("is_active", True))
    if make_active:
        active_plans = list(
            db.scalars(
                select(TrainingPlan).where(
                    TrainingPlan.member_id == member_id,
                    TrainingPlan.deleted_at.is_(None),
                    TrainingPlan.is_active.is_(True),
                )
            ).all()
        )
        for plan in active_plans:
            plan.is_active = False
            db.add(plan)

    training_plan = TrainingPlan(
        member_id=member_id,
        assessment_id=assessment_id,
        created_by_user_id=created_by,
        name=data.get("name"),
        objective=data.get("objective"),
        sessions_per_week=data.get("sessions_per_week") or 3,
        split_type=data.get("split_type"),
        start_date=data.get("start_date") or date.today(),
        end_date=data.get("end_date"),
        is_active=make_active,
        plan_data=data.get("plan_data") or {},
        notes=data.get("notes"),
        extra_data=data.get("extra_data") or {},
    )
    db.add(training_plan)
    db.commit()
    db.refresh(training_plan)
    return training_plan


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


def _generate_ai_insights(db: Session, current: Assessment) -> None:
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


def _validate_assessment_belongs_to_member(db: Session, member_id: UUID, assessment_id: UUID) -> None:
    assessment = db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.member_id == member_id,
            Assessment.deleted_at.is_(None),
        )
    )
    if not assessment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Avaliacao informada nao pertence ao membro")


def _normalize_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(tz=timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
    else:
        parsed = value
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _to_decimal(value: float | int | str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _calculate_bmi(height_cm: Decimal | None, weight_kg: Decimal | None) -> Decimal | None:
    if not height_cm or not weight_kg:
        return None
    height_m = float(height_cm) / 100
    if height_m <= 0:
        return None
    return Decimal(str(round(float(weight_kg) / (height_m**2), 2)))


def _calculate_progress_pct(current_value: Decimal | None, target_value: Decimal | None) -> int:
    if not target_value or target_value <= 0:
        return 0
    if current_value is None:
        return 0
    pct = (float(current_value) / float(target_value)) * 100
    return int(max(0, min(100, round(pct))))


def _calculate_delta(series: list[float | int | None]) -> float | int | None:
    valid_values = [value for value in series if value is not None]
    if len(valid_values) < 2:
        return None
    first = valid_values[0]
    last = valid_values[-1]
    if isinstance(first, int) and isinstance(last, int):
        return last - first
    return round(float(last) - float(first), 2)


def _safe_delta_value(before: Decimal | int | None, after: Decimal | int | None) -> str:
    if before is None or after is None:
        return "n/a"
    delta = float(after) - float(before)
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.2f}"
