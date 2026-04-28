from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import PaginatedResponse, WorkQueueActionResultOut, WorkQueueExecuteInput, WorkQueueItemOut, WorkQueueOutcomeInput
from app.services.work_queue_service import execute_work_queue_item, get_work_queue_item, list_work_queue_items, update_work_queue_outcome

router = APIRouter(prefix="/work-queue", tags=["work-queue"])

SourceType = Literal["task", "ai_triage"]
StateFilter = Literal["do_now", "awaiting_outcome", "done", "all"]
ShiftFilter = Literal["my_shift", "all", "morning", "afternoon", "evening", "unassigned"]
AssigneeFilter = Literal["mine", "unassigned", "all"]
DomainFilter = Literal["all", "retention", "onboarding", "assessment", "commercial", "finance", "manual"]
SourceFilter = Literal["all", "task", "ai_triage"]


@router.get("/items", response_model=PaginatedResponse[WorkQueueItemOut])
def list_work_queue_items_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
    state: StateFilter = Query("do_now"),
    shift: ShiftFilter = Query("my_shift"),
    assignee: AssigneeFilter = Query("all"),
    domain: DomainFilter = Query("all"),
    source: SourceFilter = Query("all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[WorkQueueItemOut]:
    payload = list_work_queue_items(
        db,
        current_user=current_user,
        state=state,
        shift=shift,
        assignee=assignee,
        domain=domain,
        source=source,
        page=page,
        page_size=page_size,
    )
    db.commit()
    return payload


@router.get("/items/{source_type}/{source_id}", response_model=WorkQueueItemOut)
def get_work_queue_item_endpoint(
    source_type: SourceType,
    source_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
) -> WorkQueueItemOut:
    return get_work_queue_item(db, current_user=current_user, source_type=source_type, source_id=source_id)


@router.post("/items/{source_type}/{source_id}/execute", response_model=WorkQueueActionResultOut)
def execute_work_queue_item_endpoint(
    source_type: SourceType,
    source_id: UUID,
    payload: WorkQueueExecuteInput,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
) -> WorkQueueActionResultOut:
    context = get_request_context(request)
    result = execute_work_queue_item(
        db,
        current_user=current_user,
        source_type=source_type,
        source_id=source_id,
        payload=payload,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return result


@router.patch("/items/{source_type}/{source_id}/outcome", response_model=WorkQueueActionResultOut)
def update_work_queue_item_outcome_endpoint(
    source_type: SourceType,
    source_id: UUID,
    payload: WorkQueueOutcomeInput,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
) -> WorkQueueActionResultOut:
    context = get_request_context(request)
    result = update_work_queue_outcome(
        db,
        current_user=current_user,
        source_type=source_type,
        source_id=source_id,
        payload=payload,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return result
