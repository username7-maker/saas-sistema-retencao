from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import AutopilotAction, AutopilotEvent, Lead, Member, RoleEnum, Task, TaskEvent, User
from app.schemas import AutopilotActionOut, AutopilotEventOut, AutopilotMetricsOut, AutopilotTimelineItemOut
from app.services.autopilot_action_service import (
    escalate_autopilot_action_to_human,
    execute_autopilot_action,
    mark_autopilot_action_failed,
)
from app.services.audit_service import log_audit_event
from app.services.human_escalation_service import escalate_to_human_task

router = APIRouter(prefix="/autopilot", tags=["autopilot"])


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _get_action_or_404(db: Session, action_id: UUID, current_user: User) -> AutopilotAction:
    action = db.scalar(select(AutopilotAction).where(AutopilotAction.id == action_id, AutopilotAction.gym_id == current_user.gym_id))
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acao Autopilot nao encontrada")
    return action


@router.get("/events", response_model=list[AutopilotEventOut])
def list_autopilot_events_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    event_type: str | None = Query(default=None),
    processing_status: str | None = Query(default=None),
    member_id: UUID | None = Query(default=None),
    lead_id: UUID | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
) -> list[AutopilotEventOut]:
    filters = [AutopilotEvent.gym_id == current_user.gym_id]
    if event_type:
        filters.append(AutopilotEvent.event_type == event_type)
    if processing_status:
        filters.append(AutopilotEvent.processing_status == processing_status)
    if member_id:
        filters.append(AutopilotEvent.member_id == member_id)
    if lead_id:
        filters.append(AutopilotEvent.lead_id == lead_id)
    events = db.scalars(select(AutopilotEvent).where(*filters).order_by(AutopilotEvent.created_at.desc()).limit(limit)).all()
    return [AutopilotEventOut.model_validate(event) for event in events]


@router.get("/actions", response_model=list[AutopilotActionOut])
def list_autopilot_actions_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    status_filter: str | None = Query(default=None, alias="status"),
    domain: str | None = Query(default=None),
    member_id: UUID | None = Query(default=None),
    lead_id: UUID | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
) -> list[AutopilotActionOut]:
    filters = [AutopilotAction.gym_id == current_user.gym_id]
    if status_filter:
        filters.append(AutopilotAction.status == status_filter)
    if domain:
        filters.append(AutopilotAction.domain == domain)
    if member_id:
        filters.append(AutopilotAction.member_id == member_id)
    if lead_id:
        filters.append(AutopilotAction.lead_id == lead_id)
    actions = db.scalars(select(AutopilotAction).where(*filters).order_by(AutopilotAction.created_at.desc()).limit(limit)).all()
    return [AutopilotActionOut.model_validate(action) for action in actions]


@router.post("/actions/{action_id}/retry", response_model=AutopilotActionOut)
def retry_autopilot_action_endpoint(
    action_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> AutopilotActionOut:
    action = _get_action_or_404(db, action_id, current_user)
    if action.status not in {"failed", "timed_out", "blocked", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Acao nao esta em estado de retry.")
    action.status = "planned"
    action.failure_reason = None
    action.escalation_reason = None
    action.attempt_number += 1
    executed = execute_autopilot_action(db, action, flush=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="autopilot_action_retried",
        entity="autopilot_action",
        user=current_user,
        entity_id=action.id,
        details={"status": executed.status},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return AutopilotActionOut.model_validate(executed)


@router.post("/actions/{action_id}/cancel", response_model=AutopilotActionOut)
def cancel_autopilot_action_endpoint(
    action_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> AutopilotActionOut:
    action = _get_action_or_404(db, action_id, current_user)
    if action.status in {"succeeded", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Acao ja finalizada.")
    mark_autopilot_action_failed(db, action, reason="cancelled_by_operator", flush=False)
    action.status = "cancelled"
    context = get_request_context(request)
    log_audit_event(
        db,
        action="autopilot_action_cancelled",
        entity="autopilot_action",
        user=current_user,
        entity_id=action.id,
        details={"policy_key": action.policy_key},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return AutopilotActionOut.model_validate(action)


@router.post("/actions/{action_id}/escalate", response_model=AutopilotActionOut)
def escalate_autopilot_action_endpoint(
    action_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> AutopilotActionOut:
    action = _get_action_or_404(db, action_id, current_user)
    escalate_autopilot_action_to_human(db, action, reason="manual_escalation", flush=False)
    member = db.get(Member, action.member_id) if action.member_id else None
    lead = db.get(Lead, action.lead_id) if action.lead_id else None
    escalate_to_human_task(
        db,
        gym_id=current_user.gym_id,
        domain=action.domain,
        reason="Escalado manualmente a partir do Autopilot.",
        priority="high",
        owner_role="manager",
        member=member,
        lead=lead,
        action=action,
        flush=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="autopilot_action_escalated",
        entity="autopilot_action",
        user=current_user,
        entity_id=action.id,
        details={"policy_key": action.policy_key, "domain": action.domain},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return AutopilotActionOut.model_validate(action)


@router.get("/metrics", response_model=AutopilotMetricsOut)
def get_autopilot_metrics_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
) -> AutopilotMetricsOut:
    end = to_date or _now()
    start = from_date or (end - timedelta(days=30))
    actions = list(
        db.scalars(
            select(AutopilotAction).where(
                AutopilotAction.gym_id == current_user.gym_id,
                AutopilotAction.created_at >= start,
                AutopilotAction.created_at <= end,
            )
        ).all()
    )
    events = list(
        db.scalars(
            select(AutopilotEvent).where(
                AutopilotEvent.gym_id == current_user.gym_id,
                AutopilotEvent.created_at >= start,
                AutopilotEvent.created_at <= end,
            )
        ).all()
    )
    auto_task_count = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.gym_id == current_user.gym_id,
                Task.created_at >= start,
                Task.created_at <= end,
                Task.extra_data["source"].astext == "autopilot",
            )
        )
        or 0
    )
    status_counts = Counter(action.status for action in actions)
    by_domain = Counter(action.domain for action in actions)
    by_template = Counter(action.template_key or "sem_template" for action in actions)
    blocked_reasons = Counter((action.failure_reason or "sem_motivo") for action in actions if action.status == "blocked")
    auto_closed = sum(1 for event in events if event.event_type in {"task_auto_closed", "automation_action_succeeded"})
    succeeded = status_counts.get("succeeded", 0)
    created = len(actions)
    human_created = int(auto_task_count)
    rates = {
        "autopilot_resolution_rate": round(succeeded / created, 4) if created else None,
        "human_task_avoidance_rate": round(auto_closed / (auto_closed + human_created), 4) if (auto_closed + human_created) else None,
    }
    return AutopilotMetricsOut(
        period={"from": start.isoformat(), "to": end.isoformat()},
        automation_actions={
            "created": created,
            "sent": status_counts.get("sent", 0) + status_counts.get("awaiting_outcome", 0),
            "succeeded": succeeded,
            "failed": status_counts.get("failed", 0),
            "timed_out": status_counts.get("timed_out", 0),
            "escalated": status_counts.get("escalated", 0),
            "blocked": status_counts.get("blocked", 0),
        },
        tasks={
            "auto_closed": auto_closed,
            "human_created": human_created,
            "avoided_estimate": auto_closed,
        },
        rates=rates,
        by_domain=dict(by_domain),
        by_template=dict(by_template),
        blocked_reasons=dict(blocked_reasons),
    )


@router.get("/timeline", response_model=list[AutopilotTimelineItemOut])
def get_autopilot_timeline_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
    member_id: UUID | None = Query(default=None),
    lead_id: UUID | None = Query(default=None),
    task_id: UUID | None = Query(default=None),
    limit: int = Query(80, ge=1, le=200),
) -> list[AutopilotTimelineItemOut]:
    if not any([member_id, lead_id, task_id]):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe member_id, lead_id ou task_id.")
    task_filters = [TaskEvent.gym_id == current_user.gym_id]
    event_filters = [AutopilotEvent.gym_id == current_user.gym_id]
    action_filters = [AutopilotAction.gym_id == current_user.gym_id]
    if member_id:
        task_filters.append(TaskEvent.member_id == member_id)
        event_filters.append(AutopilotEvent.member_id == member_id)
        action_filters.append(AutopilotAction.member_id == member_id)
    if lead_id:
        task_filters.append(TaskEvent.lead_id == lead_id)
        event_filters.append(AutopilotEvent.lead_id == lead_id)
        action_filters.append(AutopilotAction.lead_id == lead_id)
    if task_id:
        task_filters.append(TaskEvent.task_id == task_id)
        event_filters.append(AutopilotEvent.task_id == task_id)
        action_filters.append(AutopilotAction.related_task_id == task_id)

    items: list[AutopilotTimelineItemOut] = []
    for event in db.scalars(select(AutopilotEvent).where(*event_filters).order_by(AutopilotEvent.created_at.desc()).limit(limit)).all():
        items.append(
            AutopilotTimelineItemOut(
                kind="event",
                label=event.event_type,
                detail=event.processing_error or event.source,
                occurred_at=event.occurred_at,
                metadata=event.metadata_json or {},
            )
        )
    for action in db.scalars(select(AutopilotAction).where(*action_filters).order_by(AutopilotAction.created_at.desc()).limit(limit)).all():
        items.append(
            AutopilotTimelineItemOut(
                kind="action",
                label=f"{action.policy_key} / {action.status}",
                detail=action.failure_reason or action.escalation_reason or action.outcome,
                occurred_at=action.created_at,
                metadata={"action_id": str(action.id), "domain": action.domain, "template_key": action.template_key},
            )
        )
    for task_event in db.scalars(select(TaskEvent).where(*task_filters).order_by(TaskEvent.created_at.desc()).limit(limit)).all():
        items.append(
            AutopilotTimelineItemOut(
                kind="task_event",
                label=task_event.event_type,
                detail=task_event.note or task_event.outcome,
                occurred_at=task_event.created_at,
                metadata=task_event.metadata_json or {},
            )
        )
    return sorted(items, key=lambda item: item.occurred_at, reverse=True)[:limit]
