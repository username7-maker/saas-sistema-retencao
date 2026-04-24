from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.sales import (
    BookingStatusOut,
    CallEventCreate,
    CallEventResponse,
    CallScriptOut,
    LeadProposalDispatchStatusRead,
    SalesBriefOut,
)
from app.services.booking_service import get_booking_status
from app.services.call_script_service import get_call_script, register_call_event
from app.services.core_async_job_service import enqueue_lead_proposal_dispatch_job, get_core_async_job, serialize_core_async_job
from app.services.crm_service import dispatch_lead_post_commit_effects
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
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> CallEventResponse:
    lead = register_call_event(db, lead_id=lead_id, payload=payload, commit=False)
    job_id: UUID | None = None
    job_status: str | None = None
    if payload.event_type.strip().lower() == "proposal_requested":
        job, _created = enqueue_lead_proposal_dispatch_job(
            db,
            gym_id=lead.gym_id,
            lead_id=lead.id,
            requested_by_user_id=current_user.id,
        )
        job_id = job.id
        job_status = job.status
        response.status_code = status.HTTP_202_ACCEPTED
    db.commit()
    dispatch_lead_post_commit_effects(lead)
    return CallEventResponse(message="Evento registrado", lead_id=lead.id, stage=lead.stage.value, job_id=job_id, job_status=job_status)


@router.get("/leads/{lead_id}/proposal-dispatches/{job_id}", response_model=LeadProposalDispatchStatusRead)
def proposal_dispatch_status_endpoint(
    lead_id: UUID,
    job_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> LeadProposalDispatchStatusRead:
    job = get_core_async_job(db, job_id=job_id, gym_id=current_user.gym_id)
    if not job or job.related_entity_type != "lead" or job.related_entity_id != lead_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job de proposta nao encontrado")

    serialized = serialize_core_async_job(job)
    return LeadProposalDispatchStatusRead(lead_id=lead_id, **serialized)


@router.get("/leads/{lead_id}/booking-status", response_model=BookingStatusOut)
def booking_status_endpoint(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> BookingStatusOut:
    return BookingStatusOut.model_validate(get_booking_status(db, lead_id))
