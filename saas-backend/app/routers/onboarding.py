from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import OnboardingCockpitOut
from app.services.onboarding_cockpit_service import build_onboarding_cockpit

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/cockpit", response_model=OnboardingCockpitOut)
def get_onboarding_cockpit_endpoint(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER)),
    ],
) -> OnboardingCockpitOut:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return build_onboarding_cockpit(db, gym_id=current_user.gym_id)
