from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import RiskAlert, RiskLevel, User
from app.schemas import PaginatedResponse
from app.services.audit_service import log_audit_event


def list_risk_alerts(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    level: RiskLevel | None = None,
    resolved: bool | None = None,
) -> PaginatedResponse:
    filters = []
    if level:
        filters.append(RiskAlert.level == level)
    if resolved is not None:
        filters.append(RiskAlert.resolved.is_(resolved))

    where_clause = and_(*filters) if filters else None
    base_stmt = select(RiskAlert)
    if where_clause is not None:
        base_stmt = base_stmt.where(where_clause)

    count_stmt = select(func.count()).select_from(RiskAlert)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        base_stmt.order_by(RiskAlert.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


def resolve_risk_alert(
    db: Session,
    *,
    alert_id: UUID,
    current_user: User,
    resolution_note: str | None = None,
) -> RiskAlert:
    alert = db.get(RiskAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RiskAlert nao encontrado")

    if alert.resolved:
        return alert

    now = datetime.now(tz=timezone.utc)
    history = list(alert.action_history or [])
    history.append(
        {
            "type": "manual_resolution",
            "timestamp": now.isoformat(),
            "resolved_by_user_id": str(current_user.id),
            "resolution_note": resolution_note or "",
        }
    )
    alert.action_history = history
    alert.resolved = True
    alert.resolved_by_user_id = current_user.id
    alert.resolved_at = now
    db.add(alert)

    log_audit_event(
        db,
        action="risk_alert_resolved",
        entity="risk_alert",
        entity_id=alert.id,
        member_id=alert.member_id,
        user=current_user,
        details={"resolution_note": resolution_note or ""},
    )
    db.commit()
    db.refresh(alert)
    return alert
