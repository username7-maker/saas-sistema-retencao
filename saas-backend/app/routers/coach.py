from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.coach import CoachWorkspaceOut
from app.services.coach_workspace_service import get_coach_workspace

router = APIRouter(prefix="/coach", tags=["coach"])

CoachStateFilter = Literal["do_now", "awaiting_outcome", "done", "all"]
CoachShiftFilter = Literal["my_shift", "all", "overnight", "morning", "afternoon", "evening", "unassigned"]


@router.get("/workspace", response_model=CoachWorkspaceOut)
def get_coach_workspace_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
    state: CoachStateFilter = Query("do_now"),
    shift: CoachShiftFilter = Query("my_shift"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> CoachWorkspaceOut:
    return get_coach_workspace(
        db,
        current_user=current_user,
        state=state,
        shift=shift,
        page=page,
        page_size=page_size,
    )
