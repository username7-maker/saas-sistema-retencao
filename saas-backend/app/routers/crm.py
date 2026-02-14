from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import LeadStage, RoleEnum, User
from app.schemas import APIMessage, LeadCreate, LeadOut, LeadUpdate, PaginatedResponse
from app.services.crm_service import create_lead, list_leads, run_followup_automation, update_lead


router = APIRouter(prefix="/crm", tags=["crm"])


@router.post("/leads", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead_endpoint(
    payload: LeadCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> LeadOut:
    return create_lead(db, payload)


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
    lead_id: UUID,
    payload: LeadUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> LeadOut:
    return update_lead(db, lead_id, payload)


@router.post("/automation/followup", response_model=APIMessage)
def run_followup_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> APIMessage:
    created = run_followup_automation(db)
    return APIMessage(message=f"{created} tarefas de follow-up geradas")
