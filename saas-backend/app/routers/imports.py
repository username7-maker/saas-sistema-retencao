import hashlib
import json
from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.core.dependencies import get_request_context, require_roles
from app.core.limiter import limiter
from app.database import get_db, set_current_gym_id
from app.models import RoleEnum, User
from app.schemas import ImportPreview, ImportSummary
from app.services.audit_service import log_audit_event
from app.services.import_service import (
    import_assessment_appointments_csv,
    import_assessments_csv,
    import_checkins_csv,
    import_members_csv,
    preview_assessment_appointments_csv,
    preview_assessments_csv,
    preview_checkins_csv,
    preview_members_csv,
)

router = APIRouter(prefix="/imports", tags=["imports"])

_MAX_CSV_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXTENSIONS = (".csv", ".xlsx")


def _checkin_error_audit_details(content: bytes, preview: ImportPreview) -> dict:
    reason_counts = Counter(error.reason for error in preview.errors)
    return {
        "file_sha256": hashlib.sha256(content).hexdigest(),
        "error_count": len(preview.errors),
        "error_rows": [error.row_number for error in preview.errors[:100]],
        "error_reasons": dict(reason_counts),
        "ignored_rows": preview.ignored_rows,
    }


def _audit_checkin_preview_errors(
    request: Request,
    db: Session,
    current_user: User,
    *,
    content: bytes,
    preview: ImportPreview,
    action: str,
) -> None:
    context = get_request_context(request)
    log_audit_event(
        db,
        action=action,
        entity="checkins",
        user=current_user,
        details=_checkin_error_audit_details(content, preview),
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()


def _member_block_audit_details(content: bytes, preview: ImportPreview) -> dict:
    return {
        "file_sha256": hashlib.sha256(content).hexdigest(),
        "total_rows": preview.total_rows,
        "valid_rows": preview.valid_rows,
        "would_create": preview.would_create,
        "would_update": preview.would_update,
        "blocking_issues": preview.blocking_issues,
        "error_count": len(preview.errors),
    }


def _audit_member_preview_block(
    request: Request,
    db: Session,
    current_user: User,
    *,
    content: bytes,
    preview: ImportPreview,
    action: str,
) -> None:
    context = get_request_context(request)
    log_audit_event(
        db,
        action=action,
        entity="members",
        user=current_user,
        details=_member_block_audit_details(content, preview),
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()


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


def _successful_import_audit_details(
    *,
    content: bytes,
    filename: str | None,
    column_mappings: dict[str, str],
    ignored_columns: list[str],
    summary: ImportSummary,
    coverage_warning_codes: list[str] | None = None,
) -> dict:
    """Aggregate-only import evidence. Never records source rows or PII."""

    safe_filename = str(filename or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
    file_type = f".{safe_filename.rsplit('.', 1)[-1]}" if "." in safe_filename else "unknown"
    return {
        "file_type": file_type,
        "file_sha256": hashlib.sha256(content).hexdigest().upper(),
        "coverage_warning_codes": coverage_warning_codes or [],
        "mapping": {
            "mapped_fields": sorted(set(column_mappings.values())),
            "mapped_columns": len(column_mappings),
            "ignored_columns": len(ignored_columns),
        },
        "totals": {
            "imported": summary.imported,
            "updated_existing": summary.updated_existing,
            "duplicates": summary.skipped_duplicates,
            "ignored_rows": summary.ignored_rows,
            "provisional_members_created": summary.provisional_members_created,
            "errors": len(summary.errors),
        },
    }

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
    parsed_mappings = _parse_mapping_dict(column_mappings)
    parsed_ignored_columns = _parse_ignored_columns(ignored_columns)
    try:
        preview = preview_members_csv(
            db,
            content,
            filename=file.filename,
            column_mappings=parsed_mappings,
            ignored_columns=parsed_ignored_columns,
        )
        if not preview.can_confirm:
            _audit_member_preview_block(
                request,
                db,
                current_user,
                content=content,
                preview=preview,
                action="import_members_csv_blocked",
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Importacao de alunos bloqueada pelo preview. "
                    "Revise as pendencias e use Importar check-ins quando o arquivo for de acessos/catraca; "
                    "nenhum cadastro foi alterado."
                ),
            )
        summary = import_members_csv(
            db,
            content,
            filename=file.filename,
            column_mappings=parsed_mappings,
            ignored_columns=parsed_ignored_columns,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    context = get_request_context(request)
    log_audit_event(
        db,
        action="import_members_csv",
        entity="members",
        user=current_user,
        details=_successful_import_audit_details(
            content=content,
            filename=file.filename,
            column_mappings=parsed_mappings,
            ignored_columns=parsed_ignored_columns,
            summary=summary,
        ),
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
    lower_filename = (file.filename or "").lower()
    if not lower_filename.endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV ou XLSX")
    set_current_gym_id(current_user.gym_id)
    content = await file.read(_MAX_CSV_SIZE + 1)
    if len(content) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 10 MB")
    try:
        preview = preview_members_csv(
            db,
            content,
            filename=file.filename,
            column_mappings=_parse_mapping_dict(column_mappings),
            ignored_columns=_parse_ignored_columns(ignored_columns),
        )
        if not preview.can_confirm:
            _audit_member_preview_block(
                request,
                db,
                current_user,
                content=content,
                preview=preview,
                action="preview_members_csv_blocked",
            )
        return preview
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
    parsed_mappings = _parse_mapping_dict(column_mappings)
    parsed_ignored_columns = _parse_ignored_columns(ignored_columns)
    try:
        preview = preview_checkins_csv(
            db,
            content,
            filename=file.filename,
            auto_create_missing_members=auto_create_missing_members,
            column_mappings=parsed_mappings,
            ignored_columns=parsed_ignored_columns,
        )
        if not preview.can_confirm:
            _audit_checkin_preview_errors(
                request,
                db,
                current_user,
                content=content,
                preview=preview,
                action="import_checkins_csv_blocked",
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Importacao bloqueada: nenhuma linha valida ou existe um conflito no mapeamento. "
                    "Revise o preview; nenhum check-in foi gravado."
                ),
            )
        summary = import_checkins_csv(
            db,
            content,
            filename=file.filename,
            auto_create_missing_members=auto_create_missing_members,
            column_mappings=parsed_mappings,
            ignored_columns=parsed_ignored_columns,
            commit=False,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    context = get_request_context(request)
    log_audit_event(
        db,
        action="import_checkins_csv",
        entity="checkins",
        user=current_user,
        details=_successful_import_audit_details(
            content=content,
            filename=file.filename,
            column_mappings=parsed_mappings,
            ignored_columns=parsed_ignored_columns,
            summary=summary,
            coverage_warning_codes=["possible_access_gap"] if any(
                "lacuna" in warning.lower() or "nao possui acessos" in warning.lower()
                for warning in preview.warnings
            ) else [],
        ),
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    invalidate_dashboard_cache("checkins", "risk")
    if summary.provisional_members_created:
        invalidate_dashboard_cache("members")
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
    lower_filename = (file.filename or "").lower()
    if not lower_filename.endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo deve ser CSV ou XLSX")
    set_current_gym_id(current_user.gym_id)
    content = await file.read(_MAX_CSV_SIZE + 1)
    if len(content) > _MAX_CSV_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 10 MB")
    try:
        preview = preview_checkins_csv(
            db,
            content,
            filename=file.filename,
            auto_create_missing_members=auto_create_missing_members,
            column_mappings=_parse_mapping_dict(column_mappings),
            ignored_columns=_parse_ignored_columns(ignored_columns),
        )
        if preview.errors:
            _audit_checkin_preview_errors(
                request,
                db,
                current_user,
                content=content,
                preview=preview,
                action="preview_checkins_csv_errors",
            )
        return preview
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/assessments", response_model=ImportSummary)
@limiter.limit("5/minute")
async def import_assessments_endpoint(
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
    parsed_mappings = _parse_mapping_dict(column_mappings)
    parsed_ignored_columns = _parse_ignored_columns(ignored_columns)
    try:
        summary = import_assessments_csv(
            db,
            content,
            filename=file.filename,
            column_mappings=parsed_mappings,
            ignored_columns=parsed_ignored_columns,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    context = get_request_context(request)
    log_audit_event(
        db,
        action="import_assessments_csv",
        entity="assessments",
        user=current_user,
        details=_successful_import_audit_details(
            content=content,
            filename=file.filename,
            column_mappings=parsed_mappings,
            ignored_columns=parsed_ignored_columns,
            summary=summary,
        ),
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
        return preview_assessments_csv(
            db,
            content,
            filename=file.filename,
            column_mappings=_parse_mapping_dict(column_mappings),
            ignored_columns=_parse_ignored_columns(ignored_columns),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/assessment-appointments/apply", response_model=ImportSummary)
@limiter.limit("5/minute")
async def import_assessment_appointments_endpoint(
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
    parsed_mappings = _parse_mapping_dict(column_mappings)
    parsed_ignored_columns = _parse_ignored_columns(ignored_columns)
    try:
        summary = import_assessment_appointments_csv(
            db,
            content,
            filename=file.filename,
            column_mappings=parsed_mappings,
            ignored_columns=parsed_ignored_columns,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    context = get_request_context(request)
    log_audit_event(
        db,
        action="import_assessment_appointments_csv",
        entity="assessment_appointments",
        user=current_user,
        details=_successful_import_audit_details(
            content=content,
            filename=file.filename,
            column_mappings=parsed_mappings,
            ignored_columns=parsed_ignored_columns,
            summary=summary,
        ),
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return summary


@router.post("/assessment-appointments/preview", response_model=ImportPreview)
@limiter.limit("10/minute")
async def preview_assessment_appointments_endpoint(
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
        return preview_assessment_appointments_csv(
            db,
            content,
            filename=file.filename,
            column_mappings=_parse_mapping_dict(column_mappings),
            ignored_columns=_parse_ignored_columns(ignored_columns),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
