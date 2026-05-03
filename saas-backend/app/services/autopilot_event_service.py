import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutopilotEvent, Lead, Member, Task


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _payload_hash(payload: dict | None) -> str | None:
    if payload is None:
        return None
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_tenant_links(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID | None = None,
    lead_id: UUID | None = None,
    task_id: UUID | None = None,
) -> None:
    if member_id:
        member = db.get(Member, member_id)
        if not member or member.gym_id != gym_id:
            raise ValueError("member_id fora do tenant do evento")
    if lead_id:
        lead = db.get(Lead, lead_id)
        if not lead or lead.gym_id != gym_id:
            raise ValueError("lead_id fora do tenant do evento")
    if task_id:
        task = db.get(Task, task_id)
        if not task or task.gym_id != gym_id:
            raise ValueError("task_id fora do tenant do evento")


def record_event(
    db: Session,
    *,
    gym_id: UUID,
    event_type: str,
    source: str,
    metadata: dict | None = None,
    member_id: UUID | None = None,
    lead_id: UUID | None = None,
    task_id: UUID | None = None,
    autopilot_action_id: UUID | None = None,
    occurred_at: datetime | None = None,
    deduplication_key: str | None = None,
    correlation_id: str | None = None,
    raw_payload: dict | None = None,
    flush: bool = True,
) -> AutopilotEvent:
    if deduplication_key:
        existing = db.scalar(
            select(AutopilotEvent).where(
                AutopilotEvent.gym_id == gym_id,
                AutopilotEvent.deduplication_key == deduplication_key,
            )
        )
        if existing:
            return existing

    _validate_tenant_links(db, gym_id=gym_id, member_id=member_id, lead_id=lead_id, task_id=task_id)
    event = AutopilotEvent(
        gym_id=gym_id,
        event_type=event_type,
        source=source,
        member_id=member_id,
        lead_id=lead_id,
        task_id=task_id,
        autopilot_action_id=autopilot_action_id,
        occurred_at=occurred_at or _now(),
        received_at=_now(),
        metadata_json=metadata or {},
        deduplication_key=deduplication_key,
        correlation_id=correlation_id,
        raw_payload_hash=_payload_hash(raw_payload),
        processing_status="pending",
    )
    db.add(event)
    if flush:
        db.flush()
    return event


def mark_event_processed(db: Session, event: AutopilotEvent, *, status: str = "processed", error: str | None = None) -> None:
    event.processing_status = status
    event.processing_error = error
    event.processed_at = _now()
    db.add(event)

