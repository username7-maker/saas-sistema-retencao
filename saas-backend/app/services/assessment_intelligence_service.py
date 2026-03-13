from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import Checkin, Member
from app.models.assessment import Assessment, MemberConstraints, MemberGoal
from app.services.assessment_action_engine import build_actions, sync_assessment_tasks
from app.services.assessment_ai_narrative_service import build_narratives
from app.services.assessment_benchmark_service import build_benchmark
from app.services.assessment_diagnosis_service import build_diagnosis
from app.services.assessment_forecast_service import build_forecast


def get_assessment_summary_360(db: Session, member_id: UUID) -> dict:
    member, latest_assessment, previous_assessment, constraints, goals = _load_member_assessment_context(db, member_id)
    goal_type = _extract_goal_type(latest_assessment, goals)
    target_frequency_per_week = _target_frequency_per_week(latest_assessment)
    recent_weekly_checkins, days_since_last_checkin = _checkin_metrics(db, member)

    forecast = build_forecast(
        member,
        latest_assessment,
        previous_assessment,
        goal_type=goal_type,
        target_frequency_per_week=target_frequency_per_week,
        recent_weekly_checkins=recent_weekly_checkins,
        days_since_last_checkin=days_since_last_checkin,
    )
    diagnosis = build_diagnosis(
        member,
        latest_assessment,
        previous_assessment,
        constraints,
        recent_weekly_checkins=recent_weekly_checkins,
        target_frequency_per_week=target_frequency_per_week,
        days_since_last_checkin=days_since_last_checkin,
        forecast=forecast,
    )
    benchmark = build_benchmark(
        db,
        member,
        latest_assessment,
        goal_type=goal_type,
        overall_score=forecast["overall_score"],
        gym_id=member.gym_id,
    )
    narratives = build_narratives(
        member,
        latest_assessment,
        diagnosis=diagnosis,
        forecast=forecast,
        benchmark=benchmark,
    )
    actions = build_actions(member, latest_assessment, diagnosis=diagnosis, forecast=forecast)

    next_best_action = actions[0]
    return {
        "member": member,
        "goal_type": goal_type,
        "latest_assessment": latest_assessment,
        "previous_assessment": previous_assessment,
        "constraints": constraints,
        "goals": goals,
        "days_since_last_checkin": days_since_last_checkin,
        "recent_weekly_checkins": recent_weekly_checkins,
        "target_frequency_per_week": target_frequency_per_week,
        "forecast": forecast,
        "diagnosis": diagnosis,
        "benchmark": benchmark,
        "narratives": narratives,
        "next_best_action": next_best_action,
        "actions": actions,
        "status": _status_label(forecast["probability_60d"], diagnosis["frustration_risk"]),
    }


def get_assessment_diagnosis(db: Session, member_id: UUID) -> dict:
    return get_assessment_summary_360(db, member_id)["diagnosis"]


def get_assessment_forecast(db: Session, member_id: UUID) -> dict:
    return get_assessment_summary_360(db, member_id)["forecast"]


def get_assessment_benchmark(db: Session, member_id: UUID) -> dict:
    return get_assessment_summary_360(db, member_id)["benchmark"]


def get_assessment_actions(db: Session, member_id: UUID) -> list[dict]:
    return get_assessment_summary_360(db, member_id)["actions"]


def sync_assessment_intelligence_tasks(db: Session, member_id: UUID) -> None:
    summary = get_assessment_summary_360(db, member_id)
    sync_assessment_tasks(
        db,
        summary["member"],
        summary["latest_assessment"],
        actions=summary["actions"],
    )


def _load_member_assessment_context(
    db: Session,
    member_id: UUID,
) -> tuple[Member, Assessment | None, Assessment | None, MemberConstraints | None, list[MemberGoal]]:
    member = db.scalar(select(Member).where(Member.id == member_id, Member.deleted_at.is_(None)))
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")

    assessments = list(
        db.scalars(
            select(Assessment)
            .where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
            .order_by(desc(Assessment.assessment_date))
            .limit(2)
        ).all()
    )
    latest_assessment = assessments[0] if assessments else None
    previous_assessment = assessments[1] if len(assessments) > 1 else None
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
    return member, latest_assessment, previous_assessment, constraints, goals


def _checkin_metrics(db: Session, member: Member) -> tuple[float, int | None]:
    now = datetime.now(tz=timezone.utc)
    recent_cutoff = now - timedelta(days=28)
    recent_total = db.scalar(
        select(func.count(Checkin.id)).where(Checkin.member_id == member.id, Checkin.checkin_at >= recent_cutoff)
    ) or 0
    recent_weekly_checkins = round(float(recent_total) / 4.0, 2)

    if member.last_checkin_at is None:
        return recent_weekly_checkins, None
    days_since = max(0, (now - member.last_checkin_at).days)
    return recent_weekly_checkins, days_since


def _extract_goal_type(latest_assessment: Assessment | None, goals: list[MemberGoal]) -> str:
    if latest_assessment and isinstance(latest_assessment.extra_data, dict):
        raw = str(
            latest_assessment.extra_data.get("goal_type")
            or latest_assessment.extra_data.get("main_goal")
            or ""
        ).strip().lower()
        if raw in {"fat_loss", "emagrecimento", "perda de gordura", "fat loss"}:
            return "fat_loss"
        if raw in {"muscle_gain", "hipertrofia", "ganho de massa", "muscle gain"}:
            return "muscle_gain"
        if raw in {"performance", "condicionamento"}:
            return "performance"

    for goal in goals:
        category = (goal.category or "").strip().lower()
        if category in {"fat_loss", "emagrecimento"}:
            return "fat_loss"
        if category in {"muscle_gain", "hipertrofia"}:
            return "muscle_gain"
        if category in {"performance", "condicionamento"}:
            return "performance"
    return "general"


def _target_frequency_per_week(latest_assessment: Assessment | None) -> int:
    if not latest_assessment or not isinstance(latest_assessment.extra_data, dict):
        return 3
    extra = latest_assessment.extra_data
    for key in ("target_frequency_per_week", "weekly_availability_days", "goal_frequency_per_week"):
        raw = extra.get(key)
        if raw is None:
            continue
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if 1 <= value <= 14:
            return value
    return 3


def _status_label(probability_60d: int, frustration_risk: int) -> str:
    if frustration_risk >= 70 or probability_60d < 35:
        return "critical"
    if frustration_risk >= 45 or probability_60d < 60:
        return "attention"
    return "on_track"
