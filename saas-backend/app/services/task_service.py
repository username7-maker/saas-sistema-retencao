from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.cache import invalidate_dashboard_cache
from app.database import get_current_gym_id
from app.models import Task, TaskStatus
from app.schemas import PaginatedResponse, TaskCreate, TaskOut, TaskUpdate
from app.services.tenant_guard import ensure_optional_lead_in_gym, ensure_optional_member_in_gym, ensure_optional_user_in_gym


def _load_with_relations(db: Session, task_id: UUID) -> Task:
    """Reload task with member and lead relationships eager-loaded."""
    stmt = (
        select(Task)
        .options(joinedload(Task.member), joinedload(Task.lead))
        .where(Task.id == task_id)
    )
    return db.scalars(stmt).unique().one()


def _enrich(task: Task) -> TaskOut:
    """Build TaskOut with member_name and lead_name populated from eager-loaded relationships."""
    out = TaskOut.model_validate(task)
    if task.member:
        out.member_name = task.member.full_name
    if task.lead:
        out.lead_name = task.lead.full_name
    return out


def _resolve_gym_id(gym_id: UUID | None = None) -> UUID | None:
    return gym_id or get_current_gym_id()


def _validate_task_links(db: Session, payload: TaskCreate | TaskUpdate, gym_id: UUID | None) -> None:
    if gym_id is None:
        return
    data = payload.model_dump(exclude_unset=True)
    ensure_optional_member_in_gym(db, data.get("member_id"), gym_id)
    ensure_optional_lead_in_gym(db, data.get("lead_id"), gym_id)
    ensure_optional_user_in_gym(db, data.get("assigned_to_user_id"), gym_id)


def create_task(db: Session, payload: TaskCreate, gym_id: UUID | None = None) -> TaskOut:
    resolved_gym_id = _resolve_gym_id(gym_id)
    _validate_task_links(db, payload, resolved_gym_id)
    task = Task(**payload.model_dump())
    if resolved_gym_id is not None:
        task.gym_id = resolved_gym_id
    if task.kanban_column is None:
        task.kanban_column = task.status.value
    if task.status == TaskStatus.DONE:
        task.completed_at = datetime.now(tz=timezone.utc)
    db.add(task)
    db.commit()
    invalidate_dashboard_cache("tasks")
    return _enrich(_load_with_relations(db, task.id))


def list_tasks(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: TaskStatus | None = None,
    assigned_to_user_id: UUID | None = None,
) -> PaginatedResponse:
    filters = [Task.deleted_at.is_(None)]
    if status:
        filters.append(Task.status == status)
    if assigned_to_user_id:
        filters.append(Task.assigned_to_user_id == assigned_to_user_id)

    stmt = (
        select(Task)
        .options(joinedload(Task.member), joinedload(Task.lead))
        .where(and_(*filters))
        .order_by(Task.created_at.desc())
    )
    total = db.scalar(select(func.count()).select_from(Task).where(and_(*filters))) or 0
    offset = (page - 1) * page_size
    tasks = db.scalars(stmt.offset(offset).limit(page_size)).unique().all()
    items = [_enrich(t) for t in tasks]
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


def update_task(db: Session, task_id: UUID, payload: TaskUpdate, gym_id: UUID | None = None) -> TaskOut:
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")

    resolved_gym_id = _resolve_gym_id(gym_id) or task.gym_id
    _validate_task_links(db, payload, resolved_gym_id)

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(task, key, value)
    if payload.status == TaskStatus.DONE:
        task.completed_at = datetime.now(tz=timezone.utc)
    elif payload.status and payload.status != TaskStatus.DONE:
        task.completed_at = None
    if payload.status:
        task.kanban_column = payload.status.value

    db.add(task)
    db.commit()
    invalidate_dashboard_cache("tasks")
    return _enrich(_load_with_relations(db, task_id))


def delete_task(db: Session, task_id: UUID) -> None:
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")
    task.deleted_at = datetime.now(tz=timezone.utc)
    db.add(task)
    db.commit()
    invalidate_dashboard_cache("tasks")
