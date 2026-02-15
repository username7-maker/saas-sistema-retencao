from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import LeadStage, RoleEnum, User
from app.schemas import APIMessage, LeadCreate, LeadOut, LeadUpdate, PaginatedResponse
from app.services.audit_service import log_audit_event
from app.services.crm_service import create_lead, list_leads, run_followup_automation, update_lead


router = APIRouter(prefix="/crm", tags=["crm"])


@router.post("/leads", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead_endpoint(
    request: Request,
    payload: LeadCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> LeadOut:
    lead = create_lead(db, payload)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="lead_created",
        entity="lead",
        user=current_user,
        entity_id=lead.id,
        details={"stage": lead.stage.value, "source": lead.source},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return lead


@router.get("/leads", response_model=PaginatedResponse[LeadOut])
def list_leads_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON, RoleEnum.RECEPTIONIST))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    stage: LeadStage | None = None,
) -> PaginatedResponse[LeadOut]:
    return list_leads(db, page=page, page_size=page_size, stage=stage)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead_endpoint(
    request: Request,
    lead_id: UUID,
    payload: LeadUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> LeadOut:
    lead = update_lead(db, lead_id, payload)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="lead_updated",
        entity="lead",
        user=current_user,
        entity_id=lead.id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys()), "stage": lead.stage.value},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return lead


@router.post("/automation/followup", response_model=APIMessage)
def run_followup_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> APIMessage:
    created = run_followup_automation(db)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="crm_followup_automation_run",
        entity="lead",
        user=current_user,
        details={"tasks_created": created},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return APIMessage(message=f"{created} tarefas de follow-up geradas")
