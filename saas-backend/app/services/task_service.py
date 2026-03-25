from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.cache import invalidate_dashboard_cache
from app.models import RoleEnum, Task, TaskStatus, User
from app.schemas import PaginatedResponse, TaskCreate, TaskOut, TaskUpdate


def _load_with_relations(db: Session, task_id: UUID) -> Task:
    """Reload task with member and lead relationships eager-loaded."""
    stmt = (
        select(Task)
        .options(joinedload(Task.member), joinedload(Task.lead))
        .where(Task.id == task_id)
    )
    return db.scalars(stmt).unique().one()


def get_task_with_relations_or_404(db: Session, task_id: UUID) -> Task:
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")
    return _load_with_relations(db, task_id)


def _enrich(task: Task) -> TaskOut:
    """Build TaskOut with member_name and lead_name populated from eager-loaded relationships."""
    out = TaskOut.model_validate(task)
    if task.member:
        out.member_name = task.member.full_name
    if task.lead:
        out.lead_name = task.lead.full_name
    return out


def _task_extra(task: Task) -> dict:
    return task.extra_data if isinstance(task.extra_data, dict) else {}


def _is_trainer_technical_task(task: Task) -> bool:
    extra_data = _task_extra(task)
    return (
        task.lead_id is None
        and extra_data.get("source") == "assessment_intelligence"
        and extra_data.get("owner_role") == "coach"
    )


def _ensure_task_access(task: Task, current_user: User | None) -> None:
    if current_user is None:
        return
    if task.gym_id != current_user.gym_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")
    if current_user.role == RoleEnum.TRAINER and not _is_trainer_technical_task(task):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")


def create_task(db: Session, payload: TaskCreate, *, commit: bool = True) -> TaskOut:
    task = Task(**payload.model_dump())
    if task.kanban_column is None:
        task.kanban_column = task.status.value
    if task.status == TaskStatus.DONE:
        task.completed_at = datetime.now(tz=timezone.utc)
    db.add(task)
    if commit:
        db.commit()
    else:
        db.flush()
    invalidate_dashboard_cache("tasks")
    return _enrich(_load_with_relations(db, task.id))


def list_tasks(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: TaskStatus | None = None,
    assigned_to_user_id: UUID | None = None,
    current_user: User | None = None,
) -> PaginatedResponse:
    filters = [Task.deleted_at.is_(None)]
    if status:
        filters.append(Task.status == status)
    if assigned_to_user_id:
        filters.append(Task.assigned_to_user_id == assigned_to_user_id)

    stmt = select(Task).options(joinedload(Task.member), joinedload(Task.lead)).where(and_(*filters)).order_by(Task.created_at.desc())

    if current_user and current_user.role == RoleEnum.TRAINER:
        tasks = [
            task
            for task in db.scalars(stmt).unique().all()
            if task.gym_id == current_user.gym_id and _is_trainer_technical_task(task)
        ]
        total = len(tasks)
        offset = (page - 1) * page_size
        page_items = tasks[offset : offset + page_size]
        items = [_enrich(task) for task in page_items]
        return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)

    total = db.scalar(select(func.count()).select_from(Task).where(and_(*filters))) or 0
    offset = (page - 1) * page_size
    tasks = db.scalars(stmt.offset(offset).limit(page_size)).unique().all()
    items = [_enrich(task) for task in tasks]
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


def update_task(
    db: Session,
    task_id: UUID,
    payload: TaskUpdate,
    *,
    current_user: User | None = None,
    commit: bool = True,
) -> TaskOut:
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")
    _ensure_task_access(task, current_user)

    data = payload.model_dump(exclude_unset=True)
    if current_user and current_user.role == RoleEnum.TRAINER:
        disallowed_fields = set(data) - {"status", "kanban_column"}
        if disallowed_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Trainer pode atualizar apenas o status de tarefas tecnicas.",
            )
    for key, value in data.items():
        setattr(task, key, value)
    if payload.status == TaskStatus.DONE:
        task.completed_at = datetime.now(tz=timezone.utc)
    elif payload.status and payload.status != TaskStatus.DONE:
        task.completed_at = None
    if payload.status:
        task.kanban_column = payload.status.value

    db.add(task)
    if commit:
        db.commit()
    else:
        db.flush()
    invalidate_dashboard_cache("tasks")
    return _enrich(_load_with_relations(db, task_id))


def delete_task(db: Session, task_id: UUID, *, commit: bool = True) -> None:
    task = db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")
    task.deleted_at = datetime.now(tz=timezone.utc)
    db.add(task)
    if commit:
        db.commit()
    else:
        db.flush()
    invalidate_dashboard_cache("tasks")
