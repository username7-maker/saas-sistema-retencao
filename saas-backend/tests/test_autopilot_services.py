import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models import AutopilotAction, MemberStatus, TaskStatus
from app.services.autopilot_action_service import (
    build_autopilot_request_fingerprint,
    create_autopilot_action,
    execute_autopilot_action,
)
from app.services.autopilot_event_service import record_event
from app.services.autopilot_policy_service import AutopilotDecision
from app.services.autopilot_resolver_service import resolve_event
from app.services.autopilot_safety_service import SafetyResult, check_autopilot_safety, contains_sensitive_text


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
TASK_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
ACTION_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
EVENT_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")


def _autopilot_settings(**overrides):
    defaults = {
        "autopilot_enabled": True,
        "autopilot_auto_close_enabled": True,
        "autopilot_auto_send_enabled": False,
        "retention_enabled": True,
        "finance_enabled": True,
        "sales_enabled": True,
        "onboarding_enabled": True,
        "assessment_enabled": True,
        "nps_enabled": True,
        "business_hours_start": "00:00",
        "business_hours_end": "23:59",
        "max_auto_messages_per_member_per_week": 10,
        "max_auto_messages_per_lead_per_week": 10,
        "human_recent_activity_cooldown_hours": 0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _decision(action_type: str = "send_whatsapp") -> AutopilotDecision:
    return AutopilotDecision(
        decision="auto_execute",
        domain="retention",
        policy_key="manual_send_and_wait_retention",
        action_type=action_type,
        template_key=None,
        confidence=1.0,
        reason="Teste sintetico",
        next_timeout_hours=48,
        metadata={},
    )


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


def test_manual_outbound_requires_communication_consent_even_without_auto_send(monkeypatch):
    member = SimpleNamespace(id=MEMBER_ID, status=MemberStatus.ACTIVE)
    db = MagicMock()
    db.scalar.return_value = None
    monkeypatch.setattr("app.services.autopilot_safety_service.get_or_create_autopilot_settings", lambda *_args, **_kwargs: _autopilot_settings())
    monkeypatch.setattr("app.services.autopilot_safety_service._pending_duplicate_action", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("app.services.autopilot_safety_service._recent_human_task_activity", lambda *_args, **_kwargs: False)

    safety = check_autopilot_safety(
        db,
        gym_id=GYM_ID,
        domain="retention",
        policy_key="manual_send_and_wait_retention",
        action_type="send_whatsapp",
        member=member,
        message_text="Mensagem humana",
        require_auto_send=False,
    )

    assert safety.allowed is False
    assert "missing_member_communication_consent" in safety.reasons
    assert safety.consent_snapshot["effect"] == "human_outbound_message"


def test_manual_outbound_accepts_current_communication_consent(monkeypatch):
    member = SimpleNamespace(id=MEMBER_ID, status=MemberStatus.ACTIVE)
    consent = SimpleNamespace(
        id=uuid.uuid4(),
        member_id=MEMBER_ID,
        consent_type="communication",
        status="accepted",
        signed_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        revoked_at=None,
        expires_at=None,
        source="manual",
        document_version="v1",
    )
    db = MagicMock()
    db.scalar.return_value = consent
    monkeypatch.setattr("app.services.autopilot_safety_service.get_or_create_autopilot_settings", lambda *_args, **_kwargs: _autopilot_settings())
    monkeypatch.setattr("app.services.autopilot_safety_service._pending_duplicate_action", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("app.services.autopilot_safety_service._recent_human_task_activity", lambda *_args, **_kwargs: False)

    safety = check_autopilot_safety(
        db,
        gym_id=GYM_ID,
        domain="retention",
        policy_key="manual_send_and_wait_retention",
        action_type="kommo_operator_handoff",
        member=member,
        message_text="Mensagem humana",
        require_auto_send=False,
    )

    assert safety.allowed is True
    assert safety.consent_snapshot["record_id"] == str(consent.id)
    assert safety.consent_snapshot["channel"] == "kommo"


def test_dispatch_safety_excludes_current_action_from_duplicate_check(monkeypatch):
    member = SimpleNamespace(id=MEMBER_ID, status=MemberStatus.ACTIVE)
    consent = SimpleNamespace(
        id=uuid.uuid4(),
        member_id=MEMBER_ID,
        consent_type="communication",
        status="accepted",
        signed_at=None,
        revoked_at=None,
        expires_at=None,
        source="manual",
        document_version="v1",
    )
    db = MagicMock()
    db.scalar.side_effect = [consent, 0]
    monkeypatch.setattr("app.services.autopilot_safety_service.get_or_create_autopilot_settings", lambda *_args, **_kwargs: _autopilot_settings())
    monkeypatch.setattr("app.services.autopilot_safety_service._recent_human_task_activity", lambda *_args, **_kwargs: False)

    safety = check_autopilot_safety(
        db,
        gym_id=GYM_ID,
        domain="retention",
        policy_key="manual_send_and_wait_retention",
        action_type="send_whatsapp",
        member=member,
        message_text="Mensagem humana",
        require_auto_send=False,
        ignore_autopilot_action_id=ACTION_ID,
    )

    duplicate_statement = db.scalar.call_args_list[1].args[0]
    assert safety.allowed is True
    assert "autopilot_actions.id" in str(duplicate_statement)


def test_create_autopilot_action_replays_same_fingerprint_and_conflicts_on_different_fingerprint():
    existing = AutopilotAction(
        id=ACTION_ID,
        gym_id=GYM_ID,
        policy_key="manual_send_and_wait_retention",
        domain="retention",
        action_type="send_whatsapp",
        status="awaiting_outcome",
        channel="whatsapp",
        idempotency_key="send-and-wait:whatsapp:task-1",
        request_fingerprint="fp-1",
        metadata_json={},
    )
    db = MagicMock()
    db.scalar.return_value = existing

    replay = create_autopilot_action(
        db,
        gym_id=GYM_ID,
        decision=_decision(),
        idempotency_key=existing.idempotency_key,
        request_fingerprint="fp-1",
        flush=False,
    )

    assert replay is existing
    db.add.assert_not_called()
    with pytest.raises(HTTPException) as exc_info:
        create_autopilot_action(
            db,
            gym_id=GYM_ID,
            decision=_decision(),
            idempotency_key=existing.idempotency_key,
            request_fingerprint="fp-2",
            flush=False,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "autopilot_idempotency_conflict"


def test_execute_autopilot_action_commits_dispatch_reservation_before_provider(monkeypatch):
    action = AutopilotAction(
        id=ACTION_ID,
        gym_id=GYM_ID,
        policy_key="manual_send_and_wait_retention",
        domain="retention",
        action_type="send_whatsapp",
        status="planned",
        member_id=MEMBER_ID,
        channel="whatsapp",
        message_body="Ola",
        metadata_json={},
    )
    member = SimpleNamespace(id=MEMBER_ID, gym_id=GYM_ID, phone="11999999999", status=MemberStatus.ACTIVE)
    log = SimpleNamespace(id=uuid.uuid4(), status="sent", provider_message_id="provider-1", error_detail=None, extra_data={})
    db = MagicMock()
    db.get.return_value = member
    monkeypatch.setattr("app.services.autopilot_action_service.check_autopilot_safety", lambda *_args, **_kwargs: SafetyResult(True))
    monkeypatch.setattr("app.services.autopilot_action_service.get_gym_instance", lambda *_args, **_kwargs: "instance")

    provider_calls = []

    def fake_send(*_args, **_kwargs):
        provider_calls.append("sent")
        assert db.commit.called
        return log

    monkeypatch.setattr("app.services.autopilot_action_service.send_whatsapp_sync", fake_send)

    result = execute_autopilot_action(db, action, require_auto_send=False, flush=False, commit_before_provider=True)

    assert result.status == "awaiting_outcome"
    assert result.provider_status == "accepted"
    assert result.provider_reference == "provider-1"
    assert provider_calls == ["sent"]
    replay = execute_autopilot_action(db, action, require_auto_send=False, flush=False, commit_before_provider=True)
    assert replay is action
    assert provider_calls == ["sent"]
    db.commit.assert_called_once()


def test_execute_autopilot_action_marks_provider_failure_without_retry(monkeypatch):
    action = AutopilotAction(
        id=ACTION_ID,
        gym_id=GYM_ID,
        policy_key="manual_send_and_wait_retention",
        domain="retention",
        action_type="send_whatsapp",
        status="planned",
        member_id=MEMBER_ID,
        channel="whatsapp",
        message_body="Ola",
        metadata_json={},
    )
    member = SimpleNamespace(id=MEMBER_ID, gym_id=GYM_ID, phone="11999999999", status=MemberStatus.ACTIVE)
    log = SimpleNamespace(id=uuid.uuid4(), status="failed", provider_message_id=None, error_detail="provider_rejected", extra_data={})
    db = MagicMock()
    db.get.return_value = member
    provider = MagicMock(return_value=log)
    monkeypatch.setattr("app.services.autopilot_action_service.check_autopilot_safety", lambda *_args, **_kwargs: SafetyResult(True))
    monkeypatch.setattr("app.services.autopilot_action_service.get_gym_instance", lambda *_args, **_kwargs: "instance")
    monkeypatch.setattr("app.services.autopilot_action_service.send_whatsapp_sync", provider)

    result = execute_autopilot_action(db, action, require_auto_send=False, flush=False)
    replay = execute_autopilot_action(db, action, require_auto_send=False, flush=False)

    assert result.status == "failed"
    assert result.provider_status == "failed"
    assert result.provider_error == "provider_rejected"
    assert replay is action
    provider.assert_called_once()


def test_execute_autopilot_action_uncertain_provider_exception_is_durable_and_not_retried(monkeypatch):
    action = AutopilotAction(
        id=ACTION_ID,
        gym_id=GYM_ID,
        policy_key="manual_send_and_wait_retention",
        domain="retention",
        action_type="send_whatsapp",
        status="planned",
        member_id=MEMBER_ID,
        channel="whatsapp",
        message_body="Ola",
        metadata_json={},
    )
    member = SimpleNamespace(id=MEMBER_ID, gym_id=GYM_ID, phone="11999999999", status=MemberStatus.ACTIVE)
    db = MagicMock()
    db.get.return_value = member
    provider = MagicMock(side_effect=RuntimeError("provider timeout"))
    monkeypatch.setattr("app.services.autopilot_action_service.check_autopilot_safety", lambda *_args, **_kwargs: SafetyResult(True))
    monkeypatch.setattr("app.services.autopilot_action_service.get_gym_instance", lambda *_args, **_kwargs: "instance")
    monkeypatch.setattr("app.services.autopilot_action_service.send_whatsapp_sync", provider)

    result = execute_autopilot_action(db, action, require_auto_send=False, flush=False)
    replay = execute_autopilot_action(db, action, require_auto_send=False, flush=False)

    assert result.status == "dispatch_uncertain"
    assert result.provider_status == "dispatch_uncertain"
    assert "provider timeout" in result.provider_error
    assert replay is action
    provider.assert_called_once()


def test_execute_autopilot_action_replay_status_does_not_call_provider(monkeypatch):
    action = AutopilotAction(
        id=ACTION_ID,
        gym_id=GYM_ID,
        policy_key="manual_send_and_wait_retention",
        domain="retention",
        action_type="send_whatsapp",
        status="dispatch_uncertain",
        channel="whatsapp",
        message_body="Ola",
        request_fingerprint=build_autopilot_request_fingerprint(message="Ola"),
        metadata_json={},
    )
    provider = MagicMock()
    monkeypatch.setattr("app.services.autopilot_action_service.send_whatsapp_sync", provider)

    result = execute_autopilot_action(MagicMock(), action, require_auto_send=False)

    assert result is action
    provider.assert_not_called()


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
