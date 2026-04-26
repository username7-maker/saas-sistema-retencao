from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import APIMessage, MemberConsentRecordCreate, MemberConsentRecordOut, MemberConsentSummaryOut, MemberOut
from app.services.audit_service import log_audit_event
from app.services.compliance_service import list_member_consent_records, record_member_consent
from app.services.lgpd_service import anonymize_member, export_member_pdf


router = APIRouter(prefix="/lgpd", tags=["lgpd"])


@router.get("/member/{member_id}/consents", response_model=MemberConsentSummaryOut)
def get_member_consents(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> MemberConsentSummaryOut:
    return list_member_consent_records(db, member_id, gym_id=current_user.gym_id)


@router.post("/member/{member_id}/consents", response_model=MemberConsentRecordOut, status_code=201)
def create_member_consent(
    request: Request,
    member_id: UUID,
    payload: MemberConsentRecordCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> MemberConsentRecordOut:
    record = record_member_consent(
        db,
        member_id,
        payload,
        gym_id=current_user.gym_id,
        actor_user_id=current_user.id,
        commit=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="member_consent_recorded",
        entity="member_consent_record",
        user=current_user,
        member_id=member_id,
        entity_id=record.id,
        details={
            "consent_type": record.consent_type,
            "status": record.status,
            "source": record.source,
            "document_version": record.document_version,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return record


@router.get("/export/member/{member_id}")
def export_member_data(
    request: Request,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> StreamingResponse:
    buffer, filename = export_member_pdf(db, member_id, current_user.gym_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="lgpd_export_member_pdf",
        entity="member",
        user=current_user,
        member_id=member_id,
        entity_id=member_id,
        details={"filename": filename},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/anonymize/member/{member_id}", response_model=MemberOut)
def anonymize_member_data(
    request: Request,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER))],
) -> MemberOut:
    member = anonymize_member(db, member_id, current_user.gym_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="lgpd_member_anonymized",
        entity="member",
        user=current_user,
        member_id=member_id,
        entity_id=member_id,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return member


@router.get("/health", response_model=APIMessage)
def lgpd_health() -> APIMessage:
    return APIMessage(message="LGPD module online")
