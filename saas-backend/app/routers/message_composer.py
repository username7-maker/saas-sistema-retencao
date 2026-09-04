from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import GymMessageTemplateOverride, RoleEnum, User
from app.schemas.message_composer import (
    MessageCompositionOut,
    MessageComposerMetricsOut,
    MessageImproveIn,
    MessageTemplateOut,
    MessageTemplatePreviewIn,
    MessageTemplatePreviewOut,
    MessageTemplateUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.message_composer_service import get_metrics, improve_message, list_templates, resolve_composition
from app.services.message_template_service import (
    effective_template,
    ensure_domain_permission,
    get_template_definition,
    render_message,
    validate_template_content,
)

router = APIRouter(tags=["message-composer"])
ALL_ROLES = (RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)


@router.get("/message-templates", response_model=list[MessageTemplateOut])
def get_message_templates(
    current_user: Annotated[User, Depends(require_roles(*ALL_ROLES))],
    db: Session = Depends(get_db),
):
    return list_templates(db, current_user)


@router.get("/message-composer/metrics", response_model=MessageComposerMetricsOut)
def get_message_composer_metrics(
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    db: Session = Depends(get_db),
):
    return get_metrics(db, current_user)


@router.put("/message-templates/{template_key}", response_model=MessageTemplateOut)
def put_message_template(
    template_key: str,
    payload: MessageTemplateUpdate,
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    db: Session = Depends(get_db),
):
    definition = get_template_definition(template_key)
    validate_template_content(definition, payload.content)
    override = db.scalar(
        select(GymMessageTemplateOverride).where(
            GymMessageTemplateOverride.gym_id == current_user.gym_id,
            GymMessageTemplateOverride.template_key == template_key,
        )
    )
    if override:
        override.content = payload.content.strip()
        override.is_active = True
        override.version += 1
        override.updated_by_user_id = current_user.id
    else:
        override = GymMessageTemplateOverride(
            gym_id=current_user.gym_id,
            template_key=template_key,
            content=payload.content.strip(),
            updated_by_user_id=current_user.id,
        )
        db.add(override)
    db.flush()
    log_audit_event(
        db,
        "message_template_override_updated",
        "message_template",
        user=current_user,
        details={"template_key": template_key, "version": override.version},
    )
    db.commit()
    return _template_out(db, current_user, template_key)


@router.delete("/message-templates/{template_key}/override", response_model=MessageTemplateOut)
def delete_message_template_override(
    template_key: str,
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    db: Session = Depends(get_db),
):
    get_template_definition(template_key)
    override = db.scalar(
        select(GymMessageTemplateOverride).where(
            GymMessageTemplateOverride.gym_id == current_user.gym_id,
            GymMessageTemplateOverride.template_key == template_key,
        )
    )
    if override:
        override.is_active = False
        override.updated_by_user_id = current_user.id
    log_audit_event(
        db,
        "message_template_override_restored",
        "message_template",
        user=current_user,
        details={"template_key": template_key},
    )
    db.commit()
    return _template_out(db, current_user, template_key)


@router.post("/message-templates/{template_key}/preview", response_model=MessageTemplatePreviewOut)
def preview_message_template(
    template_key: str,
    payload: MessageTemplatePreviewIn,
    current_user: Annotated[User, Depends(require_roles(*ALL_ROLES))],
    db: Session = Depends(get_db),
):
    definition, content, origin = effective_template(db, current_user.gym_id, template_key)
    _ensure_permission(current_user, definition.domain)
    try:
        message = render_message(definition, content, payload.variables)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return MessageTemplatePreviewOut(template_key=template_key, message=message, origin=origin)


@router.post("/message-composer/improve", response_model=MessageCompositionOut)
def improve_message_endpoint(
    payload: MessageImproveIn,
    current_user: Annotated[User, Depends(require_roles(*ALL_ROLES))],
    db: Session = Depends(get_db),
):
    try:
        item = improve_message(db, user=current_user, **payload.model_dump())
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _composition_out(item)


@router.post("/message-composer/{request_id}/apply", response_model=MessageCompositionOut)
def apply_message_endpoint(
    request_id: UUID,
    current_user: Annotated[User, Depends(require_roles(*ALL_ROLES))],
    db: Session = Depends(get_db),
):
    return _resolve(db, current_user, request_id, apply=True)


@router.post("/message-composer/{request_id}/discard", response_model=MessageCompositionOut)
def discard_message_endpoint(
    request_id: UUID,
    current_user: Annotated[User, Depends(require_roles(*ALL_ROLES))],
    db: Session = Depends(get_db),
):
    return _resolve(db, current_user, request_id, apply=False)


def _resolve(db: Session, user: User, request_id: UUID, *, apply: bool) -> MessageCompositionOut:
    try:
        return _composition_out(resolve_composition(db, user=user, request_id=request_id, apply=apply))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _ensure_permission(user: User, domain: str) -> None:
    try:
        ensure_domain_permission(user, domain)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _template_out(db: Session, user: User, template_key: str) -> MessageTemplateOut:
    return MessageTemplateOut(**next(item for item in list_templates(db, user) if item["key"] == template_key))


def _composition_out(item) -> MessageCompositionOut:
    return MessageCompositionOut(
        request_id=item.id,
        base_message=item.base_message,
        improved_message=item.improved_message,
        model=item.model,
        prompt_version=item.prompt_version,
        origin="template_default" if item.fallback_used else "ai_improved",
        warnings=list(item.warnings_json or []),
        status=item.status,
        created_at=item.created_at,
    )
