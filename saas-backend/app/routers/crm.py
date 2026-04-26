from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import LeadStage, RoleEnum, User
from app.schemas import (
    APIMessage,
    AcquisitionCaptureInput,
    AcquisitionCaptureResponse,
    AcquisitionLeadSummaryOut,
    LeadCreate,
    LeadNoteCreate,
    LeadOut,
    LeadUpdate,
    GrowthAudienceOut,
    GrowthOpportunityPrepareInput,
    GrowthOpportunityPreparedOut,
    PaginatedResponse,
)
from app.services.acquisition_service import (
    capture_acquisition_lead,
    get_acquisition_lead_summary,
    list_acquisition_lead_summaries,
)
from app.services.audit_service import log_audit_event
from app.services.crm_service import (
    append_lead_note_entry,
    create_lead,
    delete_lead,
    dispatch_lead_post_commit_effects,
    list_leads,
    run_followup_automation,
    update_lead,
)
from app.services.growth_service import list_growth_audiences, prepare_growth_opportunity


router = APIRouter(prefix="/crm", tags=["crm"])


@router.post("/leads", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead_endpoint(
    request: Request,
    payload: LeadCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> LeadOut:
    lead = create_lead(db, payload, gym_id=current_user.gym_id, commit=False)
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
    dispatch_lead_post_commit_effects(lead)
    return lead


@router.post("/acquisition/capture", response_model=AcquisitionCaptureResponse, status_code=status.HTTP_201_CREATED)
def capture_acquisition_lead_endpoint(
    request: Request,
    payload: AcquisitionCaptureInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON, RoleEnum.RECEPTIONIST)),
    ],
) -> AcquisitionCaptureResponse:
    result = capture_acquisition_lead(db, payload, gym_id=current_user.gym_id, commit=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="lead_acquisition_captured",
        entity="lead",
        user=current_user,
        entity_id=result.lead.id,
        details={
            "source": result.summary.source,
            "channel": result.summary.channel,
            "campaign": result.summary.campaign,
            "qualification_score": result.qualification.score,
            "qualification_label": result.qualification.label,
            "scheduled_for": result.summary.next_booking_at.isoformat() if result.summary.next_booking_at else None,
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return result


@router.get("/acquisition/summary", response_model=list[AcquisitionLeadSummaryOut])
def list_acquisition_summaries_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON, RoleEnum.RECEPTIONIST)),
    ],
) -> list[AcquisitionLeadSummaryOut]:
    return list_acquisition_lead_summaries(db, gym_id=current_user.gym_id)


@router.get("/leads/{lead_id}/acquisition-summary", response_model=AcquisitionLeadSummaryOut)
def get_acquisition_summary_endpoint(
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON, RoleEnum.RECEPTIONIST)),
    ],
) -> AcquisitionLeadSummaryOut:
    return get_acquisition_lead_summary(db, lead_id, gym_id=current_user.gym_id)


@router.get("/growth/audiences", response_model=list[GrowthAudienceOut])
def list_growth_audiences_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON, RoleEnum.RECEPTIONIST)),
    ],
    limit_per_audience: int = Query(25, ge=1, le=100),
) -> list[GrowthAudienceOut]:
    return list_growth_audiences(db, gym_id=current_user.gym_id, limit_per_audience=limit_per_audience)


@router.post("/growth/opportunities/{opportunity_id}/prepare", response_model=GrowthOpportunityPreparedOut)
def prepare_growth_opportunity_endpoint(
    request: Request,
    opportunity_id: str,
    payload: GrowthOpportunityPrepareInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON, RoleEnum.RECEPTIONIST)),
    ],
) -> GrowthOpportunityPreparedOut:
    prepared = prepare_growth_opportunity(
        db,
        gym_id=current_user.gym_id,
        opportunity_id=opportunity_id,
        payload=payload,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_role=current_user.role.value,
        commit=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="growth_opportunity_prepared",
        entity="growth_opportunity",
        user=current_user,
        details={
            "opportunity_id": prepared.opportunity_id,
            "channel": prepared.channel,
            "prepared_action": prepared.prepared_action,
            "task_id": str(prepared.task_id) if prepared.task_id else None,
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return prepared


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
    lead = update_lead(db, lead_id, payload, gym_id=current_user.gym_id, commit=False)
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
    dispatch_lead_post_commit_effects(lead)
    return lead


@router.post("/leads/{lead_id}/notes", response_model=LeadOut)
def append_lead_note_endpoint(
    request: Request,
    lead_id: UUID,
    payload: LeadNoteCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON))],
) -> LeadOut:
    lead = append_lead_note_entry(
        db,
        lead_id,
        payload,
        author_id=current_user.id,
        author_name=current_user.full_name,
        author_role=current_user.role.value,
        commit=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="lead_note_appended",
        entity="lead",
        user=current_user,
        entity_id=lead.id,
        details={"entry_type": payload.entry_type, "channel": payload.channel, "outcome": payload.outcome},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return lead


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead_endpoint(
    request: Request,
    lead_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> None:
    delete_lead(db, lead_id, commit=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="lead_deleted",
        entity="lead",
        user=current_user,
        entity_id=lead_id,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()


@router.post("/automation/followup", response_model=APIMessage)
def run_followup_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> APIMessage:
    created = run_followup_automation(db, commit=False)
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
