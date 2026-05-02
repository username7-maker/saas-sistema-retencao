from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.automation_journey import (
    AutomationJourneyActivationOut,
    AutomationJourneyCreate,
    AutomationJourneyEnrollmentOut,
    AutomationJourneyOut,
    AutomationJourneyPreviewOut,
    AutomationJourneyTemplateOut,
    AutomationJourneyUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.automation_journey_service import (
    activate_journey,
    create_journey_from_template,
    get_journey_or_none,
    list_enrollments,
    list_journey_templates,
    list_journeys,
    pause_journey,
    preview_journey,
    update_journey,
)

router = APIRouter(prefix="/automation-journeys", tags=["automation-journeys"])

MANAGER_ROLES = (RoleEnum.OWNER, RoleEnum.MANAGER)
VIEW_ROLES = (RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST)


def _journey_or_404(db: Session, *, journey_id: UUID, gym_id: UUID):
    journey = get_journey_or_none(db, journey_id=journey_id, gym_id=gym_id)
    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jornada nao encontrada")
    return journey


@router.get("/templates", response_model=list[AutomationJourneyTemplateOut])
def list_templates_endpoint(
    _: Annotated[User, Depends(require_roles(*VIEW_ROLES))],
) -> list[AutomationJourneyTemplateOut]:
    return list_journey_templates()


@router.get("", response_model=list[AutomationJourneyOut])
def list_journeys_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*VIEW_ROLES))],
) -> list[AutomationJourneyOut]:
    return list_journeys(db, gym_id=current_user.gym_id)


@router.post("", response_model=AutomationJourneyOut, status_code=status.HTTP_201_CREATED)
def create_journey_endpoint(
    request: Request,
    payload: AutomationJourneyCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*MANAGER_ROLES))],
) -> AutomationJourneyOut:
    if not payload.template_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="template_id e obrigatorio na V1")
    journey = create_journey_from_template(
        db,
        gym_id=current_user.gym_id,
        template_id=payload.template_id,
        current_user=current_user,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="automation_journey_created",
        entity="automation_journey",
        user=current_user,
        entity_id=journey.id,
        details={"template_id": payload.template_id},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return journey


@router.patch("/{journey_id}", response_model=AutomationJourneyOut)
def update_journey_endpoint(
    request: Request,
    journey_id: UUID,
    payload: AutomationJourneyUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*MANAGER_ROLES))],
) -> AutomationJourneyOut:
    journey = _journey_or_404(db, journey_id=journey_id, gym_id=current_user.gym_id)
    result = update_journey(db, journey=journey, data=payload.model_dump(exclude_unset=True), current_user=current_user)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="automation_journey_updated",
        entity="automation_journey",
        user=current_user,
        entity_id=journey.id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result


@router.post("/{journey_id}/preview", response_model=AutomationJourneyPreviewOut)
def preview_existing_journey_endpoint(
    journey_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*VIEW_ROLES))],
) -> AutomationJourneyPreviewOut:
    journey = _journey_or_404(db, journey_id=journey_id, gym_id=current_user.gym_id)
    return preview_journey(db, gym_id=current_user.gym_id, journey=journey)


@router.post("/preview", response_model=AutomationJourneyPreviewOut)
def preview_template_endpoint(
    payload: AutomationJourneyCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*VIEW_ROLES))],
) -> AutomationJourneyPreviewOut:
    if not payload.template_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="template_id e obrigatorio")
    return preview_journey(db, gym_id=current_user.gym_id, template_id=payload.template_id)


@router.post("/{journey_id}/activate", response_model=AutomationJourneyActivationOut)
def activate_journey_endpoint(
    request: Request,
    journey_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*MANAGER_ROLES))],
) -> AutomationJourneyActivationOut:
    journey = _journey_or_404(db, journey_id=journey_id, gym_id=current_user.gym_id)
    result = activate_journey(db, journey=journey, current_user=current_user)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="automation_journey_activated",
        entity="automation_journey",
        user=current_user,
        entity_id=journey.id,
        details={"enrolled_count": result.enrolled_count, "skipped_existing_count": result.skipped_existing_count},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result


@router.post("/{journey_id}/pause", response_model=AutomationJourneyOut)
def pause_journey_endpoint(
    request: Request,
    journey_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*MANAGER_ROLES))],
) -> AutomationJourneyOut:
    journey = _journey_or_404(db, journey_id=journey_id, gym_id=current_user.gym_id)
    result = pause_journey(db, journey=journey, current_user=current_user)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="automation_journey_paused",
        entity="automation_journey",
        user=current_user,
        entity_id=journey.id,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result


@router.get("/{journey_id}/enrollments", response_model=list[AutomationJourneyEnrollmentOut])
def list_journey_enrollments_endpoint(
    journey_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*VIEW_ROLES))],
    limit: int = Query(100, ge=1, le=500),
) -> list[AutomationJourneyEnrollmentOut]:
    journey = _journey_or_404(db, journey_id=journey_id, gym_id=current_user.gym_id)
    if journey.domain in {"finance", "commercial"} and current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jornada nao encontrada")
    return list_enrollments(db, journey=journey, limit=limit)
