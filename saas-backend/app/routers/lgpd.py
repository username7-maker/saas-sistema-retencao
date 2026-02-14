from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import APIMessage, MemberOut
from app.services.lgpd_service import anonymize_member, export_member_pdf


router = APIRouter(prefix="/lgpd", tags=["lgpd"])


@router.get("/export/member/{member_id}")
def export_member_data(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> StreamingResponse:
    buffer, filename = export_member_pdf(db, member_id)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/anonymize/member/{member_id}", response_model=MemberOut)
def anonymize_member_data(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER))],
) -> MemberOut:
    return anonymize_member(db, member_id)


@router.get("/health", response_model=APIMessage)
def lgpd_health() -> APIMessage:
    return APIMessage(message="LGPD module online")
