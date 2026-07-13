from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.branding import PRODUCT_NAME
from app.models import AutopilotAction, AutopilotEvent, Lead, Member, MessageLog
from app.services.autopilot_event_service import record_event
from app.services.autopilot_policy_service import AutopilotDecision, render_template
from app.services.autopilot_safety_service import check_autopilot_safety
from app.services.communication_channel_service import resolve_communication_channel
from app.services.kommo_service import KommoSalesbotDispatchError, KommoServiceError, send_member_message_via_kommo_salesbot
from app.services.whatsapp_service import get_gym_instance, send_whatsapp_sync

REPLAY_SAFE_PROVIDER_STATUSES = {"awaiting_outcome", "succeeded", "dispatch_uncertain", "failed_uncertain"}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def build_autopilot_request_fingerprint(**payload: object) -> str:
    normalized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _idempotency_conflict(existing: AutopilotAction, request_fingerprint: str | None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "autopilot_idempotency_conflict",
            "message": "Intent idempotente ja existe com fingerprint diferente.",
            "idempotency_key": existing.idempotency_key,
            "existing_action_id": str(existing.id),
            "existing_fingerprint": existing.request_fingerprint,
            "request_fingerprint": request_fingerprint,
            "status": existing.status,
        },
    )


def create_autopilot_action(
    db: Session,
    *,
    gym_id: UUID,
    decision: AutopilotDecision,
    member: Member | None = None,
    lead: Lead | None = None,
    related_task_id: UUID | None = None,
    message_body: str | None = None,
    idempotency_key: str | None = None,
    request_fingerprint: str | None = None,
    consent_snapshot: dict | None = None,
    flush: bool = True,
) -> AutopilotAction:
    if idempotency_key:
        existing = db.scalar(
            select(AutopilotAction).where(
                AutopilotAction.gym_id == gym_id,
                AutopilotAction.idempotency_key == idempotency_key,
            )
        )
        if existing:
            if (
                request_fingerprint
                and existing.request_fingerprint
                and existing.request_fingerprint != request_fingerprint
            ):
                raise _idempotency_conflict(existing, request_fingerprint)
            return existing
    first_name = ((member.full_name if member else lead.full_name if lead else "") or "").split(" ")[0]
    resolved_message = message_body
    if not resolved_message and decision.template_key:
        resolved_message = render_template(decision.template_key, first_name=first_name)
    action = AutopilotAction(
        gym_id=gym_id,
        policy_key=decision.policy_key,
        domain=decision.domain,
        action_type=decision.action_type,
        status="planned",
        member_id=member.id if member else None,
        lead_id=lead.id if lead else None,
        related_task_id=related_task_id,
        channel=_channel_for_action_type(decision.action_type),
        template_key=decision.template_key,
        message_body=resolved_message,
        timeout_at=_now() + timedelta(hours=decision.next_timeout_hours),
        max_attempts=1,
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        consent_snapshot=consent_snapshot or {},
        provider_status="intent_persisted",
        metadata_json={"decision_reason": decision.reason, **decision.metadata},
    )
    db.add(action)
    if flush:
        db.flush()
    record_event(
        db,
        gym_id=gym_id,
        event_type="automation_action_created",
        source="autopilot",
        member_id=action.member_id,
        lead_id=action.lead_id,
        task_id=action.related_task_id,
        autopilot_action_id=action.id,
        metadata={"policy_key": action.policy_key, "action_type": action.action_type, "status": action.status},
        flush=flush,
    )
    return action


def _channel_for_action_type(action_type: str) -> str:
    if action_type == "send_primary_channel":
        return "primary"
    if action_type == "send_whatsapp":
        return "whatsapp"
    if action_type in {"kommo_operator_handoff", "kommo_draft_reply"}:
        return "kommo"
    return "none"


def mark_autopilot_action_succeeded(
    db: Session,
    action: AutopilotAction,
    *,
    outcome: str,
    metadata: dict | None = None,
    flush: bool = True,
) -> AutopilotAction:
    action.status = "succeeded"
    action.outcome = outcome
    action.completed_at = _now()
    extra = dict(action.metadata_json or {})
    extra.update(metadata or {})
    action.metadata_json = extra
    db.add(action)
    if flush:
        db.flush()
    record_event(
        db,
        gym_id=action.gym_id,
        event_type="automation_action_succeeded",
        source="autopilot",
        member_id=action.member_id,
        lead_id=action.lead_id,
        task_id=action.related_task_id,
        autopilot_action_id=action.id,
        metadata={"outcome": outcome, **(metadata or {})},
        flush=flush,
    )
    return action


def mark_autopilot_action_failed(db: Session, action: AutopilotAction, *, reason: str, flush: bool = True) -> AutopilotAction:
    action.status = "failed"
    action.failure_reason = reason
    action.completed_at = _now()
    db.add(action)
    if flush:
        db.flush()
    record_event(
        db,
        gym_id=action.gym_id,
        event_type="automation_action_failed",
        source="autopilot",
        member_id=action.member_id,
        lead_id=action.lead_id,
        task_id=action.related_task_id,
        autopilot_action_id=action.id,
        metadata={"reason": reason},
        flush=flush,
    )
    return action


def mark_autopilot_action_timed_out(db: Session, action: AutopilotAction, *, flush: bool = True) -> AutopilotAction:
    action.status = "timed_out"
    action.completed_at = _now()
    db.add(action)
    if flush:
        db.flush()
    record_event(
        db,
        gym_id=action.gym_id,
        event_type="automation_action_timed_out",
        source="autopilot",
        member_id=action.member_id,
        lead_id=action.lead_id,
        task_id=action.related_task_id,
        autopilot_action_id=action.id,
        metadata={"policy_key": action.policy_key},
        flush=flush,
    )
    return action


def escalate_autopilot_action_to_human(db: Session, action: AutopilotAction, *, reason: str, flush: bool = True) -> AutopilotAction:
    action.status = "escalated"
    action.escalation_reason = reason
    action.completed_at = _now()
    db.add(action)
    if flush:
        db.flush()
    record_event(
        db,
        gym_id=action.gym_id,
        event_type="human_intervention_required",
        source="autopilot",
        member_id=action.member_id,
        lead_id=action.lead_id,
        task_id=action.related_task_id,
        autopilot_action_id=action.id,
        metadata={"reason": reason, "policy_key": action.policy_key},
        flush=flush,
    )
    return action


def execute_autopilot_action(
    db: Session,
    action: AutopilotAction,
    *,
    require_auto_send: bool = True,
    flush: bool = True,
    commit_before_provider: bool = False,
) -> AutopilotAction:
    if action.status in REPLAY_SAFE_PROVIDER_STATUSES:
        return action
    if action.status not in {"planned", "scheduled"}:
        return action
    if action.action_type == "send_primary_channel":
        return _execute_primary_channel_action(
            db,
            action,
            require_auto_send=require_auto_send,
            flush=flush,
            commit_before_provider=commit_before_provider,
        )
    if action.action_type == "kommo_operator_handoff":
        return _execute_kommo_operator_handoff(db, action, flush=flush, commit_before_provider=commit_before_provider)
    if action.action_type != "send_whatsapp":
        action.status = "skipped" if action.action_type == "no_op" else "blocked"
        db.add(action)
        if flush:
            db.flush()
        return action
    return _execute_whatsapp_action(
        db,
        action,
        require_auto_send=require_auto_send,
        flush=flush,
        commit_before_provider=commit_before_provider,
    )


def _execute_primary_channel_action(
    db: Session,
    action: AutopilotAction,
    *,
    require_auto_send: bool,
    flush: bool = True,
    commit_before_provider: bool = False,
) -> AutopilotAction:
    resolution = resolve_communication_channel(db, gym_id=action.gym_id, requested_channel="auto")
    metadata = dict(action.metadata_json or {})
    metadata.update(
        {
            "requested_channel": resolution.requested_channel,
            "resolved_channel": resolution.channel,
            "primary_channel": resolution.primary_channel,
            "fallback_channel": resolution.fallback_channel,
            "used_channel_fallback": resolution.used_fallback,
            "kommo_ready": resolution.kommo_ready,
            "channel_resolution_detail": resolution.detail,
        }
    )
    action.metadata_json = metadata
    action.channel = resolution.channel
    db.add(action)

    if resolution.channel == "kommo":
        member = db.get(Member, action.member_id) if action.member_id else None
        lead = db.get(Lead, action.lead_id) if action.lead_id else None
        safety = check_autopilot_safety(
            db,
            gym_id=action.gym_id,
            domain=action.domain,
            policy_key=action.policy_key,
            action_type="kommo_operator_handoff",
            member=member,
            lead=lead,
            message_text=action.message_body,
            require_auto_send=require_auto_send,
            ignore_autopilot_action_id=action.id,
        )
        if safety.scheduled_for:
            action.status = "scheduled"
            action.scheduled_for = safety.scheduled_for
            action.failure_reason = ",".join(safety.reasons)
            db.add(action)
            if flush:
                db.flush()
            return action
        if not safety.allowed:
            action.status = "blocked"
            action.failure_reason = ",".join(safety.reasons)
            record_event(
                db,
                gym_id=action.gym_id,
                event_type="automation_action_blocked",
                source="autopilot_safety",
                member_id=action.member_id,
                lead_id=action.lead_id,
                task_id=action.related_task_id,
                autopilot_action_id=action.id,
                metadata={"reasons": safety.reasons, "resolved_channel": "kommo"},
                flush=False,
            )
            db.add(action)
            if flush:
                db.flush()
            return action
        return _execute_kommo_operator_handoff(db, action, flush=flush, commit_before_provider=commit_before_provider)

    if resolution.channel == "manual":
        action.status = "blocked"
        action.failure_reason = "manual_channel_resolved"
        record_event(
            db,
            gym_id=action.gym_id,
            event_type="automation_action_blocked",
            source="communication_channel_router",
            member_id=action.member_id,
            lead_id=action.lead_id,
            task_id=action.related_task_id,
            autopilot_action_id=action.id,
            metadata={"reason": "manual_channel_resolved", "resolution": metadata},
            flush=False,
        )
        db.add(action)
        if flush:
            db.flush()
        return action

    return _execute_whatsapp_action(
        db,
        action,
        require_auto_send=require_auto_send,
        flush=flush,
        commit_before_provider=commit_before_provider,
    )


def _execute_whatsapp_action(
    db: Session,
    action: AutopilotAction,
    *,
    require_auto_send: bool,
    flush: bool = True,
    commit_before_provider: bool = False,
) -> AutopilotAction:
    member = db.get(Member, action.member_id) if action.member_id else None
    lead = db.get(Lead, action.lead_id) if action.lead_id else None
    safety = check_autopilot_safety(
        db,
        gym_id=action.gym_id,
        domain=action.domain,
        policy_key=action.policy_key,
        action_type="send_whatsapp",
        member=member,
        lead=lead,
        message_text=action.message_body,
        require_auto_send=require_auto_send,
        ignore_autopilot_action_id=action.id,
    )
    if safety.scheduled_for:
        action.status = "scheduled"
        action.scheduled_for = safety.scheduled_for
        action.failure_reason = ",".join(safety.reasons)
        db.add(action)
        if flush:
            db.flush()
        return action
    if not safety.allowed:
        action.status = "blocked"
        action.failure_reason = ",".join(safety.reasons)
        db.add(action)
        record_event(
            db,
            gym_id=action.gym_id,
            event_type="automation_action_blocked",
            source="autopilot_safety",
            member_id=action.member_id,
            lead_id=action.lead_id,
            task_id=action.related_task_id,
            autopilot_action_id=action.id,
            metadata={"reasons": safety.reasons},
            flush=False,
        )
        if flush:
            db.flush()
        return action
    phone = (member.phone if member else lead.phone if lead else None) or ""
    if not phone or not action.message_body:
        return mark_autopilot_action_failed(db, action, reason="missing_phone_or_message", flush=flush)
    action.status = "executing"
    action.executed_at = _now()
    action.dispatched_at = action.executed_at
    action.provider_status = "dispatching"
    action.channel = "whatsapp"
    db.add(action)
    if flush or commit_before_provider:
        db.flush()
    if commit_before_provider:
        db.commit()
    try:
        log = send_whatsapp_sync(
            db,
            phone=phone,
            message=action.message_body,
            instance=get_gym_instance(db, action.gym_id),
            member_id=action.member_id,
            lead_id=action.lead_id,
            template_name=action.template_key,
            event_type="autopilot",
        )
    except Exception as exc:
        action.status = "dispatch_uncertain"
        action.provider_status = "dispatch_uncertain"
        action.provider_error = str(exc)
        action.failure_reason = str(exc)
        db.add(action)
        if flush:
            db.flush()
        return action
    _attach_action_to_message_log(log, action.id)
    if log.status in {"sent", "delivered", "read"}:
        action.status = "awaiting_outcome"
        action.provider_status = "accepted"
        action.provider_reference = str(getattr(log, "provider_message_id", None) or log.id)
        record_event(
            db,
            gym_id=action.gym_id,
            event_type="whatsapp_outbound_sent",
            source="autopilot",
            member_id=action.member_id,
            lead_id=action.lead_id,
            task_id=action.related_task_id,
            autopilot_action_id=action.id,
            metadata={"message_log_id": str(log.id), "template_key": action.template_key},
            flush=False,
        )
    else:
        action.status = "failed"
        action.provider_status = "failed"
        action.provider_error = log.error_detail or log.status
        action.failure_reason = log.error_detail or log.status
        record_event(
            db,
            gym_id=action.gym_id,
            event_type="whatsapp_outbound_failed",
            source="autopilot",
            member_id=action.member_id,
            lead_id=action.lead_id,
            task_id=action.related_task_id,
            autopilot_action_id=action.id,
            metadata={"message_log_id": str(log.id), "status": log.status, "error": log.error_detail},
            flush=False,
        )
    db.add(action)
    if flush:
        db.flush()
    return action


def _execute_kommo_operator_handoff(
    db: Session,
    action: AutopilotAction,
    *,
    flush: bool = True,
    commit_before_provider: bool = False,
) -> AutopilotAction:
    member = db.get(Member, action.member_id) if action.member_id else None
    if member is None:
        return mark_autopilot_action_failed(db, action, reason="kommo_member_required", flush=flush)

    action.status = "executing"
    action.executed_at = _now()
    action.dispatched_at = action.executed_at
    action.provider_status = "dispatching"
    db.add(action)
    if flush or commit_before_provider:
        db.flush()
    if commit_before_provider:
        db.commit()
    metadata = dict(action.metadata_json or {})
    title = str(metadata.get("task_title") or metadata.get("title") or f"{PRODUCT_NAME} - {action.policy_key}")[:120]
    try:
        result = send_member_message_via_kommo_salesbot(
            db,
            gym_id=action.gym_id,
            member=member,
            domain=action.domain,
            message_text=action.message_body or str(metadata.get("task_reason") or metadata.get("reason") or action.policy_key),
            source_type=action.policy_key,
            source_id=action.related_task_id or action.id,
            title=title,
        )
        action.provider_status = "accepted"
        action.provider_reference = result.task_id or result.lead_id or result.contact_id
        metadata.update(
            {
                "kommo_contact_id": result.contact_id,
                "kommo_lead_id": result.lead_id,
                "kommo_message_log_id": str(result.message_log_id) if result.message_log_id else None,
                "salesbot_id": result.salesbot_id,
                "delivery_mode": result.delivery_mode,
                "kommo_route_kind": result.route_kind,
                "kommo_trainer_user_id": str(result.trainer_user_id) if result.trainer_user_id else None,
                "kommo_route_fallback_reason": result.route_fallback_reason,
                "operator_confirmed_send": False,
                "salesbot_outbound": True,
            }
        )
        action.status = "awaiting_outcome"
        action.metadata_json = metadata
        record_event(
            db,
            gym_id=action.gym_id,
            event_type="kommo_salesbot_queued",
            source="autopilot",
            member_id=action.member_id,
            task_id=action.related_task_id,
            autopilot_action_id=action.id,
            metadata={
                "kommo_contact_id": result.contact_id,
                "kommo_lead_id": result.lead_id,
                "message_log_id": str(result.message_log_id) if result.message_log_id else None,
                "salesbot_id": result.salesbot_id,
                "delivery_mode": result.delivery_mode,
                "kommo_route_kind": result.route_kind,
                "kommo_trainer_user_id": str(result.trainer_user_id) if result.trainer_user_id else None,
                "kommo_route_fallback_reason": result.route_fallback_reason,
                "template_key": action.template_key,
            },
            flush=False,
        )
    except KommoSalesbotDispatchError as exc:
        result = exc.result
        metadata.update(
            {
                "kommo_contact_id": result.contact_id,
                "kommo_lead_id": result.lead_id,
                "message_log_id": str(result.message_log_id) if result.message_log_id else None,
                "salesbot_id": result.salesbot_id,
                "delivery_mode": result.delivery_mode,
                "kommo_route_kind": result.route_kind,
                "kommo_trainer_user_id": str(result.trainer_user_id) if result.trainer_user_id else None,
                "kommo_route_fallback_reason": result.route_fallback_reason,
            }
        )
        action.status = "failed_uncertain"
        action.provider_status = "failed_uncertain"
        action.provider_error = str(exc)
        action.failure_reason = str(exc)
        action.metadata_json = metadata
        record_event(
            db,
            gym_id=action.gym_id,
            event_type="kommo_salesbot_failed",
            source="autopilot",
            member_id=action.member_id,
            task_id=action.related_task_id,
            autopilot_action_id=action.id,
            metadata={
                "detail": str(exc),
                "kommo_contact_id": result.contact_id,
                "kommo_lead_id": result.lead_id,
                "salesbot_id": result.salesbot_id,
                "delivery_mode": result.delivery_mode,
                "kommo_route_kind": result.route_kind,
                "kommo_trainer_user_id": str(result.trainer_user_id) if result.trainer_user_id else None,
                "kommo_route_fallback_reason": result.route_fallback_reason,
            },
            flush=False,
        )
    except KommoServiceError as exc:
        action.status = "dispatch_uncertain"
        action.provider_status = "dispatch_uncertain"
        action.provider_error = str(exc)
        action.failure_reason = str(exc)
        action.metadata_json = metadata
        record_event(
            db,
            gym_id=action.gym_id,
            event_type="kommo_salesbot_failed",
            source="autopilot",
            member_id=action.member_id,
            task_id=action.related_task_id,
            autopilot_action_id=action.id,
            metadata={"detail": str(exc), "template_key": action.template_key},
            flush=False,
        )
    db.add(action)
    if flush:
        db.flush()
    return action


def _record_kommo_message_log(db: Session, *, action: AutopilotAction, member: Member, result) -> None:
    recipient = (member.phone or member.email or "").strip() or str(member.id)
    log = MessageLog(
        gym_id=action.gym_id,
        member_id=member.id,
        lead_id=None,
        channel="kommo",
        recipient=recipient,
        template_name=action.template_key,
        content=action.message_body or "",
        status="sent",
        direction="outbound",
        event_type="kommo_operator_handoff",
        provider_message_id=result.task_id,
        extra_data={
            "autopilot_action_id": str(action.id),
            "source": "autopilot",
            "kommo_contact_id": result.contact_id,
            "kommo_lead_id": result.lead_id,
            "kommo_task_id": result.task_id,
        },
    )
    db.add(log)


def _attach_action_to_message_log(log: MessageLog, action_id: UUID) -> None:
    extra = dict(log.extra_data or {})
    extra["autopilot_action_id"] = str(action_id)
    extra["source"] = "autopilot"
    log.extra_data = extra


def pending_actions_due(db: Session, *, limit: int = 100) -> list[AutopilotAction]:
    now = _now()
    return list(
        db.scalars(
            select(AutopilotAction)
            .where(
                AutopilotAction.status.in_(["planned", "scheduled"]),
                or_(AutopilotAction.scheduled_for.is_(None), AutopilotAction.scheduled_for <= now),
            )
            .order_by(AutopilotAction.created_at.asc())
            .limit(limit)
        ).all()
    )


def timed_out_actions(db: Session, *, limit: int = 100) -> list[AutopilotAction]:
    return list(
        db.scalars(
            select(AutopilotAction)
            .where(AutopilotAction.status == "awaiting_outcome", AutopilotAction.timeout_at <= _now())
            .order_by(AutopilotAction.timeout_at.asc())
            .limit(limit)
        ).all()
    )


def pending_events(db: Session, *, limit: int = 100) -> list[AutopilotEvent]:
    return list(
        db.scalars(
            select(AutopilotEvent)
            .where(AutopilotEvent.processing_status == "pending")
            .order_by(AutopilotEvent.received_at.asc())
            .limit(limit)
        ).all()
    )
