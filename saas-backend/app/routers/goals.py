from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import APIMessage
from app.schemas.goal import GoalCreate, GoalOut, GoalProgressOut, GoalUpdate
from app.services.audit_service import log_audit_event
from app.services.goal_service import create_goal, delete_goal, list_goal_progress, list_goals, update_goal


router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/", response_model=list[GoalOut])
def list_goals_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    active_only: bool = False,
) -> list[GoalOut]:
    return [GoalOut.model_validate(item) for item in list_goals(db, active_only=active_only)]


@router.post("/", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal_endpoint(
    request: Request,
    payload: GoalCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> GoalOut:
    goal = create_goal(db, payload)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="goal_created",
        entity="goal",
        user=current_user,
        entity_id=goal.id,
        details={"metric_type": goal.metric_type, "target_value": float(goal.target_value)},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return GoalOut.model_validate(goal)


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal_endpoint(
    request: Request,
    goal_id: UUID,
    payload: GoalUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> GoalOut:
    goal = update_goal(db, goal_id, payload)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="goal_updated",
        entity="goal",
        user=current_user,
        entity_id=goal.id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return GoalOut.model_validate(goal)


@router.delete("/{goal_id}", response_model=APIMessage)
def delete_goal_endpoint(
    request: Request,
    goal_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> APIMessage:
    delete_goal(db, goal_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="goal_deleted",
        entity="goal",
        user=current_user,
        entity_id=goal_id,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return APIMessage(message="Meta removida")


@router.get("/progress", response_model=list[GoalProgressOut])
def goal_progress_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
    active_only: bool = True,
) -> list[GoalProgressOut]:
    return list_goal_progress(db, active_only=active_only)
