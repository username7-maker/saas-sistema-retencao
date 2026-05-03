from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import AutopilotAction, Lead, Member, Task, TaskPriority, TaskStatus
from app.services.task_event_service import record_task_event


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _priority(value: str | None) -> TaskPriority:
    mapping = {
        "low": TaskPriority.LOW,
        "medium": TaskPriority.MEDIUM,
        "high": TaskPriority.HIGH,
        "urgent": TaskPriority.URGENT,
        "critical": TaskPriority.URGENT,
    }
    return mapping.get((value or "medium").lower(), TaskPriority.MEDIUM)


def _existing_open_task(
    db: Session,
    *,
    gym_id: UUID,
    domain: str,
    member_id: UUID | None,
    lead_id: UUID | None,
) -> Task | None:
    filters = [
        Task.gym_id == gym_id,
        Task.deleted_at.is_(None),
        Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
        Task.extra_data["domain"].astext == domain,
    ]
    if member_id:
        filters.append(Task.member_id == member_id)
    elif lead_id:
        filters.append(Task.lead_id == lead_id)
    else:
        return None
    return db.scalar(select(Task).options(joinedload(Task.member), joinedload(Task.lead)).where(*filters).limit(1))


def escalate_to_human_task(
    db: Session,
    *,
    gym_id: UUID,
    domain: str,
    reason: str,
    member: Member | None = None,
    lead: Lead | None = None,
    action: AutopilotAction | None = None,
    priority: str = "high",
    owner_role: str | None = None,
    suggested_action: str | None = None,
    suggested_message: str | None = None,
    metadata: dict | None = None,
    flush: bool = True,
) -> Task:
    task = _existing_open_task(db, gym_id=gym_id, domain=domain, member_id=member.id if member else None, lead_id=lead.id if lead else None)
    subject_name = (member.full_name if member else lead.full_name if lead else "Contato")
    if task:
        extra = dict(task.extra_data or {})
        attempts = list(extra.get("autopilot_attempts") or [])
        attempts.append({"action_id": str(action.id) if action else None, "reason": reason, "created_at": _now().isoformat()})
        extra.update(
            {
                "source": "autopilot",
                "domain": domain,
                "autopilot_escalated": True,
                "autopilot_attempts": attempts,
                "owner_role": owner_role or extra.get("owner_role"),
            }
        )
        task.extra_data = extra
        if _priority(priority).value in {"high", "urgent"}:
            task.priority = _priority(priority)
        db.add(task)
        record_task_event(
            db,
            task=task,
            current_user=None,
            event_type="forwarded",
            note=f"Autopilot anexou escalonamento: {reason}",
            metadata_json={"source": "autopilot", "action_id": str(action.id) if action else None, **(metadata or {})},
            flush=False,
        )
        if flush:
            db.flush()
        return task

    task = Task(
        gym_id=gym_id,
        member_id=member.id if member else None,
        lead_id=lead.id if lead else None,
        title=f"{suggested_action or 'Resolver excecao'} - {subject_name}",
        description=reason,
        priority=_priority(priority),
        status=TaskStatus.TODO,
        kanban_column=TaskStatus.TODO.value,
        due_date=_now() + timedelta(hours=8),
        suggested_message=suggested_message,
        extra_data={
            "source": "autopilot",
            "domain": domain,
            "autopilot_escalated": True,
            "autopilot_action_id": str(action.id) if action else None,
            "autopilot_policy_key": action.policy_key if action else None,
            "owner_role": owner_role,
            "primary_action_label": suggested_action,
            **(metadata or {}),
        },
    )
    db.add(task)
    db.flush()
    record_task_event(
        db,
        task=task,
        current_user=None,
        event_type="forwarded",
        note=f"Task criada pelo Autopilot: {reason}",
        metadata_json={"source": "autopilot", "action_id": str(action.id) if action else None, **(metadata or {})},
        flush=False,
    )
    if action:
        action.related_task_id = task.id
        db.add(action)
    if flush:
        db.flush()
    return task

