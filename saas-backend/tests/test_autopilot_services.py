import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models import TaskStatus
from app.services.autopilot_event_service import record_event
from app.services.autopilot_resolver_service import resolve_event
from app.services.autopilot_safety_service import contains_sensitive_text


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
TASK_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
ACTION_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
EVENT_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")


def test_record_event_deduplicates_by_key():
    existing = SimpleNamespace(id=EVENT_ID, gym_id=GYM_ID, deduplication_key="checkin:1")
    db = MagicMock()
    db.scalar.return_value = existing

    event = record_event(
        db,
        gym_id=GYM_ID,
        event_type="member_checkin_created",
        source="checkin",
        deduplication_key="checkin:1",
        flush=False,
    )

    assert event is existing
    db.add.assert_not_called()


def test_record_event_creates_pending_event_with_payload_hash():
    db = MagicMock()
    db.scalar.return_value = None

    event = record_event(
        db,
        gym_id=GYM_ID,
        event_type="whatsapp_inbound_received",
        source="whatsapp",
        metadata={"text": "Oi"},
        raw_payload={"provider_id": "abc"},
        flush=False,
    )

    assert event.gym_id == GYM_ID
    assert event.event_type == "whatsapp_inbound_received"
    assert event.processing_status == "pending"
    assert event.raw_payload_hash
    db.add.assert_called_once_with(event)


def test_sensitive_text_blocks_simple_resolution_terms():
    assert contains_sensitive_text("Quero cancelar meu plano e falar com gerente") is True
    assert contains_sensitive_text("Volto a treinar amanha") is False


def test_checkin_event_auto_closes_retention_task_and_action(monkeypatch):
    db = MagicMock()
    now = datetime.now(tz=timezone.utc)
    event = SimpleNamespace(
        id=EVENT_ID,
        gym_id=GYM_ID,
        event_type="member_checkin_created",
        member_id=MEMBER_ID,
        lead_id=None,
        metadata_json={},
        processing_status="pending",
        processed_at=None,
        processing_error=None,
    )
    task = SimpleNamespace(
        id=TASK_ID,
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        lead_id=None,
        status=TaskStatus.TODO,
        kanban_column=TaskStatus.TODO.value,
        completed_at=None,
        extra_data={"domain": "retention"},
        created_at=now,
        updated_at=now,
    )
    action = SimpleNamespace(
        id=ACTION_ID,
        gym_id=GYM_ID,
        policy_key="retention_inactive_d3",
        domain="retention",
        status="awaiting_outcome",
        outcome=None,
        completed_at=None,
        member_id=None,
        lead_id=None,
        related_task_id=None,
        metadata_json={},
    )

    monkeypatch.setattr("app.services.autopilot_resolver_service._open_tasks_for_subject", lambda *_args, **_kwargs: [task])
    monkeypatch.setattr("app.services.autopilot_resolver_service._awaiting_actions_for_subject", lambda *_args, **_kwargs: [action])

    result = resolve_event(db, event, flush=False)

    assert result["processed"] is True
    assert result["resolved_count"] == 2
    assert action.status == "succeeded"
    assert action.outcome == "completed"
    assert task.status == TaskStatus.DONE
    assert task.extra_data["work_queue_outcome"] == "completed"
    assert event.processing_status == "processed"
