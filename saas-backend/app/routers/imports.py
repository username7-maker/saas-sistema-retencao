from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.core.limiter import limiter
from app.database import get_db, set_current_gym_id
from app.models import RoleEnum, User
from app.schemas import ImportSummary
from app.services.audit_service import log_audit_event
from app.services.import_service import import_checkins_csv, import_members_csv


router = APIRouter(prefix="/imports", tags=["imports"])

_MAX_CSV_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = (".csv", ".xlsx")


@router.post("/members", response_model=ImportSummary)
@limiter.limit("5/minute")
async def import_members_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
) -> ImportSummary:
    lower_filename = (file.filename or "").lower()
    if not lower_filename.endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV ou XLSX")
    set_current_gym_id(current_user.gym_id)
    content = await file.read(_MAX_CSV_SIZE + 1)
    if len(content) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 10 MB")
    try:
        summary = import_members_csv(db, content, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
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
@limiter.limit("5/minute")
async def import_checkins_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
) -> ImportSummary:
    lower_filename = (file.filename or "").lower()
    if not lower_filename.endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV ou XLSX")
    set_current_gym_id(current_user.gym_id)
    content = await file.read(_MAX_CSV_SIZE + 1)
    if len(content) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 10 MB")
    try:
        summary = import_checkins_csv(db, content, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
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
