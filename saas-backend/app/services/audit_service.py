from uuid import UUID

from sqlalchemy.orm import Session

from app.database import get_current_gym_id
from app.models import AuditLog, User

_SENSITIVE_DETAIL_KEYS = {
    "access_token",
    "authorization",
    "cpf",
    "email",
    "gym_slug",
    "phone",
    "prospect_email",
    "prospect_whatsapp",
    "recipient",
    "refresh_token",
    "token",
    "whatsapp",
}

_REDACTION_BY_KEY = {
    "access_token": "[redacted-secret]",
    "authorization": "[redacted-secret]",
    "cpf": "[redacted-document]",
    "email": "[redacted-email]",
    "gym_slug": "[redacted-slug]",
    "phone": "[redacted-phone]",
    "prospect_email": "[redacted-email]",
    "prospect_whatsapp": "[redacted-phone]",
    "recipient": "[redacted-recipient]",
    "refresh_token": "[redacted-secret]",
    "token": "[redacted-secret]",
    "whatsapp": "[redacted-phone]",
}


def log_audit_event(
    db: Session,
    action: str,
    entity: str,
    *,
    user: User | None = None,
    gym_id: UUID | None = None,
    member_id: UUID | None = None,
    entity_id: UUID | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    flush: bool = True,
) -> AuditLog | None:
    resolved_gym_id = gym_id or (user.gym_id if user else None) or get_current_gym_id()
    if resolved_gym_id is None:
        return None

    event = AuditLog(
        gym_id=resolved_gym_id,
        user_id=user.id if user else None,
        member_id=member_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=_sanitize_audit_details(details or {}),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(event)
    if flush:
        db.flush()
    return event


def _sanitize_audit_details(details: dict) -> dict:
    return {str(key): _sanitize_audit_value(str(key), value) for key, value in details.items()}


def _sanitize_audit_value(key: str, value):
    normalized_key = key.strip().lower()
    if normalized_key in _SENSITIVE_DETAIL_KEYS:
        return _REDACTION_BY_KEY.get(normalized_key, "[redacted]")

    if isinstance(value, dict):
        return {str(child_key): _sanitize_audit_value(str(child_key), child_value) for child_key, child_value in value.items()}

    if isinstance(value, list):
        return [_sanitize_audit_value(normalized_key, item) for item in value]

    return value
