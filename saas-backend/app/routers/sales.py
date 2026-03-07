from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.sales import BookingStatusOut, CallEventCreate, CallEventResponse, CallScriptOut, SalesBriefOut
from app.services.booking_service import get_booking_status
from app.services.call_script_service import get_call_script, register_call_event, send_lead_proposal_background
from app.services.sales_brief_service import get_sales_brief


router = APIRouter(tags=["sales"])


@router.get("/leads/{lead_id}/sales-brief", response_model=SalesBriefOut)
def sales_brief_endpoint(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> SalesBriefOut:
    return SalesBriefOut.model_validate(get_sales_brief(db, lead_id))


@router.get("/leads/{lead_id}/call-script", response_model=CallScriptOut)
def call_script_endpoint(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> CallScriptOut:
    return CallScriptOut.model_validate(get_call_script(db, lead_id))


@router.post("/leads/{lead_id}/call-events", response_model=CallEventResponse)
def call_event_endpoint(
    lead_id: UUID,
    payload: CallEventCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> CallEventResponse:
    lead = register_call_event(db, lead_id=lead_id, payload=payload)
    if payload.event_type.strip().lower() == "proposal_requested":
        background_tasks.add_task(send_lead_proposal_background, lead.id)
    return CallEventResponse(message="Evento registrado", lead_id=lead.id, stage=lead.stage.value)


@router.get("/leads/{lead_id}/booking-status", response_model=BookingStatusOut)
def booking_status_endpoint(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> BookingStatusOut:
    return BookingStatusOut.model_validate(get_booking_status(db, lead_id))
