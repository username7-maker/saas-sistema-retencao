import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Checkin, Member
from app.models.assessment import Assessment, MemberConstraints, MemberGoal, TrainingPlan
from app.services.assessment_analytics_service import generate_ai_insights
from app.services.assessment_intelligence_service import sync_assessment_intelligence_tasks


logger = logging.getLogger(__name__)

_DEFAULT_ASSESSMENT_DUE_DAYS = 90
_ASSESSMENT_QUEUE_RESOLUTION_KEYS = (
    "assessment_queue_resolution",
    "assessment_queue_resolution_note",
    "assessment_queue_resolution_at",
    "assessment_queue_resolution_by",
)
_ASSESSMENT_DUE_BY_PLAN_KEYWORD = {
    "mensal": 30,
    "trimestral": 90,
    "semestral": 90,
    "anual": 120,
}


def _safe(fn, default=None):
    """Execute fn() returning default on any error, logging the failure."""
    try:
        return fn()
    except Exception:
        logger.exception("Falha parcial em Profile 360")
        return default


def get_member_or_404(db: Session, member_id: UUID, gym_id: UUID | None = None) -> Member:
    stmt = select(Member).where(Member.id == member_id, Member.deleted_at.is_(None))
    if gym_id is not None:
        stmt = stmt.where(Member.gym_id == gym_id)
    member = db.scalar(stmt)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")
    return member


def _calculate_next_assessment_due(db: Session, member_id: UUID, assessment_date: datetime) -> date:
    """Calcula next_assessment_due baseado no tipo de plano do membro."""
    member = db.scalar(select(Member).where(Member.id == member_id))
    if not member:
        return (assessment_date + timedelta(days=_DEFAULT_ASSESSMENT_DUE_DAYS)).date()

    plan = (member.plan_name or "").lower()
    due_days = next(
        (days for keyword, days in _ASSESSMENT_DUE_BY_PLAN_KEYWORD.items() if keyword in plan),
        _DEFAULT_ASSESSMENT_DUE_DAYS,
    )
    return (assessment_date + timedelta(days=due_days)).date()


def create_assessment(
    db: Session,
    member_id: UUID,
    evaluator_id: UUID,
    data: dict,
    *,
    commit: bool = True,
) -> Assessment:
    member = get_member_or_404(db, member_id)
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
        next_assessment_due=_calculate_next_assessment_due(db, member_id, assessment_date),
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
    if _clear_assessment_queue_resolution(member):
        db.add(member)
    db.add(assessment)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(assessment)

    generate_ai_insights(db, assessment, commit=False)
    sync_assessment_intelligence_tasks(db, member_id, commit=False)

    if commit:
        db.commit()
    else:
        db.flush()

    return assessment


def update_assessment_queue_resolution(
    db: Session,
    member_id: UUID,
    *,
    resolution_status: str,
    note: str | None = None,
    resolved_by_user_id: UUID | None = None,
    gym_id: UUID | None = None,
    commit: bool = True,
) -> Member:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    extra_data = dict(member.extra_data or {})

    if resolution_status == "active":
        changed = _clear_assessment_queue_resolution(member, extra_data=extra_data)
    else:
        changed = _apply_assessment_queue_resolution(
            member,
            resolution_status=resolution_status,
            note=note,
            resolved_by_user_id=resolved_by_user_id,
            extra_data=extra_data,
        )

    if changed:
        db.add(member)
    invalidate_dashboard_cache("members", gym_id=member.gym_id)
    if commit:
        db.commit()
        db.refresh(member)
    return member


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

    latest_assessment = _safe(lambda: db.scalar(
        select(Assessment)
        .where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
        .order_by(desc(Assessment.assessment_date))
        .limit(1)
    ))
    constraints = _safe(lambda: db.scalar(
        select(MemberConstraints)
        .where(MemberConstraints.member_id == member_id, MemberConstraints.deleted_at.is_(None))
        .order_by(desc(MemberConstraints.created_at))
        .limit(1)
    ))
    goals = _safe(lambda: list(
        db.scalars(
            select(MemberGoal)
            .where(MemberGoal.member_id == member_id, MemberGoal.deleted_at.is_(None))
            .order_by(MemberGoal.achieved.asc(), MemberGoal.target_date.asc().nullslast(), MemberGoal.created_at.desc())
        ).all()
    ), default=[])
    active_training_plan = _safe(lambda: db.scalar(
        select(TrainingPlan)
        .where(
            TrainingPlan.member_id == member_id,
            TrainingPlan.deleted_at.is_(None),
            TrainingPlan.is_active.is_(True),
        )
        .order_by(desc(TrainingPlan.start_date))
        .limit(1)
    ))

    return {
        "member": member,
        "latest_assessment": latest_assessment,
        "constraints": constraints,
        "goals": goals if goals is not None else [],
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
    lean_mass = [_decimal_to_float(item.lean_mass_kg) for item in assessments]
    bmi = [_decimal_to_float(item.bmi) for item in assessments]
    strength = [item.strength_score for item in assessments]
    flexibility = [item.flexibility_score for item in assessments]
    cardio = [item.cardio_score for item in assessments]
    main_lift_load = [_extract_main_lift_load(item) for item in assessments]

    checkin_labels = _last_month_labels(6)
    checkins_per_month = [0 for _ in checkin_labels]
    if checkin_labels:
        first_label = checkin_labels[0]
        first_month_start = datetime.strptime(f"{first_label}-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
        checkin_dates = db.scalars(
            select(Checkin.checkin_at).where(
                Checkin.member_id == member_id,
                Checkin.checkin_at >= first_month_start,
            )
        ).all()
        bucket_index = {label: index for index, label in enumerate(checkin_labels)}
        for checkin_at in checkin_dates:
            label = checkin_at.strftime("%Y-%m")
            idx = bucket_index.get(label)
            if idx is not None:
                checkins_per_month[idx] += 1

    return {
        "labels": labels,
        "weight": weight,
        "body_fat": body_fat,
        "lean_mass": lean_mass,
        "bmi": bmi,
        "strength": strength,
        "flexibility": flexibility,
        "cardio": cardio,
        "checkins_labels": checkin_labels,
        "checkins_per_month": checkins_per_month,
        "main_lift_load": main_lift_load,
        "main_lift_label": "Carga principal",
        "deltas": {
            "weight": _calculate_delta(weight),
            "body_fat": _calculate_delta(body_fat),
            "lean_mass": _calculate_delta(lean_mass),
            "bmi": _calculate_delta(bmi),
            "strength": _calculate_delta(strength),
            "flexibility": _calculate_delta(flexibility),
            "cardio": _calculate_delta(cardio),
            "main_lift_load": _calculate_delta(main_lift_load),
        },
    }


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


def _apply_assessment_queue_resolution(
    member: Member,
    *,
    resolution_status: str,
    note: str | None,
    resolved_by_user_id: UUID | None,
    extra_data: dict | None = None,
) -> bool:
    working_extra = extra_data if extra_data is not None else dict(member.extra_data or {})
    normalized_status = str(resolution_status or "").strip().lower()
    if normalized_status not in {"scheduled", "dismissed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status de fila de avaliacao invalido")

    cleaned_note = (note or "").strip() or None
    before_snapshot = dict(working_extra)
    working_extra["assessment_queue_resolution"] = normalized_status
    if cleaned_note:
        working_extra["assessment_queue_resolution_note"] = cleaned_note[:280]
    else:
        working_extra.pop("assessment_queue_resolution_note", None)
    working_extra["assessment_queue_resolution_at"] = datetime.now(tz=timezone.utc).isoformat()
    if resolved_by_user_id:
        working_extra["assessment_queue_resolution_by"] = str(resolved_by_user_id)
    else:
        working_extra.pop("assessment_queue_resolution_by", None)

    if working_extra == before_snapshot:
        return False
    member.extra_data = working_extra
    return True


def _clear_assessment_queue_resolution(member: Member, *, extra_data: dict | None = None) -> bool:
    working_extra = extra_data if extra_data is not None else dict(member.extra_data or {})
    before_snapshot = dict(working_extra)
    for key in _ASSESSMENT_QUEUE_RESOLUTION_KEYS:
        working_extra.pop(key, None)
    if working_extra == before_snapshot:
        return False
    member.extra_data = working_extra
    return True


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


def _safe_delta_value(previous: Decimal | None, current: Decimal | None) -> str:
    if previous is None or current is None:
        return "n/a"
    delta = current - previous
    return f"{delta:+.2f}"


def _last_month_labels(months: int) -> list[str]:
    if months <= 0:
        return []
    base = date.today().replace(day=1)
    labels: list[str] = []
    for index in range(months - 1, -1, -1):
        current = _subtract_months(base, index)
        labels.append(current.strftime("%Y-%m"))
    return labels


def _subtract_months(base: date, months_back: int) -> date:
    year = base.year
    month = base.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _extract_main_lift_load(assessment: Assessment) -> float | None:
    extra = assessment.extra_data if isinstance(assessment.extra_data, dict) else {}
    candidate_keys = (
        "main_lift_load",
        "principal_exercise_load",
        "carga_principal",
        "leg_press_load",
        "supino_load",
    )
    for key in candidate_keys:
        raw = extra.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue

    if assessment.strength_score is not None:
        return float(assessment.strength_score)
    return None

