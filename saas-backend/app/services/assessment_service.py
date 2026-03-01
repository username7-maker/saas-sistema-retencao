import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import Member
from app.models.assessment import Assessment, MemberConstraints, MemberGoal, TrainingPlan
from app.services.assessment_analytics_service import generate_ai_insights


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
        generate_ai_insights(db, assessment)

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


def _safe_delta_value(previous: Decimal | None, current: Decimal | None) -> str:
    if previous is None or current is None:
        return "n/a"
    delta = current - previous
    return f"{delta:+.2f}"
