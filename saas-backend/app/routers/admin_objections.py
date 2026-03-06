from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import ObjectionResponseOut, ObjectionResponseUpdate
from app.services.audit_service import log_audit_event
from app.services.objection_service import list_admin_objections, update_admin_objection


router = APIRouter(prefix="/admin/objections", tags=["admin-objections"])


def _resolve_admin_gym_id() -> UUID:
    raw = (settings.admin_gym_id or "").strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_GYM_ID nao configurado",
        )
    try:
        return UUID(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_GYM_ID invalido",
        ) from exc


def _ensure_admin_scope(current_user: User) -> UUID:
    admin_gym_id = _resolve_admin_gym_id()
    if current_user.gym_id != admin_gym_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Escopo administrativo invalido")
    return admin_gym_id


@router.get("/", response_model=list[ObjectionResponseOut])
def list_objections_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER))],
) -> list[ObjectionResponseOut]:
    admin_gym_id = _ensure_admin_scope(current_user)
    objections = list_admin_objections(db, admin_gym_id)
    return [ObjectionResponseOut.model_validate(item) for item in objections]


@router.put("/{objection_id}", response_model=ObjectionResponseOut)
def update_objection_endpoint(
    request: Request,
    objection_id: UUID,
    payload: ObjectionResponseUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER))],
) -> ObjectionResponseOut:
    admin_gym_id = _ensure_admin_scope(current_user)
    item = update_admin_objection(
        db,
        objection_id=objection_id,
        admin_gym_id=admin_gym_id,
        payload=payload,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="admin_objection_updated",
        entity="objection_response",
        user=current_user,
        entity_id=item.id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(item)
    return ObjectionResponseOut.model_validate(item)
