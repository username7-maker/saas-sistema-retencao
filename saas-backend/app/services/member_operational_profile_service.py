from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import (
    AutopilotAction,
    AutopilotEvent,
    FinancialEntry,
    Lead,
    Member,
    MemberNote,
    MessageLog,
    Task,
    TaskEvent,
    TaskStatus,
    User,
)
from app.schemas.member_operational_profile import MemberNoteCreate
from app.services.member_intelligence_service import get_member_intelligence_context
from app.services.member_lifecycle_service import build_member_lifecycle_state
from app.services.member_next_best_action_service import build_member_next_best_action
from app.services.member_profile_permissions_service import build_member_profile_permissions, filter_member_note_for_role
from app.services.member_service import get_member_or_404
from app.services.member_timeline_service import get_member_timeline


def build_member_operational_profile(db: Session, *, member_id: UUID, current_user: User, limit: int = 12) -> dict:
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    permissions = build_member_profile_permissions(current_user)
    intelligence = get_member_intelligence_context(db, member_id, gym_id=current_user.gym_id)
    intelligence_payload = intelligence.model_dump(mode="json")

    open_tasks = _list_member_tasks(db, member=member, include_done=False, limit=25)
    notes = list_member_notes(db, member_id=member.id, current_user=current_user, limit=20)
    timeline_preview = _build_timeline_preview(db, member=member, permissions=permissions, limit=limit)
    financial_summary = _build_financial_summary(db, member, permissions)
    commercial_summary = _build_commercial_summary(db, member, permissions)
    autopilot_summary = _build_autopilot_summary(db, member, permissions)
    lifecycle = build_member_lifecycle_state(member)

    next_best_action = build_member_next_best_action(
        db,
        member=member,
        current_user=current_user,
        permissions=permissions,
        open_tasks=open_tasks,
    )

    return {
        "generated_at": datetime.now(tz=timezone.utc),
        "member": _serialize_member(member, permissions, lifecycle),
        "permissions": permissions,
        "summary": _build_summary(member, intelligence_payload, financial_summary, autopilot_summary, lifecycle),
        "lifecycle": lifecycle,
        "risk": intelligence_payload.get("risk") or {},
        "activity": intelligence_payload.get("activity") or {},
        "assessment": intelligence_payload.get("assessment") or {},
        "financial": financial_summary if permissions.get("can_view_financial") else None,
        "commercial": commercial_summary if permissions.get("can_view_commercial") else None,
        "communication": _build_communication_summary(intelligence_payload, timeline_preview),
        "tasks": _build_task_summary(open_tasks),
        "autopilot": autopilot_summary,
        "next_best_action": next_best_action,
        "signals": _role_filter_signals(intelligence_payload.get("signals") or [], permissions),
        "timeline_preview": timeline_preview,
        "data_quality_flags": intelligence_payload.get("data_quality_flags") or [],
        "notes": notes,
    }


def list_member_notes(db: Session, *, member_id: UUID, current_user: User, limit: int = 50) -> list[MemberNote]:
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    permissions = build_member_profile_permissions(current_user)
    rows = db.scalars(
        select(MemberNote)
        .where(
            MemberNote.gym_id == current_user.gym_id,
            MemberNote.member_id == member.id,
            MemberNote.deleted_at.is_(None),
        )
        .order_by(desc(MemberNote.created_at))
        .limit(limit)
    ).all()
    return [
        note
        for note in rows
        if filter_member_note_for_role(note.note_type, note.visibility, permissions)
    ]


def create_member_note(db: Session, *, member_id: UUID, current_user: User, payload: MemberNoteCreate) -> MemberNote:
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    permissions = build_member_profile_permissions(current_user)
    if not permissions.get("can_create_notes"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissao insuficiente para criar nota")
    if not filter_member_note_for_role(payload.note_type, payload.visibility, permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Visibilidade de nota nao permitida para este perfil")
    note = MemberNote(
        gym_id=current_user.gym_id,
        member_id=member.id,
        author_user_id=current_user.id,
        note_type=payload.note_type,
        body=payload.body.strip(),
        visibility=payload.visibility,
        extra_data=payload.extra_data,
    )
    db.add(note)
    db.flush()
    db.refresh(note)
    return note


def _serialize_member(member: Member, permissions: dict, lifecycle: dict) -> dict:
    payload = {
        "id": str(member.id),
        "full_name": member.full_name,
        "status": _enum_value(member.status),
        "plan_name": member.plan_name,
        "join_date": member.join_date,
        "preferred_shift": member.preferred_shift,
        "risk_score": member.risk_score,
        "risk_level": _enum_value(member.risk_level),
        "last_checkin_at": member.last_checkin_at,
        "onboarding_score": member.onboarding_score,
        "onboarding_status": member.onboarding_status,
        "retention_stage": member.retention_stage,
        "is_vip": member.is_vip,
        "lifecycle_stage": lifecycle.get("lifecycle_stage"),
        "lifecycle_label": lifecycle.get("lifecycle_label"),
        "operational_lane": lifecycle.get("operational_lane"),
        "recommended_owner_role": lifecycle.get("recommended_owner_role"),
        "lifecycle_priority": lifecycle.get("lifecycle_priority"),
    }
    if permissions.get("can_view_contact"):
        payload.update({"email": member.email, "phone": member.phone})
    if permissions.get("can_view_financial"):
        payload["monthly_fee"] = float(member.monthly_fee or 0)
    return payload


def _build_summary(member: Member, intelligence: dict, financial: dict | None, autopilot: dict, lifecycle: dict) -> dict:
    activity = intelligence.get("activity") or {}
    operations = intelligence.get("operations") or {}
    return {
        "status_label": _enum_value(member.status),
        "risk_label": _enum_value(member.risk_level),
        "days_without_checkin": activity.get("days_without_checkin"),
        "checkins_30d": activity.get("checkins_30d"),
        "open_tasks_total": operations.get("open_tasks_total", 0),
        "overdue_tasks_total": operations.get("overdue_tasks_total", 0),
        "financial_open_amount": (financial or {}).get("open_amount"),
        "autopilot_state": autopilot.get("state"),
        "lifecycle_label": lifecycle.get("lifecycle_label"),
        "next_focus": lifecycle.get("next_focus"),
        "last_interaction_at": _latest_timestamp_from_summary(financial, autopilot),
    }


def _build_financial_summary(db: Session, member: Member, permissions: dict) -> dict | None:
    if not permissions.get("can_view_financial"):
        return None
    rows = db.scalars(
        select(FinancialEntry).where(
            FinancialEntry.gym_id == member.gym_id,
            FinancialEntry.member_id == member.id,
            FinancialEntry.entry_type == "receivable",
        )
    ).all()
    open_rows = [row for row in rows if row.status in {"open", "overdue"}]
    paid_rows = [row for row in rows if row.status == "paid"]
    return {
        "open_total": len(open_rows),
        "open_amount": float(sum(row.amount or 0 for row in open_rows)),
        "paid_total": len(paid_rows),
        "latest_paid_at": max((row.paid_at for row in paid_rows if row.paid_at), default=None),
        "latest_due_date": max((row.due_date for row in rows if row.due_date), default=None),
    }


def _build_commercial_summary(db: Session, member: Member, permissions: dict) -> dict | None:
    if not permissions.get("can_view_commercial"):
        return None
    lead = db.scalar(
        select(Lead)
        .where(Lead.gym_id == member.gym_id, Lead.converted_member_id == member.id, Lead.deleted_at.is_(None))
        .order_by(desc(Lead.updated_at))
        .limit(1)
    )
    if not lead:
        return {"has_lead_origin": False}
    return {
        "has_lead_origin": True,
        "lead_id": str(lead.id),
        "source": lead.source,
        "stage": _enum_value(lead.stage),
        "last_contact_at": lead.last_contact_at,
        "owner_id": str(lead.owner_id) if lead.owner_id else None,
    }


def _build_communication_summary(intelligence: dict, timeline: list[dict]) -> dict:
    consent = intelligence.get("consent") or {}
    latest_message = next((item for item in timeline if item.get("source") == "message"), None)
    return {
        "consent": consent,
        "latest_message": latest_message,
        "can_contact_whatsapp": bool(consent.get("whatsapp") or consent.get("communication") or consent.get("marketing")),
    }


def _build_autopilot_summary(db: Session, member: Member, permissions: dict) -> dict:
    if not permissions.get("can_use_autopilot"):
        return {"state": "hidden", "actions_open_total": 0, "latest_action": None}
    actions = db.scalars(
        select(AutopilotAction)
        .where(AutopilotAction.gym_id == member.gym_id, AutopilotAction.member_id == member.id)
        .order_by(desc(AutopilotAction.created_at))
        .limit(10)
    ).all()
    open_statuses = {"planned", "scheduled", "executing", "sent", "awaiting_outcome"}
    latest = actions[0] if actions else None
    state = "not_started"
    if latest:
        state = latest.status
    return {
        "state": state,
        "actions_open_total": sum(1 for action in actions if action.status in open_statuses),
        "latest_action": _serialize_autopilot_action(latest) if latest else None,
    }


def _build_task_summary(open_tasks: list[Task]) -> dict:
    by_domain: dict[str, int] = {}
    items: list[dict] = []
    for task in open_tasks:
        extra = task.extra_data or {}
        domain = str(extra.get("domain") or extra.get("source") or "manual")
        by_domain[domain] = by_domain.get(domain, 0) + 1
        items.append(_serialize_task(task))
    return {
        "open_total": len(open_tasks),
        "by_domain": by_domain,
        "top_open": items[:8],
    }


def _list_member_tasks(db: Session, *, member: Member, include_done: bool, limit: int) -> list[Task]:
    filters = [Task.gym_id == member.gym_id, Task.member_id == member.id]
    if not include_done:
        filters.append(Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]))
    return list(
        db.scalars(
            select(Task)
            .where(*filters)
            .order_by(Task.due_date.asc().nullslast(), desc(Task.created_at))
            .limit(limit)
        ).all()
    )


def _build_timeline_preview(db: Session, *, member: Member, permissions: dict, limit: int) -> list[dict]:
    items: list[dict] = []
    if permissions.get("can_view_clinical") or permissions.get("can_view_internal_notes"):
        items.extend(get_member_timeline(db, member.id, limit=limit))

    messages = db.scalars(
        select(MessageLog)
        .where(MessageLog.gym_id == member.gym_id, MessageLog.member_id == member.id)
        .order_by(desc(MessageLog.created_at))
        .limit(8)
    ).all()
    items.extend(_serialize_message(row) for row in messages)

    task_events = db.scalars(
        select(TaskEvent)
        .where(TaskEvent.gym_id == member.gym_id, TaskEvent.member_id == member.id)
        .order_by(desc(TaskEvent.created_at))
        .limit(8)
    ).all()
    items.extend(_serialize_task_event(row) for row in task_events)

    autopilot_events = db.scalars(
        select(AutopilotEvent)
        .where(AutopilotEvent.gym_id == member.gym_id, AutopilotEvent.member_id == member.id)
        .order_by(desc(AutopilotEvent.created_at))
        .limit(8)
    ).all()
    items.extend(_serialize_autopilot_event(row) for row in autopilot_events)

    if permissions.get("can_view_financial"):
        financial_events = db.scalars(
            select(FinancialEntry)
            .where(FinancialEntry.gym_id == member.gym_id, FinancialEntry.member_id == member.id)
            .order_by(desc(func.coalesce(FinancialEntry.paid_at, FinancialEntry.occurred_at, FinancialEntry.created_at)))
            .limit(6)
        ).all()
        items.extend(_serialize_financial_event(row) for row in financial_events)

    return sorted(items, key=_timeline_sort_key, reverse=True)[:limit]


def _role_filter_signals(signals: list[dict], permissions: dict) -> list[dict]:
    if permissions.get("can_view_financial") and permissions.get("can_view_clinical"):
        return signals
    blocked_sources = set()
    if not permissions.get("can_view_financial"):
        blocked_sources.add("finance")
    if not permissions.get("can_view_clinical"):
        blocked_sources.update({"assessment", "body_composition", "constraints"})
    return [signal for signal in signals if signal.get("source") not in blocked_sources]


def _serialize_task(task: Task) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "priority": _enum_value(task.priority),
        "status": _enum_value(task.status),
        "due_date": task.due_date,
        "source": (task.extra_data or {}).get("source"),
        "domain": (task.extra_data or {}).get("domain"),
    }


def _serialize_message(row: MessageLog) -> dict:
    return {
        "id": str(row.id),
        "source": "message",
        "type": row.event_type or row.direction or "message",
        "title": "Mensagem recebida" if row.direction == "inbound" else "Mensagem enviada",
        "description": row.content[:180],
        "channel": row.channel,
        "status": row.status,
        "occurred_at": row.created_at,
    }


def _serialize_task_event(row: TaskEvent) -> dict:
    return {
        "id": str(row.id),
        "source": "task_event",
        "type": row.event_type,
        "title": _task_event_title(row),
        "description": row.note or row.outcome,
        "occurred_at": row.created_at,
        "task_id": str(row.task_id),
    }


def _serialize_autopilot_event(row: AutopilotEvent) -> dict:
    return {
        "id": str(row.id),
        "source": "autopilot",
        "type": row.event_type,
        "title": f"Autopilot: {row.event_type}",
        "description": (row.metadata_json or {}).get("reason") or (row.metadata_json or {}).get("text"),
        "occurred_at": row.occurred_at or row.created_at,
        "status": row.processing_status,
    }


def _serialize_autopilot_action(row: AutopilotAction | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": str(row.id),
        "policy_key": row.policy_key,
        "domain": row.domain,
        "action_type": row.action_type,
        "status": row.status,
        "channel": row.channel,
        "template_key": row.template_key,
        "timeout_at": row.timeout_at,
        "created_at": row.created_at,
    }


def _serialize_financial_event(row: FinancialEntry) -> dict:
    return {
        "id": str(row.id),
        "source": "finance",
        "type": row.status,
        "title": "Pagamento confirmado" if row.status == "paid" else "Lancamento financeiro",
        "description": row.description or row.category,
        "amount": float(row.amount or 0),
        "occurred_at": row.paid_at or row.occurred_at or row.created_at,
    }


def _task_event_title(row: TaskEvent) -> str:
    labels = {
        "comment": "Comentario registrado",
        "execution_started": "Execucao iniciada",
        "contact_attempt": "Tentativa de contato",
        "outcome_recorded": "Resultado registrado",
        "snoozed": "Tarefa adiada",
        "status_changed": "Status alterado",
        "reassigned": "Responsavel alterado",
        "forwarded": "Encaminhado",
    }
    return labels.get(row.event_type, row.event_type)


def _latest_timestamp_from_summary(financial: dict | None, autopilot: dict) -> datetime | None:
    latest_action = autopilot.get("latest_action") if autopilot else None
    candidates = [
        (financial or {}).get("latest_paid_at"),
        latest_action.get("created_at") if latest_action else None,
    ]
    return max((value for value in candidates if value), default=None)


def _enum_value(value) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _timeline_sort_key(item: dict) -> datetime:
    value = item.get("occurred_at") or item.get("created_at")
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.min.replace(tzinfo=timezone.utc)
