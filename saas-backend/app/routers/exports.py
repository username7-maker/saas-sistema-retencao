from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.services.audit_service import log_audit_event
from app.services.export_service import (
    export_checkins_csv,
    export_checkins_template_csv,
    export_members_csv,
    export_members_template_csv,
)


router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/members.csv")
def export_members_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> StreamingResponse:
    buffer, filename = export_members_csv(db)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="members_csv_exported",
        entity="members",
        user=current_user,
        details={"filename": filename},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return _csv_download_response(buffer, filename)


@router.get("/checkins.csv")
def export_checkins_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    date_from: date | None = None,
    date_to: date | None = None,
) -> StreamingResponse:
    buffer, filename = export_checkins_csv(db, date_from=date_from, date_to=date_to)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="checkins_csv_exported",
        entity="checkins",
        user=current_user,
        details={"filename": filename, "date_from": str(date_from or ""), "date_to": str(date_to or "")},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return _csv_download_response(buffer, filename)


@router.get("/templates/members.csv")
def export_members_template_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> StreamingResponse:
    buffer, filename = export_members_template_csv()
    return _csv_download_response(buffer, filename)


@router.get("/templates/checkins.csv")
def export_checkins_template_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> StreamingResponse:
    buffer, filename = export_checkins_template_csv()
    return _csv_download_response(buffer, filename)


def _csv_download_response(buffer, filename: str) -> StreamingResponse:
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
