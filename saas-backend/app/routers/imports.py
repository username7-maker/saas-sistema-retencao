import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.core.limiter import limiter
from app.database import get_db, set_current_gym_id
from app.models import RoleEnum, User
from app.schemas import ImportPreview, ImportSummary
from app.services.audit_service import log_audit_event
from app.services.import_service import (
    import_checkins_csv,
    import_members_csv,
    preview_checkins_csv,
    preview_members_csv,
)


router = APIRouter(prefix="/imports", tags=["imports"])

_MAX_CSV_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = (".csv", ".xlsx")


def _parse_mapping_dict(raw_value: str | None) -> dict[str, str]:
    if not raw_value:
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="column_mappings invalido") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="column_mappings deve ser um objeto JSON")
    return {str(key): str(value) for key, value in parsed.items()}


def _parse_ignored_columns(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ignored_columns invalido") from exc
    if not isinstance(parsed, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ignored_columns deve ser uma lista JSON")
    return [str(item) for item in parsed]

@router.post("/members", response_model=ImportSummary)
@limiter.limit("5/minute")
async def import_members_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
    column_mappings: str | None = Form(None),
    ignored_columns: str | None = Form(None),
) -> ImportSummary:
    lower_filename = (file.filename or "").lower()
    if not lower_filename.endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV ou XLSX")
    set_current_gym_id(current_user.gym_id)
    content = await file.read(_MAX_CSV_SIZE + 1)
    if len(content) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 10 MB")
    try:
        summary = import_members_csv(
            db,
            content,
            filename=file.filename,
            column_mappings=_parse_mapping_dict(column_mappings),
            ignored_columns=_parse_ignored_columns(ignored_columns),
        )
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


@router.post("/members/preview", response_model=ImportPreview)
@limiter.limit("10/minute")
async def preview_members_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
    column_mappings: str | None = Form(None),
    ignored_columns: str | None = Form(None),
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
        return preview_members_csv(
            db,
            content,
            filename=file.filename,
            column_mappings=_parse_mapping_dict(column_mappings),
            ignored_columns=_parse_ignored_columns(ignored_columns),
        )
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
    column_mappings: str | None = Form(None),
    ignored_columns: str | None = Form(None),
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
            column_mappings=_parse_mapping_dict(column_mappings),
            ignored_columns=_parse_ignored_columns(ignored_columns),
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
    return summary


@router.post("/checkins/preview", response_model=ImportPreview)
@limiter.limit("10/minute")
async def preview_checkins_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    file: UploadFile = File(...),
    auto_create_missing_members: bool = Form(False),
    column_mappings: str | None = Form(None),
    ignored_columns: str | None = Form(None),
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
            column_mappings=_parse_mapping_dict(column_mappings),
            ignored_columns=_parse_ignored_columns(ignored_columns),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
