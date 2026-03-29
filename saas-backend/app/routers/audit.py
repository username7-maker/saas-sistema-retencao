from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_request_context, require_roles
from app.database import get_db
from app.models import AuditLog, RoleEnum, User
from app.schemas import APIMessage, AuditLogOut, UIEventCreate
from app.services.audit_service import log_audit_event


router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/events", response_model=APIMessage, status_code=status.HTTP_202_ACCEPTED)
def create_ui_event(
    payload: UIEventCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> APIMessage:
    context = get_request_context(request)
    log_audit_event(
        db,
        action=f"ui_event_{payload.event_name}",
        entity=payload.surface,
        entity_id=payload.entity_id,
        member_id=payload.member_id,
        user=current_user,
        details=payload.details,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return APIMessage(message="Evento registrado")


@router.get("/logs", response_model=list[AuditLogOut])
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    limit: int = Query(100, ge=1, le=1000),
) -> list[AuditLog]:
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
