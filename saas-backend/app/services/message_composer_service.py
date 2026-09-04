from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import GymMessageTemplateOverride, Lead, Member, MessageCompositionRequest, Task, User
from app.services.ai_prompt_registry_service import AiInvocationContext
from app.services.audit_service import log_audit_event
from app.services.message_template_service import (
    effective_template,
    ensure_domain_permission,
    get_template_definition,
    render_message,
)
from app.services.operational_message_ai_service import generate_operational_message_draft


def list_templates(db: Session, user: User) -> list[dict]:
    from app.services.message_template_service import ROLE_DOMAINS, TEMPLATES

    allowed = ROLE_DOMAINS.get(user.role, set())
    overrides = {
        item.template_key: item
        for item in db.scalars(
            select(GymMessageTemplateOverride).where(
                GymMessageTemplateOverride.gym_id == user.gym_id,
                GymMessageTemplateOverride.is_active.is_(True),
            )
        ).all()
    }
    result = []
    for definition in TEMPLATES.values():
        if definition.domain not in allowed:
            continue
        override = overrides.get(definition.key)
        result.append(
            {
                "key": definition.key,
                "domain": definition.domain,
                "channel": definition.channel,
                "objective": definition.objective,
                "content": override.content if override else definition.content,
                "default_content": definition.content,
                "allowed_variables": list(definition.allowed_variables),
                "required_variables": list(definition.required_variables),
                "version": definition.version,
                "active": definition.active,
                "origin": "template_gym_override" if override else "template_default",
            }
        )
    return result


def get_metrics(db: Session, user: User) -> dict[str, int | float]:
    row = db.execute(
        select(
            func.count(MessageCompositionRequest.id),
            func.sum(case((MessageCompositionRequest.status == "applied", 1), else_=0)),
            func.sum(case((MessageCompositionRequest.status == "discarded", 1), else_=0)),
            func.sum(case((MessageCompositionRequest.status == "previewed", 1), else_=0)),
            func.sum(case((MessageCompositionRequest.fallback_used.is_(True), 1), else_=0)),
            func.coalesce(func.sum(MessageCompositionRequest.input_tokens), 0),
            func.coalesce(func.sum(MessageCompositionRequest.output_tokens), 0),
        ).where(MessageCompositionRequest.gym_id == user.gym_id)
    ).one()
    requests, applied, discarded, pending, fallback, input_tokens, output_tokens = [int(value or 0) for value in row]
    return {
        "requests": requests,
        "applied": applied,
        "discarded": discarded,
        "pending_preview": pending,
        "fallback_count": fallback,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "application_rate": round((applied / requests) * 100, 2) if requests else 0.0,
    }


def improve_message(
    db: Session,
    *,
    user: User,
    source_type: str,
    source_id: UUID | None,
    template_key: str,
    objective: str,
    idempotency_key: str,
) -> MessageCompositionRequest:
    definition = get_template_definition(template_key)
    ensure_domain_permission(user, definition.domain)
    existing = db.scalar(
        select(MessageCompositionRequest).where(
            MessageCompositionRequest.gym_id == user.gym_id,
            MessageCompositionRequest.idempotency_key == idempotency_key,
        )
    )
    if existing:
        return existing

    member, lead, task = _load_source(db, gym_id=user.gym_id, source_type=source_type, source_id=source_id)
    variables = _safe_variables(member=member, lead=lead, task=task)
    _, content, _ = effective_template(db, user.gym_id, template_key)
    base_message = (
        (task.suggested_message if task else None) or render_message(definition, content, variables)
    ).strip()
    context = _minimal_context(member=member, lead=lead, task=task)
    context_hash = _hash_json(
        {"source_type": source_type, "source_id": str(source_id or ""), "objective": objective, "context": context}
    )
    recent = db.scalar(
        select(MessageCompositionRequest).where(
            MessageCompositionRequest.gym_id == user.gym_id,
            MessageCompositionRequest.requested_by_user_id == user.id,
            MessageCompositionRequest.source_type == source_type,
            MessageCompositionRequest.source_id == source_id,
            MessageCompositionRequest.template_key == template_key,
            MessageCompositionRequest.context_hash == context_hash,
            MessageCompositionRequest.base_hash == _hash_text(base_message),
            MessageCompositionRequest.created_at >= datetime.now(tz=UTC) - timedelta(minutes=5),
        )
    )
    if recent:
        return recent
    invocation = AiInvocationContext(
        explicit_user_action=True,
        gym_id=str(user.gym_id),
        user_id=str(user.id),
        objective=objective,
        source_type=source_type,
        source_id=str(source_id) if source_id else None,
        idempotency_key=idempotency_key,
    )
    draft = generate_operational_message_draft(
        db,
        domain=definition.domain,
        base_message=base_message,
        member=member,
        lead=lead,
        task=task,
        context={**context, "objective": objective},
        allow_ai=True,
        invocation_context=invocation,
    )
    metadata = draft.metadata
    improved = draft.message or base_message
    request = MessageCompositionRequest(
        gym_id=user.gym_id,
        requested_by_user_id=user.id,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        template_key=template_key,
        objective=objective,
        base_message=base_message,
        improved_message=improved,
        base_hash=_hash_text(base_message),
        improved_hash=_hash_text(improved),
        context_hash=context_hash,
        status="previewed",
        provider="system" if draft.fallback_used else "openai",
        model=metadata.get("model"),
        prompt_key=metadata.get("prompt_key"),
        prompt_version=metadata.get("prompt_version"),
        input_tokens=int(metadata.get("input_tokens") or 0),
        output_tokens=int(metadata.get("output_tokens") or 0),
        duration_ms=int(metadata.get("duration_ms") or 0),
        fallback_used=draft.fallback_used,
        warnings_json=list(
            draft.blocked_reasons
            or ([] if not draft.fallback_used else [metadata.get("ai_skipped_reason") or "ai_unavailable"])
        ),
    )
    db.add(request)
    db.flush()
    log_audit_event(
        db,
        "message_ai_improvement_requested",
        "message_composition_request",
        user=user,
        entity_id=request.id,
        details={
            "domain": definition.domain,
            "source_type": source_type,
            "template_key": template_key,
            "base_hash": request.base_hash,
            "improved_hash": request.improved_hash,
            "input_tokens": request.input_tokens,
            "output_tokens": request.output_tokens,
        },
    )
    db.commit()
    db.refresh(request)
    return request


def resolve_composition(db: Session, *, user: User, request_id: UUID, apply: bool) -> MessageCompositionRequest:
    request = db.scalar(
        select(MessageCompositionRequest).where(
            MessageCompositionRequest.id == request_id,
            MessageCompositionRequest.gym_id == user.gym_id,
        )
    )
    if not request:
        raise LookupError("Solicitação de melhoria não encontrada")
    definition = get_template_definition(request.template_key)
    ensure_domain_permission(user, definition.domain)
    if request.status not in {"previewed", "applied", "discarded"}:
        raise ValueError("Estado da solicitação inválido")
    if apply and request.source_type == "task" and request.source_id:
        task = db.scalar(
            select(Task).where(Task.id == request.source_id, Task.gym_id == user.gym_id, Task.deleted_at.is_(None))
        )
        if not task:
            raise LookupError("Tarefa não encontrada")
        task.suggested_message = request.improved_message or request.base_message
        extra = dict(task.extra_data or {})
        extra.update({"message_source": "ai_improved", "message_composition_request_id": str(request.id)})
        task.extra_data = extra
    request.status = "applied" if apply else "discarded"
    request.resolved_at = datetime.now(tz=UTC)
    log_audit_event(
        db,
        "message_ai_improvement_applied" if apply else "message_ai_improvement_discarded",
        "message_composition_request",
        user=user,
        entity_id=request.id,
        details={
            "source_type": request.source_type,
            "template_key": request.template_key,
            "base_hash": request.base_hash,
            "improved_hash": request.improved_hash,
        },
    )
    db.commit()
    db.refresh(request)
    return request


def _load_source(
    db: Session, *, gym_id: UUID, source_type: str, source_id: UUID | None
) -> tuple[Member | None, Lead | None, Task | None]:
    if source_type == "task":
        if not source_id:
            raise ValueError("A tarefa de origem é obrigatória")
        task = db.scalar(select(Task).where(Task.id == source_id, Task.gym_id == gym_id, Task.deleted_at.is_(None)))
        if not task:
            raise LookupError("Tarefa não encontrada")
        member = (
            db.scalar(
                select(Member).where(Member.id == task.member_id, Member.gym_id == gym_id, Member.deleted_at.is_(None))
            )
            if task.member_id
            else None
        )
        lead = (
            db.scalar(select(Lead).where(Lead.id == task.lead_id, Lead.gym_id == gym_id, Lead.deleted_at.is_(None)))
            if task.lead_id
            else None
        )
        return member, lead, task
    if source_type == "member":
        member = (
            db.scalar(
                select(Member).where(Member.id == source_id, Member.gym_id == gym_id, Member.deleted_at.is_(None))
            )
            if source_id
            else None
        )
        if not member:
            raise LookupError("Aluno não encontrado")
        return member, None, None
    if source_type == "lead":
        lead = (
            db.scalar(select(Lead).where(Lead.id == source_id, Lead.gym_id == gym_id, Lead.deleted_at.is_(None)))
            if source_id
            else None
        )
        if not lead:
            raise LookupError("Lead não encontrado")
        return None, lead, None
    raise ValueError("Tipo de origem ainda não suportado para melhoria")


def _safe_variables(*, member: Member | None, lead: Lead | None, task: Task | None) -> dict[str, object]:
    subject = member or lead
    first_name = ((getattr(subject, "full_name", "") or "").strip().split() or [""])[0]
    return {
        "first_name": first_name,
        "plan": getattr(member, "plan_name", "") or "",
        "days_inactive": "",
        "next_step": getattr(task, "title", "") or "",
        "responsible": "equipe",
        "risk": getattr(getattr(member, "risk_level", None), "value", "") or "",
        "nps": getattr(member, "nps_last_score", "") or "",
        "date": "",
        "gym_name": "academia",
    }


def _minimal_context(*, member: Member | None, lead: Lead | None, task: Task | None) -> dict:
    context: dict[str, object] = {}
    if member:
        context.update(
            {
                "first_name": member.full_name.split()[0],
                "status": getattr(member.status, "value", str(member.status)),
                "plan": member.plan_name,
                "risk": getattr(member.risk_level, "value", str(member.risk_level)),
                "nps": member.nps_last_score,
                "retention_stage": member.retention_stage,
                "last_checkin_at": member.last_checkin_at.isoformat() if member.last_checkin_at else None,
            }
        )
    if lead:
        context.update(
            {
                "first_name": lead.full_name.split()[0],
                "stage": getattr(lead.stage, "value", str(lead.stage)),
                "source": lead.source,
            }
        )
    if task:
        context.update(
            {
                "task_title": task.title,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            }
        )
    return context


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_json(value: dict) -> str:
    return _hash_text(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str))
