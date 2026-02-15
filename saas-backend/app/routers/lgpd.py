from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import APIMessage, MemberOut
from app.services.audit_service import log_audit_event
from app.services.lgpd_service import anonymize_member, export_member_pdf


router = APIRouter(prefix="/lgpd", tags=["lgpd"])


@router.get("/export/member/{member_id}")
def export_member_data(
    request: Request,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> StreamingResponse:
    buffer, filename = export_member_pdf(db, member_id)
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
    member = anonymize_member(db, member_id)
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
