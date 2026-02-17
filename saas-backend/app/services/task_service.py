from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Task, TaskStatus
from app.schemas import PaginatedResponse, TaskCreate, TaskUpdate


def create_task(db: Session, payload: TaskCreate) -> Task:
    task = Task(**payload.model_dump())
    if task.kanban_column is None:
        task.kanban_column = task.status.value
    if task.status == TaskStatus.DONE:
        task.completed_at = datetime.now(tz=timezone.utc)
    db.add(task)
    db.commit()
    db.refresh(task)
    invalidate_dashboard_cache("tasks")
    return task


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

    stmt = select(Task).where(and_(*filters)).order_by(Task.created_at.desc())
    total = db.scalar(select(func.count()).select_from(Task).where(and_(*filters))) or 0
    offset = (page - 1) * page_size
    items = db.scalars(stmt.offset(offset).limit(page_size)).all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


def update_task(db: Session, task_id: UUID, payload: TaskUpdate) -> Task:
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")

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
    db.refresh(task)
    invalidate_dashboard_cache("tasks")
    return task
