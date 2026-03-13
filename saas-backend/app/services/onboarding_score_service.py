from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Checkin, Member, MemberStatus, NPSResponse, Task, TaskStatus
from app.models.assessment import Assessment

logger = logging.getLogger(__name__)

# Pesos dos fatores (somam 100)
WEIGHT_CHECKIN_FREQUENCY = 30
WEIGHT_FIRST_ASSESSMENT = 15
WEIGHT_TASK_COMPLETION = 20
WEIGHT_CONSISTENCY = 20
WEIGHT_NPS_RESPONSE = 15


def calculate_onboarding_score(db: Session, member: Member) -> dict:
    """Calcula score de onboarding 0-100 baseado em sinais comportamentais."""
    now = datetime.now(tz=timezone.utc)
    join_dt = datetime.combine(member.join_date, datetime.min.time(), tzinfo=timezone.utc)
    days_since_join = max(1, (now - join_dt).days)

    analysis_window = min(days_since_join, 30)
    window_start = join_dt
    window_end = join_dt + timedelta(days=analysis_window)

    # 1. Frequencia de check-ins (0-100)
    checkin_count = db.scalar(
        select(func.count(Checkin.id)).where(
            Checkin.member_id == member.id,
            Checkin.checkin_at >= window_start,
            Checkin.checkin_at <= window_end,
        )
    ) or 0
    expected_checkins = analysis_window * 3 / 7
    checkin_score = min(100, int((checkin_count / max(1, expected_checkins)) * 100))

    # 2. Fez avaliacao fisica (0 ou 100)
    has_assessment = db.scalar(
        select(func.count(Assessment.id)).where(
            Assessment.member_id == member.id,
            Assessment.deleted_at.is_(None),
        )
    ) or 0
    assessment_score = 100 if has_assessment > 0 else 0

    # 3. Tasks de onboarding completadas (0-100)
    total_onboarding_tasks = db.scalar(
        select(func.count(Task.id)).where(
            Task.member_id == member.id,
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "onboarding",
        )
    ) or 0
    completed_onboarding_tasks = db.scalar(
        select(func.count(Task.id)).where(
            Task.member_id == member.id,
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "onboarding",
            Task.status == TaskStatus.DONE,
        )
    ) or 0
    task_score = int((completed_onboarding_tasks / max(1, total_onboarding_tasks)) * 100)

    # 4. Consistencia de horario (0-100)
    consistency_score = _calculate_consistency(db, member.id, window_start, window_end)

    # 5. Respondeu NPS ou deu feedback (0 ou 100)
    has_nps = db.scalar(
        select(func.count(NPSResponse.id)).where(
            NPSResponse.member_id == member.id,
        )
    ) or 0
    nps_score = 100 if has_nps > 0 else 0

    # Score ponderado
    weighted_score = (
        checkin_score * WEIGHT_CHECKIN_FREQUENCY
        + assessment_score * WEIGHT_FIRST_ASSESSMENT
        + task_score * WEIGHT_TASK_COMPLETION
        + consistency_score * WEIGHT_CONSISTENCY
        + nps_score * WEIGHT_NPS_RESPONSE
    ) / 100

    final_score = max(0, min(100, int(round(weighted_score))))

    if days_since_join > 30:
        status = "completed"
    elif final_score < 30:
        status = "at_risk"
    else:
        status = "active"

    return {
        "score": final_score,
        "status": status,
        "factors": {
            "checkin_frequency": checkin_score,
            "first_assessment": assessment_score,
            "task_completion": task_score,
            "consistency": consistency_score,
            "nps_response": nps_score,
        },
        "days_since_join": days_since_join,
        "checkin_count": checkin_count,
        "completed_tasks": completed_onboarding_tasks,
        "total_tasks": total_onboarding_tasks,
    }


def _calculate_consistency(db: Session, member_id: UUID, start: datetime, end: datetime) -> int:
    """Calcula consistencia baseada na variancia de horarios de check-in."""
    hours = list(db.scalars(
        select(Checkin.hour_bucket).where(
            Checkin.member_id == member_id,
            Checkin.checkin_at >= start,
            Checkin.checkin_at <= end,
        )
    ).all())
    if len(hours) < 3:
        return 50  # Dados insuficientes, score neutro
    avg = sum(hours) / len(hours)
    variance = sum((h - avg) ** 2 for h in hours) / len(hours)
    # Variancia baixa = alta consistencia
    # Variancia de 0 = score 100, variancia >= 16 (4h) = score 0
    return max(0, min(100, int(100 - (variance / 16) * 100)))


def run_daily_onboarding_score(db: Session) -> dict:
    """Job diario que recalcula onboarding_score para membros nos primeiros 30 dias."""
    now = datetime.now(tz=timezone.utc)
    cutoff_date = (now - timedelta(days=30)).date()

    members = list(db.scalars(
        select(Member).where(
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.join_date >= cutoff_date,
        )
    ).all())

    updated = 0
    for member in members:
        try:
            result = calculate_onboarding_score(db, member)
            member.onboarding_score = result["score"]
            member.onboarding_status = result["status"]
            db.add(member)
            _process_d30_handoff(db, member)
            updated += 1
        except Exception:
            logger.exception("Falha ao calcular onboarding score para membro %s", member.id)

    db.commit()
    return {"members_processed": len(members), "updated": updated}


def _process_d30_handoff(db: Session, member: Member) -> None:
    """Transicao formal de onboarding para retencao no D30."""
    from app.models import Task, TaskPriority, TaskStatus

    now = datetime.now(tz=timezone.utc)
    join_days = (now.date() - member.join_date).days

    if join_days < 30 or member.onboarding_status == "completed":
        return

    member.onboarding_status = "completed"
    member.retention_stage = "monitoring"

    existing = db.scalar(
        select(Task).where(
            Task.member_id == member.id,
            Task.title.ilike("%Handoff D30%"),
            Task.deleted_at.is_(None),
        )
    )
    if not existing:
        task = Task(
            gym_id=member.gym_id,
            member_id=member.id,
            assigned_to_user_id=member.assigned_user_id,
            title=f"Handoff D30 - {member.full_name}",
            description=(
                f"Aluno completou 30 dias. Score de onboarding: {member.onboarding_score}. "
                "Revisar experiencia e transferir para acompanhamento de retencao."
            ),
            priority=TaskPriority.HIGH if member.onboarding_score < 50 else TaskPriority.MEDIUM,
            status=TaskStatus.TODO,
            kanban_column="todo",
            due_date=now + timedelta(days=2),
            extra_data={"source": "onboarding_handoff", "onboarding_score": member.onboarding_score},
        )
        db.add(task)

    db.add(member)
