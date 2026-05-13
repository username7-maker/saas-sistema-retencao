from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import PaginatedResponse
from app.schemas.assessment_appointment import (
    AssessmentAppointmentCreate,
    AssessmentAppointmentOut,
    AssessmentAppointmentUpdate,
)
from app.services.assessment_appointment_service import (
    create_assessment_appointment,
    list_assessment_appointments,
    serialize_assessment_appointment,
    update_assessment_appointment,
)
from app.services.audit_service import log_audit_event


router = APIRouter(prefix="/assessment-appointments", tags=["assessment-appointments"])

READ_ROLES = (RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER)
WRITE_ROLES = (RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER)


@router.get("", response_model=PaginatedResponse[AssessmentAppointmentOut])
def list_assessment_appointments_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*READ_ROLES))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    payment_status: str | None = Query(default=None),
    evaluator_user_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None),
) -> PaginatedResponse[AssessmentAppointmentOut]:
    return list_assessment_appointments(
        db,
        gym_id=current_user.gym_id,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        status=status_filter,
        payment_status=payment_status,
        evaluator_user_id=evaluator_user_id,
        search=search,
    )


@router.post("", response_model=AssessmentAppointmentOut, status_code=status.HTTP_201_CREATED)
def create_assessment_appointment_endpoint(
    request: Request,
    payload: AssessmentAppointmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
) -> AssessmentAppointmentOut:
    try:
        appointment = create_assessment_appointment(
            db,
            gym_id=current_user.gym_id,
            payload=payload,
            created_by_user_id=current_user.id,
            commit=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    context = get_request_context(request)
    log_audit_event(
        db,
        action="assessment_appointment_created",
        entity="assessment_appointment",
        user=current_user,
        member_id=appointment.member_id,
        entity_id=appointment.id,
        details={"status": appointment.status, "payment_status": appointment.payment_status},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(appointment)
    return serialize_assessment_appointment(appointment)


@router.patch("/{appointment_id}", response_model=AssessmentAppointmentOut)
def update_assessment_appointment_endpoint(
    request: Request,
    appointment_id: UUID,
    payload: AssessmentAppointmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*WRITE_ROLES))],
) -> AssessmentAppointmentOut:
    try:
        appointment = update_assessment_appointment(
            db,
            appointment_id=appointment_id,
            gym_id=current_user.gym_id,
            payload=payload,
            updated_by_user_id=current_user.id,
            commit=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    context = get_request_context(request)
    log_audit_event(
        db,
        action="assessment_appointment_updated",
        entity="assessment_appointment",
        user=current_user,
        member_id=appointment.member_id,
        entity_id=appointment.id,
        details={"status": appointment.status, "payment_status": appointment.payment_status},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(appointment)
    return serialize_assessment_appointment(appointment)
