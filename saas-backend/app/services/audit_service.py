from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def log_audit_event(
    db: Session,
    action: str,
    entity: str,
    *,
    user: User | None = None,
    member_id: UUID | None = None,
    entity_id: UUID | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    event = AuditLog(
        user_id=user.id if user else None,
        member_id=member_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(event)
    db.flush()
    return event
