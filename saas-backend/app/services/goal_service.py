from datetime import date, datetime, time, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Goal, Member, MemberStatus, NPSResponse
from app.schemas.goal import GoalCreate, GoalProgressOut, GoalUpdate
from app.services.dashboard_service import get_churn_dashboard, get_executive_dashboard


def create_goal(db: Session, payload: GoalCreate) -> Goal:
    if payload.period_end < payload.period_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_end deve ser >= period_start")

    goal = Goal(**payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def list_goals(db: Session, *, active_only: bool = False) -> list[Goal]:
    stmt = select(Goal)
    if active_only:
        stmt = stmt.where(Goal.is_active.is_(True))
    return list(db.scalars(stmt.order_by(Goal.created_at.desc())).all())


def get_goal_or_404(db: Session, goal_id: UUID) -> Goal:
    goal = db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meta nao encontrada")
    return goal


def update_goal(db: Session, goal_id: UUID, payload: GoalUpdate) -> Goal:
    goal = get_goal_or_404(db, goal_id)
    data = payload.model_dump(exclude_unset=True)

    next_period_start = data.get("period_start", goal.period_start)
    next_period_end = data.get("period_end", goal.period_end)
    if next_period_end < next_period_start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_end deve ser >= period_start")

    for key, value in data.items():
        setattr(goal, key, value)

    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal_id: UUID) -> None:
    goal = get_goal_or_404(db, goal_id)
    db.delete(goal)
    db.commit()


def list_goal_progress(db: Session, *, active_only: bool = True) -> list[GoalProgressOut]:
    goals = list_goals(db, active_only=active_only)
    progress_items: list[GoalProgressOut] = []
    for goal in goals:
        current_value = _compute_metric_value(db, goal.metric_type, goal.period_start, goal.period_end)
        progress_pct = _progress_pct(goal.comparator, float(goal.target_value), current_value)
        status, status_message = _status(goal.comparator, float(goal.target_value), current_value, goal.alert_threshold_pct, progress_pct)
        progress_items.append(
            GoalProgressOut(
                goal=goal,
                current_value=round(current_value, 2),
                progress_pct=round(progress_pct, 2),
                status=status,
                status_message=status_message,
            )
        )
    return progress_items


def _compute_metric_value(db: Session, metric_type: str, period_start: date, period_end: date) -> float:
    start_dt = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(period_end, time.max, tzinfo=timezone.utc)

    if metric_type == "mrr":
        executive = get_executive_dashboard(db)
        return float(executive.mrr)

    if metric_type == "active_members":
        total = db.scalar(
            select(func.count()).select_from(Member).where(
                Member.deleted_at.is_(None),
                Member.status == MemberStatus.ACTIVE,
            )
        ) or 0
        return float(total)

    if metric_type == "new_members":
        total = db.scalar(
            select(func.count()).select_from(Member).where(
                Member.deleted_at.is_(None),
                Member.join_date >= period_start,
                Member.join_date <= period_end,
            )
        ) or 0
        return float(total)

    if metric_type == "churn_rate":
        churn_points = get_churn_dashboard(db, months=1)
        if not churn_points:
            return 0.0
        return float(churn_points[-1].churn_rate)

    if metric_type == "nps_avg":
        avg = db.scalar(
            select(func.coalesce(func.avg(NPSResponse.score), 0.0)).where(
                NPSResponse.response_date >= start_dt,
                NPSResponse.response_date <= end_dt,
            )
        ) or 0.0
        return float(avg)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Metric nao suportada: {metric_type}")


def _progress_pct(comparator: str, target_value: float, current_value: float) -> float:
    if target_value <= 0:
        return 0.0
    if comparator == "gte":
        return (current_value / target_value) * 100
    if current_value <= 0:
        return 100.0
    return (target_value / current_value) * 100


def _status(
    comparator: str,
    target_value: float,
    current_value: float,
    alert_threshold_pct: int,
    progress_pct: float,
) -> tuple[str, str]:
    if comparator == "gte":
        achieved = current_value >= target_value
    else:
        achieved = current_value <= target_value

    if achieved:
        return "achieved", "Meta atingida"
    if progress_pct < alert_threshold_pct:
        return "at_risk", "Meta em risco de nao ser batida"
    return "on_track", "Meta dentro do esperado"
