from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Checkin, Member, MemberStatus, Task, TaskStatus
from app.models.assessment import Assessment
from app.schemas.onboarding import (
    OnboardingCockpitMemberOut,
    OnboardingCockpitMetricsOut,
    OnboardingCockpitOut,
    OnboardingCockpitSummaryOut,
    OnboardingCockpitTaskStageOut,
)
from app.services.onboarding_service import ONBOARDING_PLAYBOOK


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _task_extra(task: Task) -> dict:
    return dict(task.extra_data or {}) if isinstance(task.extra_data, dict) else {}


def _day_offset_from_task(task: Task) -> int | None:
    value = _task_extra(task).get("day_offset")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _phase_for_days(days_since_join: int) -> tuple[str, int | None]:
    if days_since_join <= 1:
        return "Entrada e cadastro", 0
    if days_since_join <= 3:
        return "Primeiros treinos", 3
    if days_since_join <= 7:
        return "Primeira semana", 7
    if days_since_join <= 15:
        return "Criar rotina", 15
    return "Fechamento D30", 30


def _next_step_for_days(days_since_join: int) -> tuple[str, str]:
    future_or_current = [step for step in ONBOARDING_PLAYBOOK if step.days >= days_since_join]
    step = future_or_current[0] if future_or_current else ONBOARDING_PLAYBOOK[-1]
    owner_role = "coach" if step.days in {1, 7, 15} else "reception"
    return step.title, owner_role


def _score_bucket(score: int) -> str:
    if score >= 70:
        return "engaged"
    if score >= 40:
        return "attention"
    return "critical"


def _load_onboarding_members(db: Session, *, gym_id: UUID, now: datetime) -> list[Member]:
    lower_bound = (now - timedelta(days=37)).date()
    return list(
        db.scalars(
            select(Member).where(
                Member.gym_id == gym_id,
                Member.deleted_at.is_(None),
                Member.status == MemberStatus.ACTIVE,
                Member.join_date >= lower_bound,
                Member.join_date <= now.date(),
                Member.onboarding_status.in_(("active", "at_risk")),
            )
        ).all()
    )


def _load_onboarding_tasks(db: Session, *, gym_id: UUID, member_ids: list[UUID]) -> list[Task]:
    if not member_ids:
        return []
    return list(
        db.scalars(
            select(Task).where(
                Task.gym_id == gym_id,
                Task.member_id.in_(member_ids),
                Task.deleted_at.is_(None),
                Task.extra_data["source"].astext == "onboarding",
                func.coalesce(Task.extra_data["operational_archive"]["archived_at"].astext, "") == "",
            )
        ).all()
    )


def _checkin_counts_by_member(db: Session, *, gym_id: UUID, member_ids: list[UUID], now: datetime) -> dict[UUID, int]:
    if not member_ids:
        return {}
    rows = db.execute(
        select(Checkin.member_id, func.count(Checkin.id))
        .where(
            Checkin.gym_id == gym_id,
            Checkin.member_id.in_(member_ids),
            Checkin.checkin_at >= now - timedelta(days=7),
            Checkin.checkin_at <= now,
        )
        .group_by(Checkin.member_id)
    ).all()
    return {member_id: int(count or 0) for member_id, count in rows}


def _assessment_member_ids(db: Session, *, member_ids: list[UUID], now: datetime) -> set[UUID]:
    if not member_ids:
        return set()
    earliest_join_window = now - timedelta(days=37)
    rows = db.execute(
        select(Assessment.member_id)
        .where(
            Assessment.member_id.in_(member_ids),
            Assessment.deleted_at.is_(None),
            Assessment.assessment_date >= earliest_join_window,
            Assessment.assessment_date <= now,
        )
        .group_by(Assessment.member_id)
    ).all()
    return {member_id for (member_id,) in rows}


def build_onboarding_cockpit(db: Session, *, gym_id: UUID) -> OnboardingCockpitOut:
    now = _now()
    members = _load_onboarding_members(db, gym_id=gym_id, now=now)
    member_ids = [member.id for member in members]
    tasks = _load_onboarding_tasks(db, gym_id=gym_id, member_ids=member_ids)
    checkins_7d = _checkin_counts_by_member(db, gym_id=gym_id, member_ids=member_ids, now=now)
    assessed_member_ids = _assessment_member_ids(db, member_ids=member_ids, now=now)

    task_stage_map: dict[int, list[Task]] = {step.days: [] for step in ONBOARDING_PLAYBOOK}
    for task in tasks:
        offset = _day_offset_from_task(task)
        if offset in task_stage_map:
            task_stage_map[offset].append(task)

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    open_tasks = [task for task in tasks if task.status not in {TaskStatus.DONE, TaskStatus.CANCELLED}]
    overdue_total = sum(1 for task in open_tasks if task.due_date and task.due_date < today_start)
    due_today_total = sum(1 for task in open_tasks if task.due_date and today_start <= task.due_date < tomorrow_start)
    unassigned_total = sum(1 for task in open_tasks if task.assigned_to_user_id is None)

    member_payloads: list[OnboardingCockpitMemberOut] = []
    score_distribution = {"engaged": 0, "attention": 0, "critical": 0}
    for member in members:
        days_since_join = max(0, (now.date() - member.join_date).days)
        score = int(member.onboarding_score or 0)
        bucket = _score_bucket(score)
        score_distribution[bucket] += 1
        phase_label, current_offset = _phase_for_days(days_since_join)
        next_action, owner_role = _next_step_for_days(days_since_join)
        member_payloads.append(
            OnboardingCockpitMemberOut(
                member_id=member.id,
                full_name=member.full_name,
                plan_name=member.plan_name,
                preferred_shift=member.preferred_shift,
                days_since_join=days_since_join,
                score=score,
                status=str(member.onboarding_status or "active"),
                phase_label=phase_label,
                next_action=next_action,
                responsible_role=owner_role,
                current_stage_offset=current_offset,
            )
        )

    first_week_members = [member for member in members if 0 <= (now.date() - member.join_date).days <= 7]
    two_checkins_total = sum(1 for member in first_week_members if checkins_7d.get(member.id, 0) >= 2)
    first_week_two_checkins_rate = (
        round((two_checkins_total / len(first_week_members)) * 100, 1) if first_week_members else None
    )
    first_assessment_rate = round((len(assessed_member_ids) / len(members)) * 100, 1) if members else None

    return OnboardingCockpitOut(
        summary=OnboardingCockpitSummaryOut(
            active_total=len(members),
            at_risk_total=sum(1 for member in members if str(member.onboarding_status or "") == "at_risk"),
            critical_total=score_distribution["critical"],
            due_today_total=due_today_total,
            overdue_total=overdue_total,
            unassigned_total=unassigned_total,
        ),
        members=sorted(member_payloads, key=lambda item: (item.score, -item.days_since_join)),
        critical_members=[item for item in member_payloads if item.score < 40],
        tasks_by_stage=[
            OnboardingCockpitTaskStageOut(
                stage_key=f"d{step.days}",
                label=f"D{step.days}",
                day_offset=step.days,
                total=len(task_stage_map.get(step.days, [])),
                due_now_total=sum(
                    1
                    for task in task_stage_map.get(step.days, [])
                    if task.status not in {TaskStatus.DONE, TaskStatus.CANCELLED}
                    and task.due_date is not None
                    and task.due_date <= now
                ),
                future_total=sum(
                    1
                    for task in task_stage_map.get(step.days, [])
                    if task.status not in {TaskStatus.DONE, TaskStatus.CANCELLED}
                    and task.due_date is not None
                    and task.due_date > now
                ),
            )
            for step in ONBOARDING_PLAYBOOK
        ],
        score_distribution=score_distribution,
        metrics=OnboardingCockpitMetricsOut(
            first_week_two_checkins_rate=first_week_two_checkins_rate,
            first_assessment_rate=first_assessment_rate,
            d30_ready_total=sum(1 for member in members if (now.date() - member.join_date).days >= 30),
            generated_at=now,
        ),
        generated_at=now,
    )
