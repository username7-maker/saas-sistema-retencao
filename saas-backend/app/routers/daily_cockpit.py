from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.daily_cockpit import DailyCockpitResponse
from app.services.daily_cockpit_service import get_daily_cockpit


router = APIRouter(prefix="/cockpit", tags=["cockpit"])


@router.get("/daily", response_model=DailyCockpitResponse)
def daily_cockpit(
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
) -> DailyCockpitResponse:
    return get_daily_cockpit(db, gym_id=current_user.gym_id)
