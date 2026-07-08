from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.commercial_funnel import WeeklyFunnelResponse
from app.services.commercial_funnel_service import get_weekly_funnel


router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get("/weekly-funnel", response_model=WeeklyFunnelResponse)
def weekly_funnel(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_roles(
                RoleEnum.OWNER,
                RoleEnum.MANAGER,
                RoleEnum.SALESPERSON,
                RoleEnum.RECEPTIONIST,
            )
        ),
    ],
    week_offset: int = Query(0, ge=-12, le=0),
) -> WeeklyFunnelResponse:
    return get_weekly_funnel(db, gym_id=current_user.gym_id, week_offset=week_offset)
