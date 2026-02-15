from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import NPSResponse, RoleEnum, User
from app.schemas import APIMessage, NPSEvolutionPoint, NPSResponseCreate, NPSResponseOut
from app.services.audit_service import log_audit_event
from app.services.nps_service import create_response, detractors_alerts, nps_evolution, run_nps_dispatch


router = APIRouter(prefix="/nps", tags=["nps"])


@router.post("/responses", response_model=NPSResponseOut, status_code=status.HTTP_201_CREATED)
def create_response_endpoint(
    request: Request,
    payload: NPSResponseCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> NPSResponse:
    response = create_response(db, payload)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="nps_response_created",
        entity="nps_response",
        user=current_user,
        member_id=response.member_id,
        entity_id=response.id,
        details={"score": response.score, "trigger": response.trigger.value},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return response


@router.post("/dispatch", response_model=dict[str, int])
def dispatch_nps_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> dict[str, int]:
    result = run_nps_dispatch(db)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="nps_dispatch_run",
        entity="nps",
        user=current_user,
        details=result,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return result


@router.get("/evolution", response_model=list[NPSEvolutionPoint])
def nps_evolution_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
    months: int = Query(12, ge=1, le=24),
) -> list[NPSEvolutionPoint]:
    return nps_evolution(db, months=months)


@router.get("/detractors", response_model=list[NPSResponseOut])
def detractors_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
    days: int = Query(30, ge=1, le=365),
) -> list[NPSResponse]:
    return detractors_alerts(db, days)
