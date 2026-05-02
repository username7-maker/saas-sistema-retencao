from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import AITriageRecommendation, RoleEnum, Task, TaskStatus, User
from app.schemas import PaginatedResponse
from app.schemas.ai_triage import AITriageSafeActionPrepareInput
from app.schemas.work_queue import (
    WorkQueueActionResultOut,
    WorkQueueExecuteInput,
    WorkQueueItemOut,
    WorkQueueOutcome,
    WorkQueueOutcomeInput,
)
from app.services.ai_triage_service import (
    get_ai_triage_recommendation_or_404,
    prepare_ai_triage_recommendation_action,
    serialize_ai_triage_recommendation,
    sync_ai_triage_recommendations,
    update_ai_triage_recommendation_outcome,
)
from app.services.audit_service import log_audit_event
from app.services.automation_journey_service import handle_task_outcome_for_journey
from app.services.preferred_shift_service import normalize_preferred_shift
from app.services.retention_stage_service import (
    RETENTION_STAGE_COLD_BASE,
    is_cold_base_stage,
    retention_stage_payload,
)
from app.services.task_event_service import record_task_event
from app.services.task_service import is_task_operationally_archived

SourceType = Literal["task", "ai_triage"]
StateFilter = Literal["do_now", "awaiting_outcome", "done", "all"]
ShiftFilter = Literal["my_shift", "all", "overnight", "morning", "afternoon", "evening", "unassigned"]
AssigneeFilter = Literal["mine", "unassigned", "all"]
DomainFilter = Literal["all", "retention", "onboarding", "assessment", "commercial", "finance", "manual"]
SourceFilter = Literal["all", "task", "ai_triage"]

FINAL_TASK_OUTCOMES = {
    "responded",
    "scheduled_assessment",
    "will_return",
    "not_interested",
    "invalid_number",
    "payment_confirmed",
    "payment_link_sent",
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
    return task.lead_id is None and extra.get("source") == "assessment_intelligence" and extra.get("owner_role") == "coach"


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


def _task_action_label(task: Task) -> str:
    source = str(_task_extra(task).get("source") or "").lower()
    extra = _task_extra(task)
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
        assigned_to_user_id=task.assigned_to_user_id,
        context_path=_task_context_path(task),
        outcome_state=str(_task_extra(task).get("work_queue_outcome") or ("completed" if task.status == TaskStatus.DONE else "pending")),
        retention_stage=retention_payload.get("retention_stage"),
        retention_stage_label=retention_payload.get("retention_stage_label"),
        retention_stage_priority=int(retention_payload.get("retention_stage_priority") or 0),
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
    target = normalize_preferred_shift(current_user.work_shift) if effective_shift == "my_shift" else normalize_preferred_shift(effective_shift)
    if not target:
        return True
    if item.preferred_shift is None:
        return True
    return normalize_preferred_shift(item.preferred_shift) == target


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
    for item in items:
        if state != "all" and item.state != state:
            continue
        if domain != "all" and item.domain != domain:
            continue
        if state == "do_now" and item.domain == "retention" and is_cold_base_stage(item.retention_stage):
            continue
        if not _matches_shift(item, current_user, shift):
            continue
        if not _matches_assignee(item, current_user, assignee):
            continue
        filtered.append(item)
    now = _now()
    return sorted(filtered, key=lambda item: _work_item_score(item, now), reverse=True)


def _list_task_items(db: Session, current_user: User) -> list[WorkQueueItemOut]:
    filters = [Task.gym_id == current_user.gym_id, Task.deleted_at.is_(None)]
    filters.append(func.coalesce(Task.extra_data["operational_archive"]["archived_at"].astext, "") == "")
    if current_user.role == RoleEnum.TRAINER:
        filters.extend(
            [
                Task.lead_id.is_(None),
                Task.extra_data["source"].astext == "assessment_intelligence",
                Task.extra_data["owner_role"].astext == "coach",
            ]
        )
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
    if source in {"all", "ai_triage"}:
        items.extend(_list_ai_items(db, current_user))

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

    recommendation = get_ai_triage_recommendation_or_404(db, recommendation_id=source_id, gym_id=current_user.gym_id)
    if current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item nao encontrado")
    return _ai_to_item(recommendation)


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
    return _execute_ai_triage(
        db,
        recommendation_id=source_id,
        current_user=current_user,
        payload=payload,
        ip_address=ip_address,
        user_agent=user_agent,
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
        detail="Resultado registrado na AI Inbox.",
        prepared_message=item.suggested_message,
        context_path=item.context_path,
        task_id=None,
    )
