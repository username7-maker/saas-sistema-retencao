from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.cache import invalidate_dashboard_cache
from app.database import get_current_gym_id
from app.models import RoleEnum, Task, TaskStatus, User
from app.schemas import PaginatedResponse, TaskCreate, TaskOut, TaskUpdate
from app.services.tenant_guard import (
    ensure_optional_lead_in_gym,
    ensure_optional_member_in_gym,
    ensure_optional_user_in_gym,
)


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
        out.preferred_shift = getattr(task.member, "preferred_shift", None)
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


def _is_retention_intelligence_task(task: Task) -> bool:
    extra_data = _task_extra(task)
    source = str(extra_data.get("source") or "").lower()
    title = (task.title or "").lower()
    description = (task.description or "").lower()
    if source in {"retention_intelligence", "retention_automation"}:
        return True
    return (
        title.startswith("escalar churn - ")
        or "automacao de retencao" in description
        or "entrar em contato para reten" in description
    )


def _trainer_technical_task_filter():
    return and_(
        Task.lead_id.is_(None),
        Task.extra_data["source"].astext == "assessment_intelligence",
        Task.extra_data["owner_role"].astext == "coach",
    )


def _retention_intelligence_task_filter():
    source = func.lower(func.coalesce(Task.extra_data["source"].astext, ""))
    description = func.lower(func.coalesce(Task.description, ""))
    return or_(
        source.in_(("retention_intelligence", "retention_automation")),
        Task.title.ilike("Escalar churn - %"),
        description.contains("automacao de retencao"),
        description.contains("entrar em contato para reten"),
    )


def _ensure_task_access(task: Task, current_user: User | None) -> None:
    if current_user is None:
        return
    if task.gym_id != current_user.gym_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")
    if current_user.role == RoleEnum.TRAINER and not _is_trainer_technical_task(task):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")


def _resolve_gym_id(gym_id: UUID | None = None) -> UUID | None:
    return gym_id or get_current_gym_id()


def _validate_task_links(db: Session, payload: TaskCreate | TaskUpdate, gym_id: UUID | None) -> None:
    if gym_id is None:
        return
    data = payload.model_dump(exclude_unset=True)
    ensure_optional_member_in_gym(db, data.get("member_id"), gym_id)
    ensure_optional_lead_in_gym(db, data.get("lead_id"), gym_id)
    ensure_optional_user_in_gym(db, data.get("assigned_to_user_id"), gym_id)


def create_task(db: Session, payload: TaskCreate, *, gym_id: UUID | None = None, commit: bool = True) -> TaskOut:
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
    include_retention: bool = False,
) -> PaginatedResponse:
    filters = [Task.deleted_at.is_(None)]
    if status:
        filters.append(Task.status == status)
    if assigned_to_user_id:
        filters.append(Task.assigned_to_user_id == assigned_to_user_id)

    if current_user and current_user.role == RoleEnum.TRAINER:
        filters.append(Task.gym_id == current_user.gym_id)
        filters.append(_trainer_technical_task_filter())
    elif not include_retention:
        filters.append(not_(_retention_intelligence_task_filter()))

    criteria = and_(*filters)
    stmt = (
        select(Task)
        .options(joinedload(Task.member), joinedload(Task.lead))
        .where(criteria)
        .order_by(Task.created_at.desc())
    )

    offset = (page - 1) * page_size
    total = db.scalar(select(func.count()).select_from(Task).where(criteria)) or 0
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
    resolved_gym_id = current_user.gym_id if current_user else task.gym_id
    _validate_task_links(db, payload, resolved_gym_id)

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
