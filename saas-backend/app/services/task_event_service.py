from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Task, TaskEvent, TaskStatus, User
from app.schemas import TaskEventCreate, TaskEventOut
from app.services.task_service import _ensure_task_access, get_task_with_relations_or_404


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _task_extra(task: Task) -> dict:
    return dict(task.extra_data or {}) if isinstance(task.extra_data, dict) else {}


def _event_summary(event_type: str, outcome: str | None, note: str | None, scheduled_for: datetime | None) -> dict:
    return {
        "event_type": event_type,
        "outcome": outcome,
        "note": note,
        "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
        "created_at": _now().isoformat(),
    }


def _serialize(event: TaskEvent) -> TaskEventOut:
    return TaskEventOut.model_validate(event)


def record_task_event(
    db: Session,
    *,
    task: Task,
    current_user: User | None,
    event_type: str,
    outcome: str | None = None,
    note: str | None = None,
    scheduled_for: datetime | None = None,
    contact_channel: str | None = None,
    metadata_json: dict | None = None,
    flush: bool = True,
) -> TaskEvent:
    event = TaskEvent(
        gym_id=task.gym_id,
        task_id=task.id,
        member_id=task.member_id,
        lead_id=task.lead_id,
        user_id=current_user.id if current_user else None,
        event_type=event_type,
        outcome=outcome,
        note=note,
        scheduled_for=scheduled_for,
        contact_channel=contact_channel,
        metadata_json=metadata_json or {},
        created_at=_now(),
    )
    extra = _task_extra(task)
    extra["last_task_event"] = _event_summary(event_type, outcome, note, scheduled_for)
    task.extra_data = extra
    db.add(event)
    db.add(task)
    if flush:
        db.flush()
    return event


def list_task_events(db: Session, *, task_id: UUID, current_user: User) -> list[TaskEventOut]:
    task = get_task_with_relations_or_404(db, task_id)
    _ensure_task_access(task, current_user)
    events = db.scalars(
        select(TaskEvent)
        .where(TaskEvent.task_id == task.id, TaskEvent.gym_id == current_user.gym_id)
        .order_by(TaskEvent.created_at.desc())
    ).all()
    return [_serialize(event) for event in events]


def create_task_event(
    db: Session,
    *,
    task_id: UUID,
    payload: TaskEventCreate,
    current_user: User,
    commit: bool = True,
) -> TaskEventOut:
    task = get_task_with_relations_or_404(db, task_id)
    _ensure_task_access(task, current_user)

    if payload.event_type == "snoozed" and payload.scheduled_for:
        task.status = TaskStatus.TODO
        task.kanban_column = TaskStatus.TODO.value
        task.due_date = payload.scheduled_for
        task.completed_at = None
    elif payload.event_type == "status_changed" and payload.outcome == "completed":
        task.status = TaskStatus.DONE
        task.kanban_column = TaskStatus.DONE.value
        task.completed_at = _now()

    event = record_task_event(
        db,
        task=task,
        current_user=current_user,
        event_type=payload.event_type,
        outcome=payload.outcome,
        note=payload.note,
        scheduled_for=payload.scheduled_for,
        contact_channel=payload.contact_channel,
        metadata_json=payload.metadata_json,
        flush=False,
    )
    if commit:
        db.commit()
    else:
        db.flush()
    invalidate_dashboard_cache("tasks")
    return _serialize(event)
