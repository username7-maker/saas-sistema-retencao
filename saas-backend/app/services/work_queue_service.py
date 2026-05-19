from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AITriageRecommendation,
    AutopilotAction,
    Assessment,
    BodyCompositionEvaluation,
    Member,
    MemberStatus,
    RoleEnum,
    Task,
    TaskPriority,
    TaskStatus,
    User,
)
from app.schemas import PaginatedResponse
from app.schemas.ai_triage import AITriageSafeActionPrepareInput
from app.schemas.work_queue import (
    WorkQueueActionResultOut,
    WorkQueueExecuteInput,
    WorkQueueItemOut,
    WorkQueueOutcome,
    WorkQueueOutcomeInput,
)
from app.schemas.autopilot import WorkQueueSendAndWaitInput
from app.services.autopilot_action_service import create_autopilot_action, execute_autopilot_action
from app.services.autopilot_policy_service import AutopilotDecision
from app.services.autopilot_safety_service import check_autopilot_safety
from app.services.communication_channel_service import resolve_communication_channel
from app.services.ai_triage_service import (
    get_ai_triage_recommendation_or_404,
    prepare_ai_triage_recommendation_action,
    serialize_ai_triage_recommendation,
    sync_ai_triage_recommendations,
    update_ai_triage_recommendation_outcome,
)
from app.services.ai_service_agent_service import (
    AI_SERVICE_AGENT_ACTION_TYPE,
    AI_SERVICE_AGENT_DRAFT_READY,
    prepare_ai_service_agent_draft_in_kommo,
    serialize_ai_service_agent_draft,
)
from app.services.student_personal_ai_service import (
    STUDENT_PERSONAL_AI_ACTION_TYPE,
    STUDENT_PERSONAL_AI_DRAFT_READY,
    prepare_student_personal_ai_draft_in_kommo,
    serialize_student_personal_ai_draft,
)
from app.services.audit_service import log_audit_event
from app.services.automation_journey_service import handle_task_outcome_for_journey
from app.services.assessment_analytics_service import get_assessments_queue
from app.services.assessment_service import update_assessment_queue_resolution
from app.services.preferred_shift_service import normalize_preferred_shift, normalize_preferred_shift_scope
from app.services.retention_stage_service import (
    RETENTION_STAGE_COLD_BASE,
    is_cold_base_stage,
    retention_stage_payload,
)
from app.services.task_event_service import record_task_event
from app.services.task_service import is_task_operationally_archived

SourceType = Literal["task", "ai_triage", "assessment_queue", "ai_service_agent", "student_personal_ai"]
StateFilter = Literal["do_now", "awaiting_outcome", "done", "all"]
ShiftFilter = Literal["my_shift", "all", "overnight", "morning", "afternoon", "evening", "unassigned"]
AssigneeFilter = Literal["mine", "unassigned", "all"]
DomainFilter = Literal["all", "operations", "retention", "onboarding", "assessment", "trainer", "commercial", "finance", "manual"]
SourceFilter = Literal["all", "task", "ai_triage", "assessment_queue", "ai_service_agent", "student_personal_ai"]
DAILY_QUEUE_STALE_BACKLOG_AFTER = timedelta(days=14)
DAILY_QUEUE_STALE_BACKLOG_EXEMPT_DOMAINS = {"finance", "trainer"}

TRAINER_TASK_SOURCES = {
    "assessment_training_delivery_check_d8",
    "assessment_feedback_followup",
    "assessment_reassessment_due",
    "assessment_intelligence",
    "assessment_feedback",
    "trainer_followup",
    "training_feedback",
    "training_review",
}
TRAINER_OWNER_ROLES = {"coach", "trainer", "professor", "instrutor", "instructor", "teacher", "trainer_lead"}

FINAL_TASK_OUTCOMES = {
    "responded",
    "scheduled_assessment",
    "will_return",
    "not_interested",
    "invalid_number",
    "payment_confirmed",
    "payment_link_sent",
    "training_delivered",
    "training_adjusted",
    "feedback_positive",
    "needs_training_adjustment",
    "reassessment_scheduled",
    "completed",
}
NEUTRAL_AI_OUTCOMES = {
    "no_response",
    "postponed",
    "forwarded_to_trainer",
    "forwarded_to_reception",
    "forwarded_to_manager",
    "payment_promised",
    "payment_link_sent",
    "charge_disputed",
}
POSITIVE_AI_OUTCOMES = {"responded", "scheduled_assessment", "will_return", "payment_confirmed", "completed"}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _task_extra(task: Task) -> dict:
    return dict(task.extra_data or {}) if isinstance(task.extra_data, dict) else {}


def _is_trainer_task_visible(task: Task) -> bool:
    extra = _task_extra(task)
    source = str(extra.get("source") or "").lower()
    domain = str(extra.get("domain") or "").lower()
    owner_role = str(extra.get("owner_role") or "").lower()
    return task.lead_id is None and (
        domain == "trainer" or (source in TRAINER_TASK_SOURCES and owner_role in TRAINER_OWNER_ROLES)
    )


def _trainer_task_filter():
    source = func.lower(func.coalesce(Task.extra_data["source"].astext, ""))
    domain = func.lower(func.coalesce(Task.extra_data["domain"].astext, ""))
    owner_role = func.lower(func.coalesce(Task.extra_data["owner_role"].astext, ""))
    return and_(
        Task.lead_id.is_(None),
        or_(
            domain == "trainer",
            and_(source.in_(tuple(TRAINER_TASK_SOURCES)), owner_role.in_(tuple(TRAINER_OWNER_ROLES))),
        ),
    )


def _is_finance_task(task: Task) -> bool:
    extra = _task_extra(task)
    return extra.get("source") == "delinquency" or extra.get("domain") == "finance"


def _ensure_task_access(task: Task, current_user: User) -> None:
    if task.gym_id != current_user.gym_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    if _is_finance_task(task) and current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    if current_user.role == RoleEnum.TRAINER and not _is_trainer_task_visible(task):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")


def _task_domain(task: Task) -> str:
    source = str(_task_extra(task).get("source") or "manual").lower()
    domain = str(_task_extra(task).get("domain") or "").lower()
    title = (task.title or "").lower()
    description = (task.description or "").lower()
    if domain == "finance" or source == "delinquency" or "inadimplencia" in title:
        return "finance"
    if task.lead_id:
        return "commercial"
    if _is_trainer_task_visible(task):
        return "trainer"
    if "onboarding" in source or "onboarding" in title:
        return "onboarding"
    if "retention" in source or "reten" in title or "reten" in description or "churn" in title:
        return "retention"
    if "assessment" in source or "avaliacao" in title or "avalia" in title:
        return "assessment"
    return "manual"


def _task_severity(task: Task) -> str:
    if task.priority.value == "urgent":
        return "critical"
    if task.priority.value == "high":
        return "high"
    if task.priority.value == "medium":
        return "medium"
    return "low"


def _task_state(task: Task) -> str:
    if task.status in {TaskStatus.DONE, TaskStatus.CANCELLED}:
        return "done"
    if task.status == TaskStatus.DOING:
        return "awaiting_outcome"
    return "do_now"


def _task_context_path(task: Task) -> str:
    if task.member_id:
        return f"/assessments/members/{task.member_id}?tab=acoes"
    if task.lead_id:
        return f"/crm?leadId={task.lead_id}"
    return "/tasks"


def _parse_optional_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _task_visible_from(task: Task) -> datetime | None:
    return _parse_optional_datetime(_task_extra(task).get("work_queue_visible_from"))


def _technical_ladder_step_label(step: str | None) -> str | None:
    if step == "training_delivery_check_d8":
        return "D+8 treino"
    if step == "training_feedback_d14":
        return "D+14 feedback"
    if step == "reassessment_due":
        return "Reavaliacao"
    return None


def _task_action_label(task: Task) -> str:
    source = str(_task_extra(task).get("source") or "").lower()
    extra = _task_extra(task)
    channel_action_label = str(extra.get("work_queue_channel_action_label") or "").strip()
    if channel_action_label:
        return channel_action_label
    if _task_domain(task) == "trainer":
        if source == "assessment_training_delivery_check_d8":
            return str(extra.get("primary_action_label") or "Verificar treino")
        if source == "assessment_feedback_followup":
            return str(extra.get("primary_action_label") or "Registrar feedback")
        if source == "assessment_reassessment_due":
            return str(extra.get("primary_action_label") or "Agendar reavaliacao")
        if "training" in source or "trainer" in source:
            return str(extra.get("primary_action_label") or "Revisar treino do aluno")
        return str(extra.get("primary_action_label") or "Abrir contexto tecnico")
    if source == "automation_journey":
        return str(extra.get("primary_action_label") or task.title or "Executar etapa da jornada")
    if source == "delinquency" or extra.get("domain") == "finance":
        return str(extra.get("primary_action_label") or "Cobrar inadimplencia")
    if task.suggested_message:
        return "Usar mensagem pronta"
    if task.status == TaskStatus.DOING:
        return "Registrar resultado"
    if "assessment" in source or "avaliacao" in (task.title or "").lower():
        return "Abrir avaliacao"
    if task.lead_id:
        return "Abrir lead"
    return "Iniciar tarefa"


def _task_to_item(task: Task) -> WorkQueueItemOut:
    member_name = task.member.full_name if task.member else None
    lead_name = task.lead.full_name if task.lead else None
    subject_name = member_name or lead_name or task.title
    subject_phone = (task.member.phone if task.member else None) or (task.lead.phone if task.lead else None)
    reason = task.description or task.title
    preferred_shift = getattr(task.member, "preferred_shift", None) if task.member else None
    extra = _task_extra(task)
    retention_stage = extra.get("retention_stage") or (getattr(task.member, "retention_stage", None) if task.member else None)
    retention_payload = retention_stage_payload(str(retention_stage) if retention_stage else None) if _task_domain(task) == "retention" else {}
    technical_step = str(extra.get("technical_ladder_step") or "") or None
    return WorkQueueItemOut(
        source_type="task",
        source_id=task.id,
        subject_name=subject_name,
        member_id=task.member_id,
        lead_id=task.lead_id,
        subject_phone=subject_phone,
        domain=_task_domain(task),
        severity=_task_severity(task),
        preferred_shift=preferred_shift,
        reason=reason[:260],
        primary_action_label=_task_action_label(task),
        primary_action_type="open_context" if not task.suggested_message else "prepare_outbound_message",
        suggested_message=task.suggested_message,
        requires_confirmation=False,
        state=_task_state(task),  # type: ignore[arg-type]
        due_at=task.due_date,
        visible_from=_task_visible_from(task),
        assigned_to_user_id=task.assigned_to_user_id,
        context_path=_task_context_path(task),
        outcome_state=str(_task_extra(task).get("work_queue_outcome") or ("completed" if task.status == TaskStatus.DONE else "pending")),
        retention_stage=retention_payload.get("retention_stage"),
        retention_stage_label=retention_payload.get("retention_stage_label"),
        retention_stage_priority=int(retention_payload.get("retention_stage_priority") or 0),
        technical_ladder_step=technical_step,
        technical_ladder_step_label=_technical_ladder_step_label(technical_step),
        autopilot_state=str(extra.get("autopilot_state") or "") or None,
        autopilot_badges=_task_autopilot_badges(task),
        execution_channel=str(extra.get("work_queue_execution_channel") or "") or None,
        channel_action_label=str(extra.get("work_queue_channel_action_label") or "") or None,
        channel_status=str(extra.get("work_queue_channel_status") or "") or None,
        kommo_contact_id=str(extra.get("kommo_contact_id") or "") or None,
        kommo_lead_id=str(extra.get("kommo_lead_id") or "") or None,
    )


def _task_autopilot_badges(task: Task) -> list[str]:
    extra = _task_extra(task)
    badges: list[str] = []
    if extra.get("source") == "autopilot":
        badges.append("Criada pelo Autopilot")
    if extra.get("autopilot_escalated"):
        badges.append("Escalada apos automacao")
    if extra.get("autopilot_waiting_action_id"):
        badges.append("Aguardando resposta")
    if extra.get("autopilot_auto_resolved"):
        badges.append("Auto-resolvida")
    if extra.get("autopilot_blocked_reason"):
        badges.append("Bloqueada por seguranca")
    if extra.get("work_queue_execution_channel") == "kommo":
        badges.append("Kommo")
    if extra.get("work_queue_channel_status") == "awaiting_kommo":
        badges.append("Aguardando Kommo")
    if extra.get("work_queue_channel_status") == "fallback_whatsapp":
        badges.append("Fallback WhatsApp")
    return badges


def _assessment_queue_due_at(item) -> datetime | None:
    due_date = getattr(item, "next_assessment_due", None)
    if not due_date:
        return None
    return datetime.combine(due_date, datetime.min.time()).replace(tzinfo=timezone.utc)


def _assessment_queue_severity(item) -> str:
    bucket = str(getattr(item, "queue_bucket", "") or "").lower()
    risk_score = int(getattr(item, "risk_score", 0) or 0)
    if bucket in {"never", "overdue"} or risk_score >= 80:
        return "high"
    if bucket == "week" or risk_score >= 55:
        return "medium"
    return "low"


def _assessment_queue_action_label(item) -> str:
    bucket = str(getattr(item, "queue_bucket", "") or "").lower()
    if bucket == "never":
        return "Agendar primeira avaliacao"
    if bucket == "overdue":
        return "Revisar avaliacao vencida"
    if bucket == "week":
        return "Planejar reavaliacao desta semana"
    return "Abrir contexto tecnico"


def _assessment_queue_domain(item) -> str:
    bucket = str(getattr(item, "queue_bucket", "") or "").lower()
    return "assessment" if bucket == "never" else "trainer"


def _ensure_assessment_queue_access(item: WorkQueueItemOut, current_user: User) -> None:
    if current_user.role in {RoleEnum.OWNER, RoleEnum.MANAGER}:
        return
    if current_user.role == RoleEnum.TRAINER and item.domain == "trainer":
        return
    if current_user.role == RoleEnum.RECEPTIONIST and item.domain != "trainer":
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")


def _assessment_queue_to_item(item) -> WorkQueueItemOut:
    resolution_status = str(getattr(item, "queue_resolution_status", "active") or "active").lower()
    state = "done" if resolution_status in {"scheduled", "dismissed"} else "do_now"
    due_label = str(getattr(item, "due_label", "") or "").strip()
    coverage_label = str(getattr(item, "coverage_label", "") or "").strip()
    reason = " - ".join(part for part in (due_label, coverage_label) if part)
    if not reason:
        reason = "Pendencia tecnica de avaliacao ou acompanhamento."
    return WorkQueueItemOut(
        source_type="assessment_queue",
        source_id=getattr(item, "id"),
        subject_name=getattr(item, "full_name"),
        member_id=getattr(item, "id"),
        lead_id=None,
        subject_phone=None,
        domain=_assessment_queue_domain(item),
        severity=_assessment_queue_severity(item),
        preferred_shift=getattr(item, "preferred_shift", None),
        reason=reason[:260],
        primary_action_label=_assessment_queue_action_label(item),
        primary_action_type="open_context",
        suggested_message=None,
        requires_confirmation=False,
        state=state,  # type: ignore[arg-type]
        due_at=_assessment_queue_due_at(item),
        assigned_to_user_id=None,
        context_path=f"/assessments/members/{getattr(item, 'id')}?tab=acoes",
        outcome_state=resolution_status,
        autopilot_badges=["Fila de avaliacoes"],
    )


def _member_assessment_queue_item(db: Session, *, member_id: UUID, current_user: User) -> WorkQueueItemOut:
    member = db.scalar(
        select(Member)
        .where(
            Member.id == member_id,
            Member.gym_id == current_user.gym_id,
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
        )
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")

    latest_assessment = db.scalar(
        select(Assessment)
        .where(Assessment.member_id == member.id, Assessment.deleted_at.is_(None))
        .order_by(Assessment.assessment_date.desc(), Assessment.updated_at.desc())
        .limit(1)
    )
    latest_body_composition = db.scalar(
        select(BodyCompositionEvaluation)
        .where(BodyCompositionEvaluation.member_id == member.id)
        .order_by(BodyCompositionEvaluation.evaluation_date.desc(), BodyCompositionEvaluation.updated_at.desc())
        .limit(1)
    )
    now = _now()
    today = now.date()
    cutoff_90 = (now - timedelta(days=90)).date()
    next_7 = today + timedelta(days=7)
    queue_resolution_status = str((member.extra_data or {}).get("assessment_queue_resolution") or "active").lower()

    formal_date = latest_assessment.assessment_date.date() if latest_assessment and latest_assessment.assessment_date else None
    body_date = latest_body_composition.evaluation_date if latest_body_composition else None
    if formal_date is None and body_date is None:
        bucket = "never"
        next_assessment_due = None
        coverage_label = "Nenhuma avaliacao registrada"
        due_label = "Primeira avaliacao pendente"
        urgency_bonus = 300
    else:
        latest_coverage_date = max(value for value in (formal_date, body_date) if value is not None)
        latest_source_is_body = body_date is not None and (formal_date is None or body_date > formal_date)
        next_assessment_due = None if latest_source_is_body else latest_assessment.next_assessment_due
        if latest_coverage_date < cutoff_90 or (next_assessment_due and next_assessment_due < today):
            bucket = "overdue"
            coverage_label = "Cobertura vencida"
            due_label = f"Atrasada desde {next_assessment_due.strftime('%d/%m/%Y')}" if next_assessment_due else "Fora da janela ideal de 90 dias"
            urgency_bonus = 240
        elif next_assessment_due and next_assessment_due <= next_7:
            bucket = "week"
            coverage_label = "Avaliacao prevista nesta semana"
            due_label = "Vence hoje" if next_assessment_due == today else f"Janela ate {next_assessment_due.strftime('%d/%m/%Y')}"
            urgency_bonus = 180
        elif next_assessment_due and next_assessment_due > next_7:
            bucket = "upcoming"
            coverage_label = "Planejamento futuro"
            due_label = f"Proxima janela em {next_assessment_due.strftime('%d/%m/%Y')}"
            urgency_bonus = 120
        else:
            bucket = "covered"
            coverage_label = "Base coberta recentemente"
            due_label = "Sem proxima janela definida"
            urgency_bonus = 60

    return _assessment_queue_to_item(
        SimpleNamespace(
            id=member.id,
            full_name=member.full_name,
            preferred_shift=member.preferred_shift,
            risk_score=int(member.risk_score or 0),
            next_assessment_due=next_assessment_due,
            queue_bucket=bucket,
            coverage_label=coverage_label,
            due_label=due_label,
            urgency_score=int(member.risk_score or 0) + urgency_bonus,
            queue_resolution_status=queue_resolution_status,
        )
    )


def _ai_state(recommendation: AITriageRecommendation) -> str:
    if recommendation.outcome_state in {"positive", "neutral", "negative", "dismissed"}:
        return "done"
    if recommendation.execution_state in {"prepared", "queued", "running", "completed"} and recommendation.outcome_state == "pending":
        return "awaiting_outcome"
    return "do_now"


def _ai_context_path(item) -> str:
    if item.member_id:
        return f"/assessments/members/{item.member_id}?tab=acoes"
    if item.lead_id:
        return f"/crm?leadId={item.lead_id}"
    return "/ai/triage"


def _ai_to_item(recommendation: AITriageRecommendation) -> WorkQueueItemOut:
    item = serialize_ai_triage_recommendation(recommendation)
    preferred_shift = item.metadata.get("preferred_shift")
    subject_phone = item.metadata.get("subject_phone")
    retention_stage = item.metadata.get("retention_stage")
    retention_payload = retention_stage_payload(str(retention_stage) if retention_stage else None) if item.source_domain == "retention" else {}
    return WorkQueueItemOut(
        source_type="ai_triage",
        source_id=item.id,
        subject_name=item.subject_name,
        member_id=item.member_id,
        lead_id=item.lead_id,
        subject_phone=str(subject_phone) if subject_phone else None,
        domain=item.source_domain,
        severity=item.priority_bucket,
        preferred_shift=str(preferred_shift) if preferred_shift else None,
        reason=item.operator_summary or item.why_now_summary,
        primary_action_label=item.primary_action_label or item.recommended_action,
        primary_action_type=str(item.primary_action_type or "create_task"),
        suggested_message=item.suggested_message,
        requires_confirmation=item.requires_explicit_approval,
        state=_ai_state(recommendation),  # type: ignore[arg-type]
        due_at=None,
        assigned_to_user_id=item.recommended_owner.user_id if item.recommended_owner else None,
        context_path=_ai_context_path(item),
        outcome_state=item.outcome_state,
        retention_stage=retention_payload.get("retention_stage"),
        retention_stage_label=retention_payload.get("retention_stage_label"),
        retention_stage_priority=int(retention_payload.get("retention_stage_priority") or 0),
    )


def _ai_service_agent_state(action: AutopilotAction) -> str:
    if action.status in {"succeeded", "cancelled"}:
        return "done"
    if action.status == "awaiting_outcome":
        return "awaiting_outcome"
    return "do_now"


def _ai_service_agent_to_item(db: Session, action: AutopilotAction) -> WorkQueueItemOut:
    draft = serialize_ai_service_agent_draft(action)
    member = db.get(Member, action.member_id) if action.member_id else None
    subject_name = member.full_name if member else "Conversa Kommo"
    preferred_shift = getattr(member, "preferred_shift", None) if member else None
    domain = "commercial" if draft.intent == "sales" else draft.intent
    if domain in {"cancellation", "complaint", "human_request", "opt_out"}:
        domain = "manual"
    if domain == "injury":
        domain = "assessment"
    if domain == "finance_dispute":
        domain = "finance"
    severity = "high" if draft.sensitivity == "sensitive" or action.status in {"blocked", "escalated"} else "medium"
    if action.status == AI_SERVICE_AGENT_DRAFT_READY:
        primary_label = "Preparar na Kommo"
    elif action.status == "awaiting_outcome":
        primary_label = "Aguardando Kommo"
    elif action.status in {"blocked", "escalated"}:
        primary_label = "Assumir conversa"
    else:
        primary_label = "Revisar conversa"
    return WorkQueueItemOut(
        source_type="ai_service_agent",
        source_id=action.id,
        subject_name=subject_name,
        member_id=action.member_id,
        lead_id=action.lead_id,
        subject_phone=getattr(member, "phone", None) if member else None,
        domain=domain,
        severity=severity,
        preferred_shift=str(preferred_shift) if preferred_shift else None,
        reason=draft.summary,
        primary_action_label=primary_label,
        primary_action_type="prepare_kommo",
        suggested_message=draft.draft_reply,
        requires_confirmation=False,
        state=_ai_service_agent_state(action),  # type: ignore[arg-type]
        due_at=action.created_at,
        assigned_to_user_id=None,
        context_path="/settings",
        outcome_state=action.outcome or action.status,
        autopilot_state=action.status,
        autopilot_badges=["Agente Kommo", "Draft-only"] + (["Bloqueado por seguranca"] if action.status == "blocked" else []),
        execution_channel="kommo",
        channel_action_label=primary_label,
        channel_status=action.status,
        kommo_contact_id=draft.kommo_contact_id,
        kommo_lead_id=draft.kommo_lead_id,
    )


def _student_personal_ai_state(action: AutopilotAction) -> str:
    if action.status in {"succeeded", "cancelled"}:
        return "done"
    if action.status == "awaiting_outcome":
        return "awaiting_outcome"
    return "do_now"


def _student_personal_ai_to_item(db: Session, action: AutopilotAction) -> WorkQueueItemOut:
    draft = serialize_student_personal_ai_draft(action)
    member = db.get(Member, action.member_id) if action.member_id else None
    subject_name = member.full_name if member else "Aluno Kommo"
    preferred_shift = getattr(member, "preferred_shift", None) if member else None
    severity = "high" if action.status in {"blocked", "escalated"} or draft.sensitivity == "sensitive" else "medium"
    if action.status == STUDENT_PERSONAL_AI_DRAFT_READY:
        primary_label = "Preparar resposta Kommo"
    elif action.status == "awaiting_outcome":
        primary_label = "Aguardando Kommo"
    elif action.status in {"blocked", "escalated"}:
        primary_label = "Assumir conversa"
    else:
        primary_label = "Revisar aluno"
    badges = ["Aluno Kommo", "Aluno Cordex", "Draft-only"]
    if draft.intent == "movement_video":
        badges.append("Video")
    if action.status == "blocked":
        badges.append("Bloqueado por seguranca")
    return WorkQueueItemOut(
        source_type="student_personal_ai",
        source_id=action.id,
        subject_name=subject_name,
        member_id=action.member_id,
        lead_id=action.lead_id,
        subject_phone=getattr(member, "phone", None) if member else None,
        domain="trainer",
        severity=severity,
        preferred_shift=str(preferred_shift) if preferred_shift else None,
        reason=draft.summary,
        primary_action_label=primary_label,
        primary_action_type="prepare_kommo",
        suggested_message=draft.draft_reply,
        requires_confirmation=False,
        state=_student_personal_ai_state(action),  # type: ignore[arg-type]
        due_at=action.created_at,
        assigned_to_user_id=None,
        context_path=f"/assessments/members/{action.member_id}" if action.member_id else "/tasks",
        outcome_state=action.outcome or action.status,
        autopilot_state=action.status,
        autopilot_badges=badges,
        execution_channel="kommo",
        channel_action_label=primary_label,
        channel_status=action.status,
        kommo_contact_id=draft.kommo_contact_id,
        kommo_lead_id=draft.kommo_lead_id,
    )


def _effective_shift_filter(current_user: User, shift: ShiftFilter) -> ShiftFilter:
    if shift == "all" and current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER}:
        return "my_shift"
    return shift


def _matches_shift(item: WorkQueueItemOut, current_user: User, shift: ShiftFilter) -> bool:
    effective_shift = _effective_shift_filter(current_user, shift)
    if effective_shift == "all":
        return True
    if effective_shift == "unassigned":
        return item.preferred_shift is None
    if effective_shift == "my_shift":
        targets = normalize_preferred_shift_scope(
            getattr(current_user, "work_shift_scope", None),
            fallback=getattr(current_user, "work_shift", None),
        )
    else:
        target = normalize_preferred_shift(effective_shift)
        targets = [target] if target else []
    if not targets:
        return item.preferred_shift is None
    if item.preferred_shift is None:
        return True
    return normalize_preferred_shift(item.preferred_shift) in targets


def _matches_assignee(item: WorkQueueItemOut, current_user: User, assignee: AssigneeFilter) -> bool:
    if assignee == "all":
        return True
    if assignee == "unassigned":
        return item.assigned_to_user_id is None
    return item.assigned_to_user_id == current_user.id


def _work_item_score(item: WorkQueueItemOut, now: datetime) -> tuple[int, datetime]:
    severity_weight = {"critical": 500, "urgent": 500, "high": 350, "medium": 180, "low": 80}.get(item.severity, 120)
    state_weight = {"do_now": 200, "awaiting_outcome": 140, "done": -500}.get(item.state, 0)
    finance_weight = 120 if item.domain == "finance" and item.severity in {"critical", "high"} else 0
    retention_weight = int(item.retention_stage_priority or 0) if item.domain == "retention" else 0
    if is_cold_base_stage(item.retention_stage):
        retention_weight -= 260
    due_weight = 0
    if item.due_at and item.state != "done":
        if item.due_at <= now:
            due_weight = 260
        elif item.due_at <= now + timedelta(days=1):
            due_weight = 160
        elif item.due_at <= now + timedelta(days=7):
            due_weight = 60
    unassigned_weight = 70 if item.assigned_to_user_id is None and item.state != "done" else 0
    return (
        severity_weight + state_weight + finance_weight + retention_weight + due_weight + unassigned_weight,
        item.due_at or datetime.max.replace(tzinfo=timezone.utc),
    )


def _as_aware_datetime(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _is_stale_daily_backlog(item: WorkQueueItemOut, now: datetime) -> bool:
    if item.domain in DAILY_QUEUE_STALE_BACKLOG_EXEMPT_DOMAINS:
        return False
    if item.due_at is None:
        return False
    due_at = _as_aware_datetime(item.due_at)
    return due_at < now - DAILY_QUEUE_STALE_BACKLOG_AFTER


def _filter_items(
    items: list[WorkQueueItemOut],
    *,
    current_user: User,
    state: StateFilter,
    shift: ShiftFilter,
    assignee: AssigneeFilter,
    domain: DomainFilter,
) -> list[WorkQueueItemOut]:
    filtered = []
    now = _now()
    for item in items:
        if state != "all" and item.state != state:
            continue
        if domain == "operations" and item.domain in {"retention", "trainer"}:
            continue
        if domain not in {"all", "operations"} and item.domain != domain:
            continue
        if state == "do_now":
            if item.domain == "retention" and is_cold_base_stage(item.retention_stage):
                continue
            if item.visible_from and _as_aware_datetime(item.visible_from) > now:
                continue
            if _is_stale_daily_backlog(item, now):
                continue
        if not _matches_shift(item, current_user, shift):
            continue
        if not _matches_assignee(item, current_user, assignee):
            continue
        filtered.append(item)
    return sorted(filtered, key=lambda item: _work_item_score(item, now), reverse=True)


def _list_task_items(db: Session, current_user: User) -> list[WorkQueueItemOut]:
    filters = [Task.gym_id == current_user.gym_id, Task.deleted_at.is_(None)]
    filters.append(func.coalesce(Task.extra_data["operational_archive"]["archived_at"].astext, "") == "")
    if current_user.role == RoleEnum.TRAINER:
        filters.append(_trainer_task_filter())
    elif current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST}:
        filters.append(
            func.coalesce(Task.extra_data["domain"].astext, "") != "finance",
        )
        filters.append(func.coalesce(Task.extra_data["source"].astext, "") != "delinquency")
    tasks = list(
        db.scalars(
            select(Task)
            .options(joinedload(Task.member), joinedload(Task.lead))
            .where(*filters)
            .order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
            .limit(300)
        )
        .unique()
        .all()
    )
    return [_task_to_item(task) for task in tasks if not is_task_operationally_archived(task)]


def _list_ai_items(db: Session, current_user: User) -> list[WorkQueueItemOut]:
    if current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST}:
        return []
    sync_ai_triage_recommendations(db, gym_id=current_user.gym_id)
    recommendations = list(
        db.scalars(
            select(AITriageRecommendation)
            .where(AITriageRecommendation.gym_id == current_user.gym_id, AITriageRecommendation.is_active.is_(True))
            .order_by(AITriageRecommendation.priority_score.desc(), AITriageRecommendation.updated_at.desc())
            .limit(200)
        ).all()
    )
    return [_ai_to_item(recommendation) for recommendation in recommendations]


def _list_ai_service_agent_items(db: Session, current_user: User) -> list[WorkQueueItemOut]:
    if current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER, RoleEnum.SALESPERSON}:
        return []
    actions = list(
        db.scalars(
            select(AutopilotAction)
            .where(
                AutopilotAction.gym_id == current_user.gym_id,
                AutopilotAction.action_type == AI_SERVICE_AGENT_ACTION_TYPE,
                AutopilotAction.status.in_([AI_SERVICE_AGENT_DRAFT_READY, "blocked", "escalated", "awaiting_outcome"]),
            )
            .order_by(AutopilotAction.created_at.desc())
            .limit(100)
        ).all()
    )
    items = [_ai_service_agent_to_item(db, action) for action in actions]
    if current_user.role == RoleEnum.TRAINER:
        return [item for item in items if item.domain == "assessment"]
    if current_user.role == RoleEnum.SALESPERSON:
        return [item for item in items if item.domain == "commercial"]
    return items


def _list_student_personal_ai_items(db: Session, current_user: User) -> list[WorkQueueItemOut]:
    if current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER}:
        return []
    actions = list(
        db.scalars(
            select(AutopilotAction)
            .where(
                AutopilotAction.gym_id == current_user.gym_id,
                AutopilotAction.action_type == STUDENT_PERSONAL_AI_ACTION_TYPE,
                AutopilotAction.status.in_([STUDENT_PERSONAL_AI_DRAFT_READY, "blocked", "escalated", "awaiting_outcome"]),
            )
            .order_by(AutopilotAction.created_at.desc())
            .limit(100)
        ).all()
    )
    return [_student_personal_ai_to_item(db, action) for action in actions]


def _list_assessment_queue_items(
    db: Session,
    current_user: User,
    *,
    exclude_member_ids: set[UUID] | None = None,
) -> list[WorkQueueItemOut]:
    if current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER, RoleEnum.RECEPTIONIST}:
        return []
    queue = get_assessments_queue(db, page=1, page_size=200, bucket="all", gym_id=current_user.gym_id)
    excluded = exclude_member_ids or set()
    items: list[WorkQueueItemOut] = []
    for queue_item in queue.items:
        member_id = getattr(queue_item, "id", None)
        if member_id in excluded:
            continue
        item = _assessment_queue_to_item(queue_item)
        if current_user.role == RoleEnum.TRAINER and item.domain != "trainer":
            continue
        if current_user.role == RoleEnum.RECEPTIONIST and item.domain == "trainer":
            continue
        items.append(item)
    return items


def list_work_queue_items(
    db: Session,
    *,
    current_user: User,
    state: StateFilter = "do_now",
    shift: ShiftFilter = "my_shift",
    assignee: AssigneeFilter = "all",
    domain: DomainFilter = "all",
    source: SourceFilter = "all",
    page: int = 1,
    page_size: int = 25,
) -> PaginatedResponse[WorkQueueItemOut]:
    items: list[WorkQueueItemOut] = []
    if source in {"all", "task"}:
        items.extend(_list_task_items(db, current_user))
    if source == "all" and domain in {"all", "operations", "assessment", "trainer"}:
        trainer_task_member_ids = {
            item.member_id for item in items if item.domain == "trainer" and item.member_id is not None
        }
        items.extend(_list_assessment_queue_items(db, current_user, exclude_member_ids=trainer_task_member_ids))
    if source in {"all", "ai_triage"}:
        items.extend(_list_ai_items(db, current_user))
    if source in {"all", "ai_service_agent"}:
        items.extend(_list_ai_service_agent_items(db, current_user))
    if source in {"all", "student_personal_ai"}:
        items.extend(_list_student_personal_ai_items(db, current_user))

    filtered = _filter_items(items, current_user=current_user, state=state, shift=shift, assignee=assignee, domain=domain)
    total = len(filtered)
    start = (page - 1) * page_size
    return PaginatedResponse(items=filtered[start : start + page_size], total=total, page=page, page_size=page_size)


def get_work_queue_item(db: Session, *, current_user: User, source_type: SourceType, source_id: UUID) -> WorkQueueItemOut:
    if source_type == "task":
        task = db.scalar(
            select(Task)
            .options(joinedload(Task.member), joinedload(Task.lead))
            .where(Task.id == source_id, Task.deleted_at.is_(None))
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
        if is_task_operationally_archived(task):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
        _ensure_task_access(task, current_user)
        return _task_to_item(task)

    if source_type == "assessment_queue":
        if current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER, RoleEnum.RECEPTIONIST}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
        item = _member_assessment_queue_item(db, member_id=source_id, current_user=current_user)
        _ensure_assessment_queue_access(item, current_user)
        return item

    if source_type == "ai_service_agent":
        action = db.scalar(
            select(AutopilotAction).where(
                AutopilotAction.gym_id == current_user.gym_id,
                AutopilotAction.id == source_id,
                AutopilotAction.action_type == AI_SERVICE_AGENT_ACTION_TYPE,
            )
        )
        if action is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
        item = _ai_service_agent_to_item(db, action)
        if current_user.role == RoleEnum.TRAINER and item.domain != "assessment":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
        if current_user.role == RoleEnum.SALESPERSON and item.domain != "commercial":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
        return item

    if source_type == "student_personal_ai":
        action = db.scalar(
            select(AutopilotAction).where(
                AutopilotAction.gym_id == current_user.gym_id,
                AutopilotAction.id == source_id,
                AutopilotAction.action_type == STUDENT_PERSONAL_AI_ACTION_TYPE,
            )
        )
        if action is None or current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
        return _student_personal_ai_to_item(db, action)

    recommendation = get_ai_triage_recommendation_or_404(db, recommendation_id=source_id, gym_id=current_user.gym_id)
    if current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    return _ai_to_item(recommendation)


def _execute_assessment_queue_item(
    db: Session,
    *,
    member_id: UUID,
    current_user: User,
    payload: WorkQueueExecuteInput,
    ip_address: str | None,
    user_agent: str | None,
) -> WorkQueueActionResultOut:
    item = _member_assessment_queue_item(db, member_id=member_id, current_user=current_user)
    _ensure_assessment_queue_access(item, current_user)
    log_audit_event(
        db,
        action="work_queue_assessment_queue_opened",
        entity="assessment_queue",
        user=current_user,
        member_id=member_id,
        entity_id=member_id,
        details={"operator_note": payload.operator_note, "source": "work_queue"},
        ip_address=ip_address,
        user_agent=user_agent,
        flush=False,
    )
    db.flush()
    return WorkQueueActionResultOut(
        item=item,
        detail="Abra o Perfil 360, revise avaliacao/treino e registre o resultado.",
        prepared_message=item.suggested_message,
        context_path=item.context_path,
        task_id=None,
        supported=True,
    )


def _execute_task(
    db: Session,
    *,
    task_id: UUID,
    current_user: User,
    payload: WorkQueueExecuteInput,
    ip_address: str | None,
    user_agent: str | None,
) -> WorkQueueActionResultOut:
    task = db.scalar(
        select(Task)
        .options(joinedload(Task.member), joinedload(Task.lead))
        .where(Task.id == task_id, Task.deleted_at.is_(None))
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    if is_task_operationally_archived(task):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    _ensure_task_access(task, current_user)

    extra = _task_extra(task)
    extra.update(
        {
            "work_queue_execution_started_at": _now().isoformat(),
            "work_queue_execution_started_by_user_id": str(current_user.id),
            "work_queue_operator_note": payload.operator_note,
        }
    )
    task.extra_data = extra
    if task.status == TaskStatus.TODO:
        task.status = TaskStatus.DOING
        task.kanban_column = TaskStatus.DOING.value
        task.completed_at = None
    db.add(task)
    record_task_event(
        db,
        task=task,
        current_user=current_user,
        event_type="execution_started",
        note=payload.operator_note,
        metadata_json={"source": "work_queue", "previous_status": "todo"},
        flush=False,
    )
    log_audit_event(
        db,
        action="work_queue_task_execution_started",
        entity="task",
        user=current_user,
        member_id=task.member_id,
        entity_id=task.id,
        details={"operator_note": payload.operator_note, "status": task.status.value},
        ip_address=ip_address,
        user_agent=user_agent,
        flush=False,
    )
    db.flush()
    item = _task_to_item(task)
    return WorkQueueActionResultOut(
        item=item,
        detail="Task colocada em execucao. Registre o resultado apos o contato.",
        prepared_message=task.suggested_message,
        context_path=item.context_path,
        task_id=task.id,
        supported=True,
    )


def _execute_ai_triage(
    db: Session,
    *,
    recommendation_id: UUID,
    current_user: User,
    payload: WorkQueueExecuteInput,
    ip_address: str | None,
    user_agent: str | None,
) -> WorkQueueActionResultOut:
    recommendation = get_ai_triage_recommendation_or_404(
        db,
        recommendation_id=recommendation_id,
        gym_id=current_user.gym_id,
    )
    if current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    item_before = _ai_to_item(recommendation)
    if item_before.state == "awaiting_outcome":
        metadata = dict((recommendation.payload_snapshot or {}).get("metadata") or {})
        task_id_raw = metadata.get("prepared_task_id")
        task_id = UUID(str(task_id_raw)) if task_id_raw else None
        return WorkQueueActionResultOut(
            item=item_before,
            detail="Acao ja preparada. Registre o resultado para fechar o ciclo.",
            prepared_message=item_before.suggested_message,
            context_path=str(metadata.get("follow_up_url") or item_before.context_path),
            task_id=task_id,
            supported=True,
        )
    if item_before.requires_confirmation and not payload.confirm_approval and recommendation.approval_state != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item critico ou degradado exige confirmacao explicita antes da acao.",
        )

    prepared = prepare_ai_triage_recommendation_action(
        db,
        recommendation_id=recommendation_id,
        gym_id=current_user.gym_id,
        action=AITriageSafeActionPrepareInput(action=item_before.primary_action_type).action,
        current_user=current_user,
        operator_note=payload.operator_note,
        auto_approve=payload.auto_approve or not item_before.requires_confirmation,
        confirm_approval=payload.confirm_approval,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    recommendation = get_ai_triage_recommendation_or_404(db, recommendation_id=recommendation_id, gym_id=current_user.gym_id)
    item = _ai_to_item(recommendation)
    return WorkQueueActionResultOut(
        item=item,
        detail=prepared.detail,
        prepared_message=prepared.prepared_message,
        context_path=prepared.follow_up_url or item.context_path,
        task_id=prepared.task_id,
        supported=prepared.supported,
    )


def _execute_ai_service_agent(
    db: Session,
    *,
    action_id: UUID,
    current_user: User,
    payload: WorkQueueExecuteInput,
    ip_address: str | None,
    user_agent: str | None,
) -> WorkQueueActionResultOut:
    action = db.scalar(
        select(AutopilotAction).where(
            AutopilotAction.gym_id == current_user.gym_id,
            AutopilotAction.id == action_id,
            AutopilotAction.action_type == AI_SERVICE_AGENT_ACTION_TYPE,
        )
    )
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    item_before = _ai_service_agent_to_item(db, action)
    if current_user.role == RoleEnum.TRAINER and item_before.domain != "assessment":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    if current_user.role == RoleEnum.SALESPERSON and item_before.domain != "commercial":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")

    if action.status != AI_SERVICE_AGENT_DRAFT_READY:
        return WorkQueueActionResultOut(
            item=item_before,
            detail="Este item exige assumicao humana. Abra a conversa na Kommo e registre o resultado depois.",
            prepared_message=item_before.suggested_message,
            context_path=item_before.context_path,
            task_id=None,
            supported=True,
        )

    prepared = prepare_ai_service_agent_draft_in_kommo(db, gym_id=current_user.gym_id, draft_id=action_id, flush=False)
    log_audit_event(
        db,
        action="work_queue_ai_service_agent_prepared",
        entity="autopilot_action",
        user=current_user,
        member_id=prepared.draft.member_id,
        entity_id=action_id,
        details={"operator_note": payload.operator_note, "status": prepared.draft.status},
        ip_address=ip_address,
        user_agent=user_agent,
        flush=False,
    )
    return WorkQueueActionResultOut(
        item=_ai_service_agent_to_item(db, action),
        detail=prepared.detail,
        prepared_message=prepared.draft.draft_reply,
        context_path="/settings",
        task_id=None,
        supported=True,
    )


def _update_ai_service_agent_outcome(
    db: Session,
    *,
    action_id: UUID,
    current_user: User,
    payload: WorkQueueOutcomeInput,
    ip_address: str | None,
    user_agent: str | None,
) -> WorkQueueActionResultOut:
    action = db.scalar(
        select(AutopilotAction).where(
            AutopilotAction.gym_id == current_user.gym_id,
            AutopilotAction.id == action_id,
            AutopilotAction.action_type == AI_SERVICE_AGENT_ACTION_TYPE,
        )
    )
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")

    item_before = _ai_service_agent_to_item(db, action)
    if current_user.role == RoleEnum.TRAINER and item_before.domain != "assessment":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    if current_user.role == RoleEnum.SALESPERSON and item_before.domain != "commercial":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")

    now = datetime.now(timezone.utc)
    final_outcomes = {"responded", "completed", "will_return", "scheduled_assessment", "payment_confirmed"}
    escalated_outcomes = {
        "forwarded_to_manager",
        "forwarded_to_trainer",
        "forwarded_to_reception",
        "charge_disputed",
        "needs_training_adjustment",
        "training_missing",
    }
    cancelled_outcomes = {"not_interested", "invalid_number"}

    action.outcome = payload.outcome
    action.metadata_json = {
        **(action.metadata_json or {}),
        "last_work_queue_outcome": payload.outcome,
        "last_work_queue_note": payload.note,
        "last_work_queue_contact_channel": payload.contact_channel,
        "last_work_queue_user_id": str(current_user.id),
        "last_work_queue_recorded_at": now.isoformat(),
    }
    if payload.outcome in final_outcomes:
        action.status = "succeeded"
        action.completed_at = now
    elif payload.outcome in escalated_outcomes:
        action.status = "escalated"
        action.escalation_reason = payload.note or "Encaminhado pela Work Queue."
    elif payload.outcome in cancelled_outcomes:
        action.status = "cancelled"
        action.completed_at = now
    elif payload.outcome in {"no_response", "postponed"}:
        action.status = "awaiting_outcome"
        if payload.scheduled_for:
            action.cooldown_until = payload.scheduled_for
    else:
        action.status = "succeeded"
        action.completed_at = now

    log_audit_event(
        db,
        action="work_queue_ai_service_agent_outcome_updated",
        entity="autopilot_action",
        user=current_user,
        member_id=action.member_id,
        entity_id=action.id,
        details={
            "outcome": payload.outcome,
            "status": action.status,
            "note": payload.note,
            "contact_channel": payload.contact_channel,
        },
        ip_address=ip_address,
        user_agent=user_agent,
        flush=False,
    )
    db.flush()
    item = _ai_service_agent_to_item(db, action)
    return WorkQueueActionResultOut(
        item=item,
        detail="Resultado registrado no Agente Kommo.",
        prepared_message=item.suggested_message,
        context_path=item.context_path,
        task_id=None,
    )


def _execute_student_personal_ai(
    db: Session,
    *,
    action_id: UUID,
    current_user: User,
    payload: WorkQueueExecuteInput,
    ip_address: str | None,
    user_agent: str | None,
) -> WorkQueueActionResultOut:
    action = db.scalar(
        select(AutopilotAction).where(
            AutopilotAction.gym_id == current_user.gym_id,
            AutopilotAction.id == action_id,
            AutopilotAction.action_type == STUDENT_PERSONAL_AI_ACTION_TYPE,
        )
    )
    if action is None or current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")

    item_before = _student_personal_ai_to_item(db, action)
    if action.status != STUDENT_PERSONAL_AI_DRAFT_READY:
        return WorkQueueActionResultOut(
            item=item_before,
            detail="Este item exige assumicao humana. Abra a conversa na Kommo e registre o resultado depois.",
            prepared_message=item_before.suggested_message,
            context_path=item_before.context_path,
            task_id=None,
            supported=True,
        )

    prepared = prepare_student_personal_ai_draft_in_kommo(db, gym_id=current_user.gym_id, draft_id=action_id, flush=False)
    log_audit_event(
        db,
        action="work_queue_student_personal_ai_prepared",
        entity="autopilot_action",
        user=current_user,
        member_id=prepared.draft.member_id,
        entity_id=action_id,
        details={"operator_note": payload.operator_note, "status": prepared.draft.status, "intent": prepared.draft.intent},
        ip_address=ip_address,
        user_agent=user_agent,
        flush=False,
    )
    return WorkQueueActionResultOut(
        item=_student_personal_ai_to_item(db, action),
        detail=prepared.detail,
        prepared_message=prepared.draft.draft_reply,
        context_path=f"/assessments/members/{prepared.draft.member_id}" if prepared.draft.member_id else "/tasks",
        task_id=None,
        supported=True,
    )


def _update_student_personal_ai_outcome(
    db: Session,
    *,
    action_id: UUID,
    current_user: User,
    payload: WorkQueueOutcomeInput,
    ip_address: str | None,
    user_agent: str | None,
) -> WorkQueueActionResultOut:
    action = db.scalar(
        select(AutopilotAction).where(
            AutopilotAction.gym_id == current_user.gym_id,
            AutopilotAction.id == action_id,
            AutopilotAction.action_type == STUDENT_PERSONAL_AI_ACTION_TYPE,
        )
    )
    if action is None or current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")

    now = datetime.now(timezone.utc)
    final_outcomes = {
        "responded",
        "completed",
        "training_delivered",
        "training_adjusted",
        "feedback_positive",
        "reassessment_scheduled",
    }
    escalated_outcomes = {
        "forwarded_to_manager",
        "forwarded_to_trainer",
        "needs_training_adjustment",
        "training_missing",
    }

    action.outcome = payload.outcome
    action.metadata_json = {
        **(action.metadata_json or {}),
        "last_work_queue_outcome": payload.outcome,
        "last_work_queue_note": payload.note,
        "last_work_queue_contact_channel": payload.contact_channel,
        "last_work_queue_user_id": str(current_user.id),
        "last_work_queue_recorded_at": now.isoformat(),
    }
    if payload.outcome in final_outcomes:
        action.status = "succeeded"
        action.completed_at = now
    elif payload.outcome in escalated_outcomes:
        action.status = "escalated"
        action.escalation_reason = payload.note or "Encaminhado pela Work Queue."
    elif payload.outcome in {"not_interested", "invalid_number"}:
        action.status = "cancelled"
        action.completed_at = now
    elif payload.outcome in {"no_response", "postponed"}:
        action.status = "awaiting_outcome"
        if payload.scheduled_for:
            action.cooldown_until = payload.scheduled_for
    else:
        action.status = "succeeded"
        action.completed_at = now

    log_audit_event(
        db,
        action="work_queue_student_personal_ai_outcome_updated",
        entity="autopilot_action",
        user=current_user,
        member_id=action.member_id,
        entity_id=action.id,
        details={
            "outcome": payload.outcome,
            "status": action.status,
            "note": payload.note,
            "contact_channel": payload.contact_channel,
        },
        ip_address=ip_address,
        user_agent=user_agent,
        flush=False,
    )
    db.flush()
    item = _student_personal_ai_to_item(db, action)
    return WorkQueueActionResultOut(
        item=item,
        detail="Resultado registrado no Aluno Cordex.",
        prepared_message=item.suggested_message,
        context_path=item.context_path,
        task_id=None,
    )


def execute_work_queue_item(
    db: Session,
    *,
    current_user: User,
    source_type: SourceType,
    source_id: UUID,
    payload: WorkQueueExecuteInput,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> WorkQueueActionResultOut:
    if source_type == "task":
        return _execute_task(
            db,
            task_id=source_id,
            current_user=current_user,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    if source_type == "assessment_queue":
        return _execute_assessment_queue_item(
            db,
            member_id=source_id,
            current_user=current_user,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    if source_type == "ai_service_agent":
        return _execute_ai_service_agent(
            db,
            action_id=source_id,
            current_user=current_user,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    if source_type == "student_personal_ai":
        return _execute_student_personal_ai(
            db,
            action_id=source_id,
            current_user=current_user,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    return _execute_ai_triage(
        db,
        recommendation_id=source_id,
        current_user=current_user,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def send_and_wait_work_queue_item(
    db: Session,
    *,
    current_user: User,
    source_type: SourceType,
    source_id: UUID,
    payload: WorkQueueSendAndWaitInput,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> WorkQueueActionResultOut:
    if source_type != "task":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enviar e aguardar resposta esta disponivel apenas para tasks humanas nesta V1.",
        )
    task = db.scalar(
        select(Task)
        .options(joinedload(Task.member), joinedload(Task.lead))
        .where(Task.id == source_id, Task.deleted_at.is_(None))
    )
    if task is None or is_task_operationally_archived(task):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    _ensure_task_access(task, current_user)

    message = (payload.message or task.suggested_message or "").strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Mensagem obrigatoria para envio.")
    if not (task.member or task.lead):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Task sem aluno ou lead vinculado.")

    domain = _task_domain(task)
    channel_resolution = resolve_communication_channel(
        db,
        gym_id=current_user.gym_id,
        requested_channel=payload.channel or "auto",
    )
    effective_channel = channel_resolution.channel
    used_channel_fallback = channel_resolution.used_fallback
    if effective_channel == "kommo" and task.member is None:
        effective_channel = channel_resolution.fallback_channel
        used_channel_fallback = True
    if effective_channel == "manual":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Canal manual resolvido. Abra o contexto e registre o resultado sem envio monitorado.",
        )
    action_type = "kommo_operator_handoff" if effective_channel == "kommo" else "send_whatsapp"
    safety = check_autopilot_safety(
        db,
        gym_id=current_user.gym_id,
        domain=domain,
        policy_key=f"manual_send_and_wait_{domain}",
        action_type=action_type,
        member=task.member,
        lead=task.lead,
        message_text=message,
        require_auto_send=False,
        ignore_recent_human_activity=True,
    )
    if not safety.allowed and not safety.scheduled_for:
        extra = _task_extra(task)
        extra["autopilot_blocked_reason"] = ",".join(safety.reasons)
        task.extra_data = extra
        db.add(task)
        record_task_event(
            db,
            task=task,
            current_user=current_user,
            event_type="contact_attempt",
            note=payload.operator_note,
            contact_channel=effective_channel,
            metadata_json={
                "source": "work_queue_send_and_wait",
                "blocked_reasons": safety.reasons,
                "requested_channel": channel_resolution.requested_channel,
                "resolved_channel": effective_channel,
            },
            flush=False,
        )
        db.flush()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Envio bloqueado: " + ", ".join(safety.reasons))

    decision = AutopilotDecision(
        decision="auto_execute",
        domain=domain,
        policy_key=f"manual_send_and_wait_{domain}",
        action_type=action_type,
        template_key=payload.template_key,
        confidence=1.0,
        reason="Envio iniciado por operador via Work Queue.",
        next_timeout_hours=48,
        metadata={
            "human_initiated": True,
            "operator_user_id": str(current_user.id),
            "requested_channel": channel_resolution.requested_channel,
            "resolved_channel": effective_channel,
            "used_channel_fallback": used_channel_fallback,
            "fallback_channel": channel_resolution.fallback_channel,
            "task_title": task.title,
            "task_reason": task.description or task.title,
            "context_path": _task_context_path(task),
        },
    )
    action = create_autopilot_action(
        db,
        gym_id=current_user.gym_id,
        decision=decision,
        member=task.member,
        lead=task.lead,
        related_task_id=task.id,
        message_body=message,
        idempotency_key=f"send-and-wait:{effective_channel}:{task.id}:{message[:80]}",
        flush=False,
    )
    if safety.scheduled_for:
        action.status = "scheduled"
        action.scheduled_for = safety.scheduled_for
        action.failure_reason = ",".join(safety.reasons)
        db.add(action)
    else:
        action = execute_autopilot_action(db, action, require_auto_send=False, flush=False)
    if effective_channel == "kommo" and action.status == "failed" and channel_resolution.fallback_channel == "whatsapp":
        effective_channel = "whatsapp"
        used_channel_fallback = True
        fallback_safety = check_autopilot_safety(
            db,
            gym_id=current_user.gym_id,
            domain=domain,
            policy_key=f"manual_send_and_wait_{domain}_fallback_whatsapp",
            action_type="send_whatsapp",
            member=task.member,
            lead=task.lead,
            message_text=message,
            require_auto_send=False,
            ignore_recent_human_activity=True,
        )
        if fallback_safety.allowed or fallback_safety.scheduled_for:
            fallback_decision = AutopilotDecision(
                decision="auto_execute",
                domain=domain,
                policy_key=f"manual_send_and_wait_{domain}_fallback_whatsapp",
                action_type="send_whatsapp",
                template_key=payload.template_key,
                confidence=1.0,
                reason="Fallback WhatsApp apos falha no handoff Kommo.",
                next_timeout_hours=48,
                metadata={
                    "human_initiated": True,
                    "operator_user_id": str(current_user.id),
                    "requested_channel": channel_resolution.requested_channel,
                    "resolved_channel": "whatsapp",
                    "used_channel_fallback": True,
                    "kommo_failure_reason": action.failure_reason,
                    "task_title": task.title,
                    "task_reason": task.description or task.title,
                    "context_path": _task_context_path(task),
                },
            )
            action = create_autopilot_action(
                db,
                gym_id=current_user.gym_id,
                decision=fallback_decision,
                member=task.member,
                lead=task.lead,
                related_task_id=task.id,
                message_body=message,
                idempotency_key=f"send-and-wait:fallback-whatsapp:{task.id}:{message[:80]}",
                flush=False,
            )
            if fallback_safety.scheduled_for:
                action.status = "scheduled"
                action.scheduled_for = fallback_safety.scheduled_for
                action.failure_reason = ",".join(fallback_safety.reasons)
                db.add(action)
            else:
                action = execute_autopilot_action(db, action, require_auto_send=False, flush=False)

    extra = _task_extra(task)
    extra["autopilot_action_id"] = str(action.id)
    extra["autopilot_state"] = action.status
    extra["work_queue_execution_channel"] = effective_channel
    extra["work_queue_channel_status"] = "awaiting_kommo" if effective_channel == "kommo" and action.status == "awaiting_outcome" else (
        "fallback_whatsapp" if used_channel_fallback and effective_channel == "whatsapp" else action.status
    )
    extra["work_queue_channel_action_label"] = "Enviar para Kommo" if effective_channel == "kommo" else "Enviar WhatsApp e aguardar"
    action_metadata = dict(action.metadata_json or {})
    if action_metadata.get("kommo_contact_id"):
        extra["kommo_contact_id"] = action_metadata.get("kommo_contact_id")
    if action_metadata.get("kommo_lead_id"):
        extra["kommo_lead_id"] = action_metadata.get("kommo_lead_id")
    if action.status == "awaiting_outcome":
        task.status = TaskStatus.DOING
        task.kanban_column = TaskStatus.DOING.value
        task.completed_at = None
        extra["autopilot_waiting_action_id"] = str(action.id)
    elif action.status == "scheduled":
        extra["autopilot_scheduled_for"] = action.scheduled_for.isoformat() if action.scheduled_for else None
    else:
        extra["autopilot_blocked_reason"] = action.failure_reason
    task.extra_data = extra
    db.add(task)
    record_task_event(
        db,
        task=task,
        current_user=current_user,
        event_type="contact_attempt",
        note=payload.operator_note,
        contact_channel=effective_channel,
        metadata_json={
            "source": "work_queue_send_and_wait",
            "autopilot_action_id": str(action.id),
            "action_status": action.status,
            "requested_channel": channel_resolution.requested_channel,
            "resolved_channel": effective_channel,
            "used_channel_fallback": used_channel_fallback,
            "ip_address": ip_address,
            "user_agent": user_agent,
        },
        flush=False,
    )
    db.flush()
    item = _task_to_item(task)
    if action.status == "awaiting_outcome":
        detail = (
            "Handoff criado na Kommo. A task ficou aguardando resposta na Kommo para o Autopilot resolver ou escalar."
            if effective_channel == "kommo"
            else "Mensagem enviada. A task ficou aguardando resposta para o Autopilot resolver ou escalar."
        )
    elif action.status == "scheduled":
        detail = "Mensagem agendada pelo Autopilot para o proximo horario permitido."
    else:
        detail = f"Mensagem nao enviada. Status da acao: {action.status}."
    return WorkQueueActionResultOut(
        item=item,
        detail=detail,
        prepared_message=message,
        context_path=item.context_path,
        task_id=task.id,
        supported=action.status in {"awaiting_outcome", "scheduled"},
    )


def _resolve_snooze_date(payload: WorkQueueOutcomeInput) -> datetime:
    if payload.scheduled_for:
        return payload.scheduled_for
    if payload.snooze_preset == "tomorrow":
        return _now() + timedelta(days=1)
    if payload.snooze_preset == "next_week":
        return _now() + timedelta(days=7)
    return _now() + timedelta(days=2)


def _task_event_type_for_outcome(outcome: WorkQueueOutcome) -> str:
    if outcome in {"postponed", "no_response", "payment_promised"}:
        return "snoozed"
    if outcome in {
        "training_delivered",
        "training_missing",
        "training_adjusted",
        "feedback_positive",
        "needs_training_adjustment",
        "reassessment_scheduled",
    }:
        return "outcome_recorded"
    if outcome in {"forwarded_to_trainer", "forwarded_to_reception", "forwarded_to_manager", "charge_disputed"}:
        return "forwarded"
    return "outcome_recorded"


def _apply_task_outcome(task: Task, payload: WorkQueueOutcomeInput, current_user: User) -> datetime | None:
    outcome = payload.outcome
    note = payload.note
    scheduled_for: datetime | None = None
    extra = _task_extra(task)
    now = _now()
    extra.update(
        {
            "work_queue_outcome": outcome,
            "work_queue_outcome_note": note,
            "work_queue_outcome_recorded_at": now.isoformat(),
            "work_queue_outcome_recorded_by_user_id": str(current_user.id),
            "work_queue_contact_channel": payload.contact_channel,
        }
    )
    if outcome in FINAL_TASK_OUTCOMES:
        task.status = TaskStatus.DONE
        task.kanban_column = TaskStatus.DONE.value
        task.completed_at = now
    elif outcome == "training_missing":
        scheduled_for = payload.scheduled_for or (now + timedelta(days=1))
        task.status = TaskStatus.TODO
        task.kanban_column = TaskStatus.TODO.value
        task.priority = TaskPriority.HIGH
        task.due_date = scheduled_for
        task.completed_at = None
        extra["owner_role"] = "coach"
        extra["domain"] = "trainer"
        extra["technical_followup_required"] = True
        extra["work_queue_snoozed_until"] = scheduled_for.isoformat()
    elif outcome in {"postponed", "no_response", "payment_promised"}:
        if _task_domain(task) == "retention" and outcome == "no_response":
            no_response_count = int(extra.get("retention_no_response_count") or 0) + 1
            extra["retention_no_response_count"] = no_response_count
            if no_response_count == 1:
                scheduled_for = now + timedelta(days=3)
            elif no_response_count == 2:
                scheduled_for = now + timedelta(days=7)
            else:
                scheduled_for = now + timedelta(days=30)
                extra["retention_stage"] = RETENTION_STAGE_COLD_BASE
                extra["retention_stage_label"] = "Base fria"
            extra["retention_cooldown_until"] = scheduled_for.isoformat()
        else:
            scheduled_for = _resolve_snooze_date(payload)
        task.status = TaskStatus.TODO
        task.kanban_column = TaskStatus.TODO.value
        task.due_date = scheduled_for
        task.completed_at = None
        extra["work_queue_snoozed_until"] = scheduled_for.isoformat()
        extra["work_queue_snooze_preset"] = payload.snooze_preset
        if outcome == "payment_promised":
            extra["owner_role"] = "reception"
    elif outcome in {"forwarded_to_trainer", "forwarded_to_reception", "forwarded_to_manager", "charge_disputed"}:
        task.status = TaskStatus.TODO
        task.kanban_column = TaskStatus.TODO.value
        task.completed_at = None
        if outcome == "forwarded_to_trainer":
            extra["work_queue_forwarded_to"] = "trainer"
            extra["owner_role"] = "coach"
            extra["domain"] = "trainer"
        elif outcome == "forwarded_to_reception":
            extra["work_queue_forwarded_to"] = "reception"
            extra["owner_role"] = "reception"
        else:
            extra["work_queue_forwarded_to"] = "manager"
            extra["owner_role"] = "manager"
    task.extra_data = extra
    return scheduled_for


def _ai_outcome_for_work_queue(outcome: WorkQueueOutcome) -> str:
    if outcome in POSITIVE_AI_OUTCOMES:
        return "positive"
    if outcome in NEUTRAL_AI_OUTCOMES:
        return "neutral"
    return "negative"


def update_work_queue_outcome(
    db: Session,
    *,
    current_user: User,
    source_type: SourceType,
    source_id: UUID,
    payload: WorkQueueOutcomeInput,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> WorkQueueActionResultOut:
    if source_type == "task":
        task = db.scalar(
            select(Task)
            .options(joinedload(Task.member), joinedload(Task.lead))
            .where(Task.id == source_id, Task.deleted_at.is_(None))
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
        if is_task_operationally_archived(task):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
        _ensure_task_access(task, current_user)
        scheduled_for = _apply_task_outcome(task, payload, current_user)
        db.add(task)
        record_task_event(
            db,
            task=task,
            current_user=current_user,
            event_type=_task_event_type_for_outcome(payload.outcome),
            outcome=payload.outcome,
            note=payload.note,
            scheduled_for=scheduled_for,
            contact_channel=payload.contact_channel,
            metadata_json={
                "source": "work_queue",
                "snooze_preset": payload.snooze_preset,
            },
            flush=False,
        )
        log_audit_event(
            db,
            action="work_queue_task_outcome_updated",
            entity="task",
            user=current_user,
            member_id=task.member_id,
            entity_id=task.id,
            details={
                "outcome": payload.outcome,
                "note": payload.note,
                "status": task.status.value,
                "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
                "contact_channel": payload.contact_channel,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            flush=False,
        )
        handle_task_outcome_for_journey(
            db,
            task=task,
            outcome=payload.outcome,
            current_user=current_user,
            note=payload.note,
        )
        db.flush()
        item = _task_to_item(task)
        return WorkQueueActionResultOut(
            item=item,
            detail="Resultado registrado na task.",
            prepared_message=task.suggested_message,
            context_path=item.context_path,
            task_id=task.id,
        )

    if source_type == "assessment_queue":
        if current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER, RoleEnum.RECEPTIONIST}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
        current_item = _member_assessment_queue_item(db, member_id=source_id, current_user=current_user)
        _ensure_assessment_queue_access(current_item, current_user)
        if payload.outcome == "scheduled_assessment":
            resolution_status = "scheduled"
            detail = "Avaliacao marcada e removida da fila operacional."
        elif payload.outcome in {"postponed", "no_response"}:
            resolution_status = "active"
            detail = "Resultado registrado. A pendencia continua ativa para acompanhamento."
        elif payload.outcome in {"completed", "will_return"}:
            resolution_status = "scheduled"
            detail = "Acompanhamento registrado e pendencia tecnica marcada como encaminhada."
        else:
            resolution_status = "dismissed"
            detail = "Pendencia tecnica retirada da fila operacional."
        update_assessment_queue_resolution(
            db,
            source_id,
            resolution_status=resolution_status,
            note=payload.note,
            resolved_by_user_id=current_user.id,
            gym_id=current_user.gym_id,
            commit=False,
        )
        log_audit_event(
            db,
            action="work_queue_assessment_queue_outcome_updated",
            entity="assessment_queue",
            user=current_user,
            member_id=source_id,
            entity_id=source_id,
            details={
                "outcome": payload.outcome,
                "resolution_status": resolution_status,
                "note": payload.note,
                "contact_channel": payload.contact_channel,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            flush=False,
        )
        db.flush()
        item = _member_assessment_queue_item(db, member_id=source_id, current_user=current_user)
        return WorkQueueActionResultOut(
            item=item,
            detail=detail,
            prepared_message=item.suggested_message,
            context_path=item.context_path,
            task_id=None,
        )

    if source_type == "ai_service_agent":
        return _update_ai_service_agent_outcome(
            db,
            action_id=source_id,
            current_user=current_user,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    if source_type == "student_personal_ai":
        return _update_student_personal_ai_outcome(
            db,
            action_id=source_id,
            current_user=current_user,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    recommendation = update_ai_triage_recommendation_outcome(
        db,
        recommendation_id=source_id,
        gym_id=current_user.gym_id,
        outcome=_ai_outcome_for_work_queue(payload.outcome),
        note=payload.note,
        current_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    source = get_ai_triage_recommendation_or_404(db, recommendation_id=recommendation.id, gym_id=current_user.gym_id)
    item = _ai_to_item(source)
    return WorkQueueActionResultOut(
        item=item,
        detail="Resultado registrado na Central Cordex.",
        prepared_message=item.suggested_message,
        context_path=item.context_path,
        task_id=None,
    )
