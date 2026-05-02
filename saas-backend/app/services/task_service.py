from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.cache import invalidate_dashboard_cache
from app.database import get_current_gym_id
from app.models import Lead, Member, RoleEnum, Task, TaskPriority, TaskStatus, User
from app.schemas import (
    PaginatedResponse,
    TaskCreate,
    TaskMetricsBreakdownOut,
    TaskMetricsOut,
    TaskMetricsOwnerOut,
    TaskOperationalCleanupApplyOut,
    TaskOperationalCleanupPreviewOut,
    TaskOut,
    TaskUpdate,
)
from app.services.preferred_shift_service import preferred_shift_filter_condition
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


def _is_finance_task(task: Task) -> bool:
    extra_data = _task_extra(task)
    return extra_data.get("source") == "delinquency" or extra_data.get("domain") == "finance"


def is_task_operationally_archived(task: Task) -> bool:
    archive = _task_extra(task).get("operational_archive")
    return isinstance(archive, dict) and bool(archive.get("archived_at"))


def _operational_archive_filter():
    return func.coalesce(Task.extra_data["operational_archive"]["archived_at"].astext, "") == ""


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
    if _is_finance_task(task) and current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST}:
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
    q: str | None = None,
    priority: TaskPriority | None = None,
    source: str | None = None,
    due: Literal["overdue", "today", "upcoming"] | None = None,
    unassigned: bool | None = None,
    member_id: UUID | None = None,
    lead_id: UUID | None = None,
    preferred_shift: str | None = None,
    plan_name: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    include_archived: bool = False,
) -> PaginatedResponse:
    filters = [Task.deleted_at.is_(None)]
    if not include_archived:
        filters.append(_operational_archive_filter())
    if current_user:
        filters.append(Task.gym_id == current_user.gym_id)
    if status:
        filters.append(Task.status == status)
    if priority:
        filters.append(Task.priority == priority)
    if assigned_to_user_id:
        filters.append(Task.assigned_to_user_id == assigned_to_user_id)
    if unassigned is True:
        filters.append(Task.assigned_to_user_id.is_(None))
    elif unassigned is False:
        filters.append(Task.assigned_to_user_id.is_not(None))
    if member_id:
        filters.append(Task.member_id == member_id)
    if lead_id:
        filters.append(Task.lead_id == lead_id)
    if source:
        filters.append(func.lower(func.coalesce(Task.extra_data["source"].astext, "manual")) == source.lower())
    if preferred_shift:
        if preferred_shift == "unassigned":
            filters.append(or_(Task.member_id.is_(None), Member.preferred_shift.is_(None)))
        else:
            shift_filter = preferred_shift_filter_condition(Member.preferred_shift, preferred_shift)
            if shift_filter is not None:
                filters.append(shift_filter)
    if plan_name:
        filters.append(Member.plan_name.ilike(f"%{plan_name.strip()}%"))
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                Task.title.ilike(term),
                Task.description.ilike(term),
                Member.full_name.ilike(term),
                Lead.full_name.ilike(term),
            )
        )
    if date_from:
        filters.append(Task.due_date >= date_from)
    if date_to:
        filters.append(Task.due_date <= date_to)
    if due:
        now = datetime.now(tz=timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        if due == "overdue":
            filters.append(Task.due_date < today_start)
            filters.append(Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]))
        elif due == "today":
            filters.append(Task.due_date >= today_start)
            filters.append(Task.due_date < tomorrow_start)
        elif due == "upcoming":
            filters.append(Task.due_date >= tomorrow_start)

    if current_user and current_user.role == RoleEnum.TRAINER:
        filters.append(_trainer_technical_task_filter())
    else:
        if current_user and current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST}:
            filters.append(func.coalesce(Task.extra_data["domain"].astext, "") != "finance")
            filters.append(func.coalesce(Task.extra_data["source"].astext, "") != "delinquency")
        if not include_retention:
            filters.append(not_(_retention_intelligence_task_filter()))

    criteria = and_(*filters)
    stmt = (
        select(Task)
        .outerjoin(Task.member)
        .outerjoin(Task.lead)
        .options(joinedload(Task.member), joinedload(Task.lead))
        .where(criteria)
        .order_by(Task.created_at.desc())
    )

    offset = (page - 1) * page_size
    total = (
        db.scalar(
            select(func.count(func.distinct(Task.id)))
            .select_from(Task)
            .outerjoin(Task.member)
            .outerjoin(Task.lead)
            .where(criteria)
        )
        or 0
    )
    tasks = db.scalars(stmt.offset(offset).limit(page_size)).unique().all()
    items = [_enrich(task) for task in tasks]
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


def get_task_metrics(db: Session, *, current_user: User) -> TaskMetricsOut:
    filters = [Task.gym_id == current_user.gym_id, Task.deleted_at.is_(None), _operational_archive_filter()]
    if current_user.role == RoleEnum.TRAINER:
        filters.append(_trainer_technical_task_filter())
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    seven_days_ago = now - timedelta(days=7)

    tasks = db.scalars(
        select(Task)
        .options(joinedload(Task.assigned_user))
        .where(and_(*filters))
    ).unique().all()

    open_tasks = [task for task in tasks if task.status not in {TaskStatus.DONE, TaskStatus.CANCELLED}]
    completed = [task for task in tasks if task.status == TaskStatus.DONE and task.completed_at]
    completed_today = [task for task in completed if task.completed_at and task.completed_at >= today_start]
    completed_7d = [task for task in completed if task.completed_at and task.completed_at >= seven_days_ago]
    overdue = [
        task
        for task in open_tasks
        if task.due_date is not None and task.due_date < today_start
    ]
    due_today = [
        task
        for task in open_tasks
        if task.due_date is not None and today_start <= task.due_date < tomorrow_start
    ]

    completion_hours = [
        (task.completed_at - task.created_at).total_seconds() / 3600
        for task in completed
        if task.completed_at and task.created_at
    ]
    tasks_with_due_completed = [task for task in completed if task.due_date and task.completed_at]
    on_time_total = sum(1 for task in tasks_with_due_completed if task.completed_at <= task.due_date)

    owner_map: dict[str, TaskMetricsOwnerOut] = {}
    for task in tasks:
        owner_id = str(task.assigned_to_user_id) if task.assigned_to_user_id else "unassigned"
        owner_name = getattr(task.assigned_user, "full_name", None) or "Sem responsavel"
        entry = owner_map.setdefault(
            owner_id,
            TaskMetricsOwnerOut(user_id=task.assigned_to_user_id, owner_name=owner_name),
        )
        if task.status not in {TaskStatus.DONE, TaskStatus.CANCELLED}:
            entry.open_total += 1
        if task in overdue:
            entry.overdue_total += 1
        if task in completed_7d:
            entry.completed_7d_total += 1

    source_counts: dict[str, int] = {}
    outcome_counts: dict[str, int] = {}
    for task in tasks:
        extra = _task_extra(task)
        source = str(extra.get("source") or "manual")
        source_counts[source] = source_counts.get(source, 0) + 1
        outcome = str(extra.get("work_queue_outcome") or "pending")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    return TaskMetricsOut(
        open_total=len(open_tasks),
        overdue_total=len(overdue),
        due_today_total=len(due_today),
        completed_today_total=len(completed_today),
        completed_7d_total=len(completed_7d),
        avg_completion_hours=round(sum(completion_hours) / len(completion_hours), 1) if completion_hours else None,
        on_time_rate_pct=round((on_time_total / len(tasks_with_due_completed)) * 100, 1) if tasks_with_due_completed else None,
        by_owner=sorted(owner_map.values(), key=lambda item: (item.overdue_total, item.open_total), reverse=True),
        by_source=[
            TaskMetricsBreakdownOut(key=key, label=key.replace("_", " ").title(), total=value)
            for key, value in sorted(source_counts.items(), key=lambda item: item[1], reverse=True)
        ],
        by_outcome=[
            TaskMetricsBreakdownOut(key=key, label=key.replace("_", " ").title(), total=value)
            for key, value in sorted(outcome_counts.items(), key=lambda item: item[1], reverse=True)
        ],
    )


_OPERATIONAL_CLEANUP_CUTOFF_DAYS = 14
_ARCHIVE_PROTECTED_SOURCES = {"delinquency", "automation_journey"}
_ARCHIVE_PROTECTED_DOMAINS = {"finance"}
_ACTIVE_ONBOARDING_SOURCES = {"onboarding"}


def _source_label(task: Task) -> str:
    source = str(_task_extra(task).get("source") or "manual").strip().lower()
    return source or "manual"


def _has_recorded_outcome(task: Task) -> bool:
    extra = _task_extra(task)
    last_event = extra.get("last_task_event")
    last_outcome = last_event.get("outcome") if isinstance(last_event, dict) else None
    return bool(extra.get("work_queue_outcome") or last_outcome)


def _is_active_onboarding_d0_d30(task: Task, now: datetime) -> bool:
    if _source_label(task) not in _ACTIVE_ONBOARDING_SOURCES:
        return False
    member = getattr(task, "member", None)
    join_date = getattr(member, "join_date", None)
    if join_date is None:
        return False
    days_since_join = (now.date() - join_date).days
    status_value = str(getattr(member, "onboarding_status", "") or "").lower()
    return 0 <= days_since_join <= 30 and status_value in {"active", "at_risk", ""}


def _is_cleanup_candidate(task: Task, now: datetime) -> bool:
    if task.status != TaskStatus.TODO or task.due_date is not None or is_task_operationally_archived(task):
        return False
    if not task.created_at or task.created_at > now - timedelta(days=_OPERATIONAL_CLEANUP_CUTOFF_DAYS):
        return False
    extra = _task_extra(task)
    source = _source_label(task)
    domain = str(extra.get("domain") or "").strip().lower()
    if source in _ARCHIVE_PROTECTED_SOURCES or domain in _ARCHIVE_PROTECTED_DOMAINS:
        return False
    if _has_recorded_outcome(task):
        return False
    if _is_active_onboarding_d0_d30(task, now):
        return False
    return True


def _cleanup_candidates(db: Session, *, current_user: User, now: datetime) -> list[Task]:
    cutoff = now - timedelta(days=_OPERATIONAL_CLEANUP_CUTOFF_DAYS)
    db_filters = [
        Task.gym_id == current_user.gym_id,
        Task.deleted_at.is_(None),
        Task.status == TaskStatus.TODO,
        Task.due_date.is_(None),
        Task.created_at <= cutoff,
        _operational_archive_filter(),
        func.lower(func.coalesce(Task.extra_data["source"].astext, "")).notin_(tuple(_ARCHIVE_PROTECTED_SOURCES)),
        func.lower(func.coalesce(Task.extra_data["domain"].astext, "")).notin_(tuple(_ARCHIVE_PROTECTED_DOMAINS)),
        func.coalesce(Task.extra_data["work_queue_outcome"].astext, "") == "",
    ]
    tasks = db.scalars(
        select(Task)
        .options(joinedload(Task.member), joinedload(Task.lead))
        .where(and_(*db_filters))
        .order_by(Task.created_at.asc())
    ).unique().all()
    return [task for task in tasks if _is_cleanup_candidate(task, now)]


def _cleanup_preview_from_tasks(tasks: list[Task]) -> TaskOperationalCleanupPreviewOut:
    source_counts: dict[str, int] = {}
    oldest_created_at: datetime | None = None
    for task in tasks:
        source = _source_label(task)
        source_counts[source] = source_counts.get(source, 0) + 1
        if task.created_at and (oldest_created_at is None or task.created_at < oldest_created_at):
            oldest_created_at = task.created_at
    return TaskOperationalCleanupPreviewOut(
        candidate_total=len(tasks),
        cutoff_days=_OPERATIONAL_CLEANUP_CUTOFF_DAYS,
        oldest_created_at=oldest_created_at,
        by_source=[
            TaskMetricsBreakdownOut(key=key, label=key.replace("_", " ").title(), total=value)
            for key, value in sorted(source_counts.items(), key=lambda item: item[1], reverse=True)
        ],
    )


def preview_operational_task_cleanup(db: Session, *, current_user: User) -> TaskOperationalCleanupPreviewOut:
    now = datetime.now(tz=timezone.utc)
    tasks = _cleanup_candidates(db, current_user=current_user, now=now)
    return _cleanup_preview_from_tasks(tasks)


def apply_operational_task_cleanup(
    db: Session,
    *,
    current_user: User,
    reason: str,
    commit: bool = True,
) -> TaskOperationalCleanupApplyOut:
    from app.services.task_event_service import record_task_event

    now = datetime.now(tz=timezone.utc)
    batch_id = str(uuid4())
    tasks = _cleanup_candidates(db, current_user=current_user, now=now)
    preview = _cleanup_preview_from_tasks(tasks)
    for task in tasks:
        extra = _task_extra(task)
        extra["operational_archive"] = {
            "archived_at": now.isoformat(),
            "archived_by_user_id": str(current_user.id),
            "reason": reason,
            "batch_id": batch_id,
        }
        task.extra_data = extra
        db.add(task)
        record_task_event(
            db,
            task=task,
            current_user=current_user,
            event_type="status_changed",
            note=f"Arquivada da fila operacional: {reason}",
            metadata_json={"source": "operational_cleanup", "batch_id": batch_id},
            flush=False,
        )
    if tasks:
        invalidate_dashboard_cache("tasks")
    if commit:
        db.commit()
    else:
        db.flush()
    return TaskOperationalCleanupApplyOut(
        candidate_total=preview.candidate_total,
        cutoff_days=preview.cutoff_days,
        oldest_created_at=preview.oldest_created_at,
        by_source=preview.by_source,
        archived_total=len(tasks),
        batch_id=batch_id,
    )


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
