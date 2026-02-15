from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import InAppNotificationOut, MarkNotificationReadInput, PaginatedResponse
from app.services.audit_service import log_audit_event
from app.services.notification_service import list_notifications, mark_notification_read


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=PaginatedResponse[InAppNotificationOut])
def list_notifications_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_roles(
                RoleEnum.OWNER,
                RoleEnum.MANAGER,
                RoleEnum.RECEPTIONIST,
                RoleEnum.SALESPERSON,
            )
        ),
    ],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    include_all: bool = False,
) -> PaginatedResponse[InAppNotificationOut]:
    return list_notifications(
        db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
        include_all=include_all,
    )


@router.patch("/{notification_id}/read", response_model=InAppNotificationOut)
def mark_read_endpoint(
    request: Request,
    notification_id: UUID,
    payload: MarkNotificationReadInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> InAppNotificationOut:
    notification = mark_notification_read(
        db,
        notification_id=notification_id,
        current_user=current_user,
        read=payload.read,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="notification_read_toggled",
        entity="in_app_notification",
        user=current_user,
        member_id=notification.member_id,
        entity_id=notification.id,
        details={"read": payload.read},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return notification
