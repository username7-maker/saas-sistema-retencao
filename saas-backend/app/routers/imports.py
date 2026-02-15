from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import ImportSummary
from app.services.audit_service import log_audit_event
from app.services.import_service import import_checkins_csv, import_members_csv


router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/members", response_model=ImportSummary)
async def import_members_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
) -> ImportSummary:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV")
    content = await file.read()
    summary = import_members_csv(db, content)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="import_members_csv",
        entity="members",
        user=current_user,
        details={"imported": summary.imported, "duplicates": summary.skipped_duplicates, "errors": len(summary.errors)},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return summary


@router.post("/checkins", response_model=ImportSummary)
async def import_checkins_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
) -> ImportSummary:
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV")
    content = await file.read()
    summary = import_checkins_csv(db, content)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="import_checkins_csv",
        entity="checkins",
        user=current_user,
        details={"imported": summary.imported, "duplicates": summary.skipped_duplicates, "errors": len(summary.errors)},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return summary
