from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import InAppNotification, RoleEnum, User
from app.schemas import PaginatedResponse


def create_notification(
    db: Session,
    *,
    title: str,
    message: str,
    category: str = "retention",
    member_id: UUID | None = None,
    user_id: UUID | None = None,
    extra_data: dict | None = None,
) -> InAppNotification:
    notification = InAppNotification(
        member_id=member_id,
        user_id=user_id,
        title=title,
        message=message,
        category=category,
        extra_data=extra_data or {},
    )
    db.add(notification)
    db.flush()
    return notification


def list_notifications(
    db: Session,
    *,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
    include_all: bool = False,
) -> PaginatedResponse:
    filters = []
    if unread_only:
        filters.append(InAppNotification.read_at.is_(None))

    is_leadership = current_user.role in {RoleEnum.OWNER, RoleEnum.MANAGER}
    if not (is_leadership and include_all):
        filters.append(or_(InAppNotification.user_id == current_user.id, InAppNotification.user_id.is_(None)))

    where_clause = and_(*filters) if filters else None
    base_stmt = select(InAppNotification)
    if where_clause is not None:
        base_stmt = base_stmt.where(where_clause)

    count_stmt = select(func.count()).select_from(InAppNotification)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        base_stmt.order_by(InAppNotification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


def mark_notification_read(
    db: Session,
    *,
    notification_id: UUID,
    current_user: User,
    read: bool = True,
) -> InAppNotification:
    notification = db.get(InAppNotification, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificacao nao encontrada")

    is_leadership = current_user.role in {RoleEnum.OWNER, RoleEnum.MANAGER}
    belongs_to_user = notification.user_id == current_user.id or notification.user_id is None
    if not is_leadership and not belongs_to_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissao insuficiente")

    notification.read_at = datetime.now(tz=timezone.utc) if read else None
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
