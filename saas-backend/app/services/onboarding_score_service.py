from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import AuditLog, AssessmentAppointment, Checkin, Member, MemberStatus, MessageLog, NPSResponse, Task, TaskStatus
from app.models.assessment import Assessment
from app.models.body_composition import BodyCompositionEvaluation
from app.services.whatsapp_service import normalize_phone

logger = logging.getLogger(__name__)

# Pesos dos fatores (somam 100)
WEIGHT_CHECKIN_FREQUENCY = 30
WEIGHT_FIRST_ASSESSMENT = 15
WEIGHT_TASK_COMPLETION = 20
WEIGHT_CONSISTENCY = 20
WEIGHT_MEMBER_RESPONSE = 15


def calculate_onboarding_score(db: Session, member: Member) -> dict:
    """Calcula score de onboarding 0-100 baseado em sinais comportamentais."""
    now = datetime.now(tz=timezone.utc)
    join_dt = datetime.combine(member.join_date, datetime.min.time(), tzinfo=timezone.utc)
    days_since_join = max(0, (now - join_dt).days)

    analysis_window = max(1, min(days_since_join, 30))
    window_start = join_dt
    window_end = min(join_dt + timedelta(days=30), now)

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
    has_formal_assessment = db.scalar(
        select(func.count(Assessment.id)).where(
            Assessment.member_id == member.id,
            Assessment.deleted_at.is_(None),
            Assessment.assessment_date >= window_start,
            Assessment.assessment_date <= window_end,
        )
    ) or 0
    has_body_composition = db.scalar(
        select(func.count(BodyCompositionEvaluation.id)).where(
            BodyCompositionEvaluation.member_id == member.id,
            BodyCompositionEvaluation.evaluation_date >= window_start.date(),
            BodyCompositionEvaluation.evaluation_date <= window_end.date(),
        )
    ) or 0
    has_historical_appointment = db.scalar(
        select(func.count(AssessmentAppointment.id)).where(
            AssessmentAppointment.member_id == member.id,
            AssessmentAppointment.deleted_at.is_(None),
            AssessmentAppointment.status.in_(("attended", "completed")),
            AssessmentAppointment.scheduled_at >= window_start,
            AssessmentAppointment.scheduled_at <= window_end,
        )
    ) or 0
    assessment_score = 100 if has_formal_assessment > 0 or has_body_composition > 0 or has_historical_appointment > 0 else 0

    # 3. Tasks de onboarding completadas (0-100)
    # Conta apenas etapas esperadas ate hoje; D7/D15/D30 futuras nao devem derrubar aluno D1.
    due_task_filter = or_(Task.due_date.is_(None), Task.due_date <= now)
    total_onboarding_tasks = db.scalar(
        select(func.count(Task.id)).where(
            Task.member_id == member.id,
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "onboarding",
            func.coalesce(Task.extra_data["operational_archive"]["archived_at"].astext, "") == "",
            due_task_filter,
        )
    ) or 0
    completed_onboarding_tasks = db.scalar(
        select(func.count(Task.id)).where(
            Task.member_id == member.id,
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "onboarding",
            func.coalesce(Task.extra_data["operational_archive"]["archived_at"].astext, "") == "",
            due_task_filter,
            Task.status == TaskStatus.DONE,
        )
    ) or 0
    total_journey_tasks = db.scalar(
        select(func.count(Task.id)).where(
            Task.member_id == member.id,
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "onboarding",
            func.coalesce(Task.extra_data["operational_archive"]["archived_at"].astext, "") == "",
        )
    ) or 0
    # 0/0 nao significa "100% concluido"; significa que nenhuma etapa esta exigivel ainda.
    # Para a barra operacional, mostramos 0%. Para o score geral, removemos esse fator
    # da ponderacao para nao premiar nem punir tarefas futuras.
    task_score = 0 if total_onboarding_tasks == 0 else int((completed_onboarding_tasks / total_onboarding_tasks) * 100)

    # 4. Consistencia de horario (0-100)
    consistency_score = _calculate_consistency(db, member.id, window_start, window_end)

    # 5. Respondeu ao onboarding (0 ou 100)
    has_member_response = _has_member_response(db, member, window_start, window_end)
    member_response_score = 100 if has_member_response else 0

    # Compatibilidade da janela e leitura agregada
    has_nps = db.scalar(
        select(func.count(NPSResponse.id)).where(
            NPSResponse.member_id == member.id,
            NPSResponse.response_date >= window_start,
            NPSResponse.response_date <= window_end,
        )
    ) or 0

    # Score ponderado
    weighted_points = (
        checkin_score * WEIGHT_CHECKIN_FREQUENCY
        + assessment_score * WEIGHT_FIRST_ASSESSMENT
        + task_score * WEIGHT_TASK_COMPLETION
        + consistency_score * WEIGHT_CONSISTENCY
        + member_response_score * WEIGHT_MEMBER_RESPONSE
    )
    applicable_weight = 100 if total_onboarding_tasks > 0 else 100 - WEIGHT_TASK_COMPLETION
    weighted_score = weighted_points / max(1, applicable_weight)

    final_score = _apply_engagement_floor(
        weighted_score=weighted_score,
        checkin_count=checkin_count,
        expected_checkins=expected_checkins,
        checkin_score=checkin_score,
        consistency_score=consistency_score,
    )

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
            "member_response": member_response_score,
        },
        "days_since_join": days_since_join,
        "checkin_count": checkin_count,
        "completed_tasks": completed_onboarding_tasks,
        "total_tasks": total_onboarding_tasks,
        "total_journey_tasks": total_journey_tasks,
        "nps_feedback_count": has_nps,
    }


def _apply_engagement_floor(
    *,
    weighted_score: float,
    checkin_count: int,
    expected_checkins: float,
    checkin_score: int,
    consistency_score: int,
) -> int:
    """Evita classificar como amarelo/vermelho um onboarding com rotina já forte.

    Se o aluno já demonstra presença acima do esperado e horário consistente,
    o score mínimo sobe para refletir o comportamento real mesmo antes de
    avaliação, tasks ou resposta formal estarem completas.
    """
    final_score = max(0, min(100, int(round(weighted_score))))
    strong_checkin_volume = max(3, int(round(expected_checkins)))

    if checkin_count >= strong_checkin_volume and checkin_score >= 90 and consistency_score >= 85:
        return max(final_score, 72)
    if checkin_count >= 3 and checkin_score >= 80 and consistency_score >= 75:
        return max(final_score, 60)
    return final_score


def _has_member_response(db: Session, member: Member, window_start: datetime, window_end: datetime) -> bool:
    has_nps = db.scalar(
        select(func.count(NPSResponse.id)).where(
            NPSResponse.member_id == member.id,
            NPSResponse.response_date >= window_start,
            NPSResponse.response_date <= window_end,
        )
    ) or 0
    if has_nps > 0:
        return True

    answered_contact_logs = db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.member_id == member.id,
            AuditLog.action == "call_log_manual",
            AuditLog.details["outcome"].astext == "answered",
            AuditLog.created_at >= window_start,
            AuditLog.created_at <= window_end,
        )
    ) or 0
    if answered_contact_logs > 0:
        return True

    normalized_phone = normalize_phone(member.phone)
    if not normalized_phone:
        return False

    inbound_messages = db.scalar(
        select(func.count(MessageLog.id)).where(
            MessageLog.gym_id == member.gym_id,
            MessageLog.channel == "whatsapp",
            MessageLog.direction == "inbound",
            MessageLog.recipient == normalized_phone,
            MessageLog.created_at >= window_start,
            MessageLog.created_at <= window_end,
        )
    ) or 0
    return inbound_messages > 0


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
    """Job diario que recalcula onboarding_score para membros nos primeiros 30 dias.

    A janela operacional inclui D30-D37 para garantir handoff mesmo se o job
    falhar em um dia especifico.
    """
    now = datetime.now(tz=timezone.utc)
    cutoff_date = (now - timedelta(days=37)).date()

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

    if join_days < 30 or join_days > 37:
        return

    member.onboarding_status = "completed"
    member.retention_stage = "monitoring"

    existing = db.scalar(
        select(Task).where(
            Task.member_id == member.id,
            Task.deleted_at.is_(None),
            or_(
                Task.extra_data["source"].astext == "onboarding_handoff",
                Task.title.ilike("%Handoff D30%"),
            ),
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
