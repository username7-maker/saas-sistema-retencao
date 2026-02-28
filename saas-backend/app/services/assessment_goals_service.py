from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.assessment import MemberConstraints, MemberGoal, TrainingPlan
from app.services.assessment_service import (
    _calculate_progress_pct,
    _normalize_datetime,
    _to_decimal,
    _validate_assessment_belongs_to_member,
    get_member_or_404,
)


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
