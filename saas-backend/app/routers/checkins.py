from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import CheckinCreate, CheckinOut
from app.services.checkin_service import create_checkin


router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.post("/", response_model=CheckinOut, status_code=status.HTTP_201_CREATED)
def create_checkin_endpoint(
    payload: CheckinCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> CheckinOut:
    try:
        return create_checkin(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
