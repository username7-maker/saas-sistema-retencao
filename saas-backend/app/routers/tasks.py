from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, TaskStatus, User
from app.schemas import AIAssistantPayload, PaginatedResponse, TaskCreate, TaskOut, TaskUpdate
from app.services.audit_service import log_audit_event
from app.services.ai_assistant_service import build_task_assistant
from app.services.task_service import create_task, delete_task, get_task_with_relations_or_404, list_tasks, update_task


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task_endpoint(
    request: Request,
    payload: TaskCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
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
) -> PaginatedResponse[TaskOut]:
    return list_tasks(
        db,
        page=page,
        page_size=page_size,
        status=status,
        assigned_to_user_id=assigned_to_user_id,
        current_user=current_user,
        include_retention=include_retention,
    )


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
