from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, TaskPriority, TaskStatus, User
from app.schemas import AIAssistantPayload, PaginatedResponse, TaskCreate, TaskEventCreate, TaskEventOut, TaskMetricsOut, TaskOut, TaskUpdate
from app.services.audit_service import log_audit_event
from app.services.ai_assistant_service import build_task_assistant
from app.services.task_event_service import create_task_event, list_task_events
from app.services.task_service import create_task, delete_task, get_task_metrics, get_task_with_relations_or_404, list_tasks, update_task


router = APIRouter(prefix="/tasks", tags=["tasks"])
DueFilter = Literal["overdue", "today", "upcoming"]


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task_endpoint(
    request: Request,
    payload: TaskCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON)),
    ],
) -> TaskOut:
    task = create_task(db, payload, gym_id=current_user.gym_id, commit=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="task_created",
        entity="task",
        user=current_user,
        member_id=task.member_id,
        entity_id=task.id,
        details={"status": task.status.value, "priority": task.priority.value},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return task


@router.get("/", response_model=PaginatedResponse[TaskOut])
def list_tasks_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: TaskStatus | None = None,
    assigned_to_user_id: UUID | None = None,
    include_retention: bool = Query(False),
    q: str | None = Query(None),
    priority: TaskPriority | None = None,
    source: str | None = Query(None),
    due: DueFilter | None = Query(None),
    unassigned: bool | None = Query(None),
    member_id: UUID | None = None,
    lead_id: UUID | None = None,
    preferred_shift: str | None = Query(None),
    plan_name: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
) -> PaginatedResponse[TaskOut]:
    return list_tasks(
        db,
        page=page,
        page_size=page_size,
        status=status,
        assigned_to_user_id=assigned_to_user_id,
        current_user=current_user,
        include_retention=include_retention,
        q=q,
        priority=priority,
        source=source,
        due=due,
        unassigned=unassigned,
        member_id=member_id,
        lead_id=lead_id,
        preferred_shift=preferred_shift,
        plan_name=plan_name,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/metrics", response_model=TaskMetricsOut)
def task_metrics_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
) -> TaskMetricsOut:
    return get_task_metrics(db, current_user=current_user)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task_endpoint(
    request: Request,
    task_id: UUID,
    payload: TaskUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
) -> TaskOut:
    task = update_task(db, task_id, payload, current_user=current_user, commit=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="task_updated",
        entity="task",
        user=current_user,
        member_id=task.member_id,
        entity_id=task.id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys()), "status": task.status.value},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return task


@router.get("/{task_id}/events", response_model=list[TaskEventOut])
def list_task_events_endpoint(
    task_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
) -> list[TaskEventOut]:
    return list_task_events(db, task_id=task_id, current_user=current_user)


@router.post("/{task_id}/events", response_model=TaskEventOut, status_code=status.HTTP_201_CREATED)
def create_task_event_endpoint(
    request: Request,
    task_id: UUID,
    payload: TaskEventCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
) -> TaskEventOut:
    event = create_task_event(db, task_id=task_id, payload=payload, current_user=current_user, commit=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="task_event_created",
        entity="task_event",
        user=current_user,
        member_id=event.member_id,
        entity_id=event.id,
        details={"task_id": str(task_id), "event_type": event.event_type, "outcome": event.outcome},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return event


@router.get("/{task_id}/assistant", response_model=AIAssistantPayload)
def task_assistant_endpoint(
    task_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
) -> AIAssistantPayload:
    task = get_task_with_relations_or_404(db, task_id)
    if task.gym_id != current_user.gym_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task nao encontrada")
    return build_task_assistant(db, task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_endpoint(
    request: Request,
    task_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> None:
    delete_task(db, task_id, commit=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="task_deleted",
        entity="task",
        user=current_user,
        entity_id=task_id,
        details={},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
