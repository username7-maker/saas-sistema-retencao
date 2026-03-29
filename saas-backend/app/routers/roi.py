from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import RoiSummaryOut
from app.services.roi_service import get_roi_summary

router = APIRouter(prefix="/roi", tags=["roi"])


@router.get("/summary", response_model=RoiSummaryOut)
def roi_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    period_days: int = Query(30, ge=7, le=365),
) -> RoiSummaryOut:
    return get_roi_summary(db, period_days)
