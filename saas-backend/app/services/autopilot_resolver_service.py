from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutopilotAction, AutopilotEvent, FinancialEntry, Lead, LeadStage, Member, Task, TaskStatus
from app.services.autopilot_action_service import (
    escalate_autopilot_action_to_human,
    mark_autopilot_action_succeeded,
    mark_autopilot_action_timed_out,
)
from app.services.autopilot_event_service import mark_event_processed, record_event
from app.services.autopilot_safety_service import contains_sensitive_text
from app.services.human_escalation_service import escalate_to_human_task
from app.services.task_event_service import record_task_event


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _task_extra(task: Task) -> dict:
    return dict(task.extra_data or {}) if isinstance(task.extra_data, dict) else {}


def _task_domain_filter(domain: str):
    return Task.extra_data["domain"].astext == domain


def _open_tasks_for_subject(db: Session, *, event: AutopilotEvent, domain: str | None = None) -> list[Task]:
    filters = [
        Task.gym_id == event.gym_id,
        Task.deleted_at.is_(None),
        Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
    ]
    if event.member_id:
        filters.append(Task.member_id == event.member_id)
    elif event.lead_id:
        filters.append(Task.lead_id == event.lead_id)
    else:
        return []
    if domain:
        filters.append(_task_domain_filter(domain))
    return list(db.scalars(select(Task).where(*filters).limit(20)).all())


def _awaiting_actions_for_subject(db: Session, event: AutopilotEvent, *, domain: str | None = None) -> list[AutopilotAction]:
    filters = [
        AutopilotAction.gym_id == event.gym_id,
        AutopilotAction.status.in_(["awaiting_outcome", "sent", "scheduled", "planned"]),
    ]
    if event.member_id:
        filters.append(AutopilotAction.member_id == event.member_id)
    elif event.lead_id:
        filters.append(AutopilotAction.lead_id == event.lead_id)
    else:
        return []
    if domain:
        filters.append(AutopilotAction.domain == domain)
    return list(db.scalars(select(AutopilotAction).where(*filters).limit(20)).all())


def _auto_close_task(db: Session, task: Task, *, outcome: str, note: str, event: AutopilotEvent) -> None:
    extra = _task_extra(task)
    extra.update(
        {
            "work_queue_outcome": outcome,
            "autopilot_auto_closed_at": _now().isoformat(),
            "autopilot_auto_closed_event_id": str(event.id),
            "autopilot_auto_close_reason": note,
        }
    )
    task.status = TaskStatus.DONE
    task.kanban_column = TaskStatus.DONE.value
    task.completed_at = _now()
    task.extra_data = extra
    db.add(task)
    record_task_event(
        db,
        task=task,
        current_user=None,
        event_type="outcome_recorded",
        outcome=outcome,
        note=note,
        metadata_json={"source": "autopilot", "autopilot_event_id": str(event.id), "event_type": event.event_type},
        flush=False,
    )


def _resolve_success(db: Session, event: AutopilotEvent, *, domain: str, outcome: str, note: str) -> int:
    resolved = 0
    for action in _awaiting_actions_for_subject(db, event, domain=domain):
        mark_autopilot_action_succeeded(db, action, outcome=outcome, metadata={"autopilot_event_id": str(event.id)}, flush=False)
        resolved += 1
    for task in _open_tasks_for_subject(db, event=event, domain=domain):
        _auto_close_task(db, task, outcome=outcome, note=note, event=event)
        resolved += 1
    return resolved


def resolve_event(db: Session, event: AutopilotEvent, *, flush: bool = True) -> dict:
    if event.processing_status == "processed":
        return {"processed": False, "detail": "Evento ja processado"}
    try:
        result = _resolve_event_inner(db, event)
        mark_event_processed(db, event, status="processed")
        if flush:
            db.flush()
        return result
    except Exception as exc:
        mark_event_processed(db, event, status="failed", error=str(exc)[:500])
        if flush:
            db.flush()
        raise


def _resolve_event_inner(db: Session, event: AutopilotEvent) -> dict:
    metadata = dict(event.metadata_json or {})
    if event.event_type == "whatsapp_inbound_received":
        text = str(metadata.get("message_text") or metadata.get("text") or "")
        if contains_sensitive_text(text):
            member = db.get(Member, event.member_id) if event.member_id else None
            lead = db.get(Lead, event.lead_id) if event.lead_id else None
            for action in _awaiting_actions_for_subject(db, event):
                escalate_autopilot_action_to_human(db, action, reason="sensitive_inbound_message", flush=False)
            task = escalate_to_human_task(
                db,
                gym_id=event.gym_id,
                domain="support" if event.member_id else "commercial",
                reason=f"Resposta sensivel recebida: {text[:280]}",
                member=member,
                lead=lead,
                priority="urgent",
                owner_role="manager",
                suggested_action="Intervencao humana obrigatoria",
                metadata={"autopilot_event_id": str(event.id)},
                flush=False,
            )
            return {"processed": True, "detail": "Resposta sensivel escalada", "task_id": str(task.id)}
        resolved = 0
        resolved += _resolve_success(db, event, domain="retention", outcome="responded", note="Fechada automaticamente porque o aluno respondeu no WhatsApp.")
        resolved += _resolve_success(db, event, domain="finance", outcome="responded", note="Resposta recebida; cobrança deixa de ficar como tentativa pendente.")
        resolved += _resolve_success(db, event, domain="commercial", outcome="responded", note="Lead respondeu no WhatsApp; follow-up automatico foi resolvido.")
        return {"processed": True, "resolved_count": resolved}

    if event.event_type == "member_checkin_created":
        resolved = _resolve_success(db, event, domain="retention", outcome="completed", note="Fechada automaticamente porque o aluno fez check-in.")
        return {"processed": True, "resolved_count": resolved}

    if event.event_type == "member_payment_confirmed":
        resolved = _resolve_success(db, event, domain="finance", outcome="payment_confirmed", note="Fechada automaticamente porque o pagamento foi confirmado.")
        return {"processed": True, "resolved_count": resolved}

    if event.event_type in {"member_assessment_scheduled", "member_assessment_completed"}:
        outcome = "scheduled_assessment" if event.event_type.endswith("scheduled") else "completed"
        note = "Fechada automaticamente porque a avaliacao foi agendada." if outcome == "scheduled_assessment" else "Fechada automaticamente porque a avaliacao foi concluida."
        resolved = _resolve_success(db, event, domain="assessment", outcome=outcome, note=note)
        return {"processed": True, "resolved_count": resolved}

    if event.event_type in {"lead_won", "lead_lost"}:
        outcome = "completed" if event.event_type == "lead_won" else "not_interested"
        note = "Fechada automaticamente porque o lead mudou para etapa final."
        resolved = _resolve_success(db, event, domain="commercial", outcome=outcome, note=note)
        return {"processed": True, "resolved_count": resolved}

    return {"processed": True, "detail": "Evento sem resolver V1"}


def resolve_timeout(db: Session, action: AutopilotAction) -> dict:
    if action.status != "awaiting_outcome":
        return {"processed": False, "detail": "Action nao aguarda outcome"}
    mark_autopilot_action_timed_out(db, action, flush=False)
    member = db.get(Member, action.member_id) if action.member_id else None
    lead = db.get(Lead, action.lead_id) if action.lead_id else None
    task = escalate_to_human_task(
        db,
        gym_id=action.gym_id,
        domain=action.domain,
        reason=f"Autopilot sem retorno apos timeout da policy {action.policy_key}.",
        member=member,
        lead=lead,
        action=action,
        priority="high" if action.domain in {"retention", "finance"} else "medium",
        owner_role="reception" if action.domain in {"retention", "finance"} else "salesperson",
        suggested_action="Resolver excecao do Autopilot",
        metadata={"timeout_at": action.timeout_at.isoformat() if action.timeout_at else None},
        flush=False,
    )
    return {"processed": True, "task_id": str(task.id)}


def register_financial_payment_event(db: Session, entry: FinancialEntry, *, flush: bool = True) -> AutopilotEvent | None:
    if entry.status != "paid" or not entry.member_id:
        return None
    event = record_event(
        db,
        gym_id=entry.gym_id,
        event_type="member_payment_confirmed",
        source="finance",
        member_id=entry.member_id,
        metadata={"financial_entry_id": str(entry.id), "amount": float(entry.amount)},
        deduplication_key=f"finance:payment_confirmed:{entry.id}:{entry.paid_at or entry.updated_at}",
        flush=flush,
    )
    resolve_event(db, event)
    return event


def register_lead_stage_event(db: Session, lead: Lead, *, previous_stage: LeadStage | None, flush: bool = True) -> AutopilotEvent | None:
    if previous_stage == lead.stage:
        return None
    event_type = "lead_stage_changed"
    if lead.stage == LeadStage.WON:
        event_type = "lead_won"
    elif lead.stage == LeadStage.LOST:
        event_type = "lead_lost"
    event = record_event(
        db,
        gym_id=lead.gym_id,
        event_type=event_type,
        source="crm",
        lead_id=lead.id,
        metadata={"previous_stage": previous_stage.value if previous_stage else None, "stage": lead.stage.value},
        deduplication_key=f"crm:{event_type}:{lead.id}:{lead.updated_at}",
        flush=flush,
    )
    resolve_event(db, event)
    return event
