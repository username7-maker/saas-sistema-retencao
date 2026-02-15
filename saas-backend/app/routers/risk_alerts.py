from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RiskLevel, RoleEnum, User
from app.schemas import PaginatedResponse, RiskAlertOut, RiskAlertResolveInput
from app.services.risk_alert_service import list_risk_alerts, resolve_risk_alert


router = APIRouter(prefix="/risk-alerts", tags=["risk-alerts"])


@router.get("/", response_model=PaginatedResponse[RiskAlertOut])
def list_risk_alerts_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: RiskLevel | None = None,
    resolved: bool | None = None,
) -> PaginatedResponse[RiskAlertOut]:
    return list_risk_alerts(
        db,
        page=page,
        page_size=page_size,
        level=level,
        resolved=resolved,
    )


@router.patch("/{alert_id}/resolve", response_model=RiskAlertOut)
def resolve_risk_alert_endpoint(
    alert_id: UUID,
    payload: RiskAlertResolveInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> RiskAlertOut:
    return resolve_risk_alert(
        db,
        alert_id=alert_id,
        current_user=current_user,
        resolution_note=payload.resolution_note,
    )
