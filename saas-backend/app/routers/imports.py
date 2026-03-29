import logging
import threading
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_request_context, require_roles
from app.core.distributed_lock import with_distributed_lock
from app.core.limiter import limiter
from app.database import SessionLocal, clear_current_gym_id, get_db, set_current_gym_id
from app.models import RoleEnum, User
from app.schemas import ImportPreview, ImportSummary
from app.services.audit_service import log_audit_event
from app.services.import_service import (
    import_assessments_csv,
    import_checkins_csv,
    import_members_csv,
    preview_assessments_csv,
    preview_checkins_csv,
    preview_members_csv,
)
from app.services.risk import run_daily_risk_processing


router = APIRouter(prefix="/imports", tags=["imports"])
logger = logging.getLogger(__name__)

_MAX_CSV_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = (".csv", ".xlsx")


def _queue_risk_recalculation(gym_id) -> None:
    threading.Thread(
        target=_run_risk_recalculation_background,
        args=(gym_id,),
        daemon=True,
    ).start()


def _run_risk_recalculation_background(gym_id) -> None:
    @with_distributed_lock(
        "daily_risk",
        ttl_seconds=1800,
        fail_open=lambda: settings.scheduler_critical_lock_fail_open,
    )
    def _inner() -> None:
        db = SessionLocal()
        try:
            set_current_gym_id(gym_id)
            result = run_daily_risk_processing(db)
            logger.info("Post-import risk recalculation completed for gym %s: %s", gym_id, result)
        except Exception:
            logger.exception("Post-import risk recalculation failed for gym %s", gym_id)
            db.rollback()
        finally:
            clear_current_gym_id()
            db.close()

    try:
        _inner()
    except Exception:
        logger.warning("Post-import risk recalculation skipped - lock already held")


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
    if summary.imported > 0:
        _queue_risk_recalculation(current_user.gym_id)
    return summary


@router.post("/members/preview", response_model=ImportPreview)
@limiter.limit("10/minute")
async def preview_members_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
) -> ImportPreview:
    _ = request
    lower_filename = (file.filename or "").lower()
    if not lower_filename.endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV ou XLSX")
    set_current_gym_id(current_user.gym_id)
    content = await file.read(_MAX_CSV_SIZE + 1)
    if len(content) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 10 MB")
    try:
        return preview_members_csv(db, content, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/checkins", response_model=ImportSummary)
@limiter.limit("5/minute")
async def import_checkins_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
    auto_create_missing_members: bool = Form(False),
) -> ImportSummary:
    lower_filename = (file.filename or "").lower()
    if not lower_filename.endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV ou XLSX")
    set_current_gym_id(current_user.gym_id)
    content = await file.read(_MAX_CSV_SIZE + 1)
    if len(content) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 10 MB")
    try:
        summary = import_checkins_csv(
            db,
            content,
            filename=file.filename,
            auto_create_missing_members=auto_create_missing_members,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    context = get_request_context(request)
    log_audit_event(
        db,
        action="import_checkins_csv",
        entity="checkins",
        user=current_user,
        details={
            "imported": summary.imported,
            "duplicates": summary.skipped_duplicates,
            "ignored_rows": summary.ignored_rows,
            "provisional_members_created": summary.provisional_members_created,
            "errors": len(summary.errors),
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    if summary.imported > 0 or summary.provisional_members_created > 0:
        _queue_risk_recalculation(current_user.gym_id)
    return summary


@router.post("/checkins/preview", response_model=ImportPreview)
@limiter.limit("10/minute")
async def preview_checkins_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
    auto_create_missing_members: bool = Form(False),
) -> ImportPreview:
    _ = request
    lower_filename = (file.filename or "").lower()
    if not lower_filename.endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV ou XLSX")
    set_current_gym_id(current_user.gym_id)
    content = await file.read(_MAX_CSV_SIZE + 1)
    if len(content) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 10 MB")
    try:
        return preview_checkins_csv(
            db,
            content,
            filename=file.filename,
            auto_create_missing_members=auto_create_missing_members,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/assessments", response_model=ImportSummary)
@limiter.limit("5/minute")
async def import_assessments_endpoint(
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
        summary = import_assessments_csv(db, content, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    context = get_request_context(request)
    log_audit_event(
        db,
        action="import_assessments_csv",
        entity="assessments",
        user=current_user,
        details={"imported": summary.imported, "duplicates": summary.skipped_duplicates, "errors": len(summary.errors)},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return summary


@router.post("/assessments/preview", response_model=ImportPreview)
@limiter.limit("10/minute")
async def preview_assessments_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
) -> ImportPreview:
    _ = request
    lower_filename = (file.filename or "").lower()
    if not lower_filename.endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV ou XLSX")
    set_current_gym_id(current_user.gym_id)
    content = await file.read(_MAX_CSV_SIZE + 1)
    if len(content) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 10 MB")
    try:
        return preview_assessments_csv(db, content, filename=file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
