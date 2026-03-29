from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache
from app.models import OperationalOutcome


def record_operational_outcome(
    db: Session,
    *,
    gym_id: UUID,
    source: str,
    action_type: str,
    actor: str,
    status: str,
    member_id: UUID | None = None,
    lead_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    task_id: UUID | None = None,
    risk_alert_id: UUID | None = None,
    message_log_id: UUID | None = None,
    lead_booking_id: UUID | None = None,
    channel: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: UUID | None = None,
    playbook_key: str | None = None,
    metadata_json: dict | None = None,
    occurred_at: datetime | None = None,
    flush: bool = True,
) -> OperationalOutcome:
    normalized_occurred = occurred_at or datetime.now(tz=timezone.utc)
    if normalized_occurred.tzinfo is None:
        normalized_occurred = normalized_occurred.replace(tzinfo=timezone.utc)

    outcome = OperationalOutcome(
        gym_id=gym_id,
        member_id=member_id,
        lead_id=lead_id,
        actor_user_id=actor_user_id,
        task_id=task_id,
        risk_alert_id=risk_alert_id,
        message_log_id=message_log_id,
        lead_booking_id=lead_booking_id,
        source=source,
        action_type=action_type,
        actor=actor,
        channel=channel,
        status=status,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        playbook_key=playbook_key,
        metadata_json=metadata_json or {},
        occurred_at=normalized_occurred,
    )
    db.add(outcome)
    if flush:
        db.flush()

    dashboard_cache.invalidate_namespaces(
        {"dashboard_action_center", "dashboard_roi"},
        gym_id=gym_id,
    )
    return outcome
