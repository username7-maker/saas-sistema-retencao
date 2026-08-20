from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.core.config import settings
from app.services.nurturing_service import handle_incoming_whatsapp_webhook
from app.services.whatsapp_agent_service import (
    WhatsAppAgentOutcome,
    build_whatsapp_agent_payload,
    classify_whatsapp_agent_audience,
)


def _message_payload(*, phone: str = "5511999999999", text: str = "Oi") -> dict:
    return {
        "event": "MESSAGES_UPSERT",
        "instance": "gym_instance",
        "data": {
            "key": {
                "remoteJid": f"{phone}@s.whatsapp.net",
                "fromMe": False,
                "id": "msg-123",
            },
            "message": {"conversation": text},
        },
    }


def test_classifies_internal_allowed_phone(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_internal_allowed_phones", "5511999999999")

    assert classify_whatsapp_agent_audience("11 99999-9999") == "internal"
    assert classify_whatsapp_agent_audience("5511888888888") == "external"


def test_builds_normalized_whatsapp_agent_payload():
    gym_id = uuid4()
    member_id = uuid4()
    payload = build_whatsapp_agent_payload(
        event_id="msg-123",
        provider_message_id="msg-123",
        gym_id=gym_id,
        instance="gym_instance",
        sender_phone="(11) 99999-9999",
        sender_name="Ana",
        audience="external",
        message="Quero saber sobre planos",
        member_id=member_id,
    )

    assert payload["gym_id"] == str(gym_id)
    assert payload["sender_phone"] == "5511999999999"
    assert payload["audience"] == "external"
    assert payload["context"]["member_id"] == str(member_id)


def test_incoming_whatsapp_calls_n8n_with_normalized_payload(monkeypatch):
    gym_id = uuid4()
    member_id = uuid4()
    db = MagicMock()
    member = SimpleNamespace(id=member_id, gym_id=gym_id, full_name="Ana Cliente")
    captured: dict = {}

    monkeypatch.setattr("app.services.nurturing_service.whatsapp_agent_enabled", lambda: True)
    monkeypatch.setattr("app.services.nurturing_service.find_active_sequence_by_phone", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.nurturing_service._find_member_by_phone", lambda *_args, **_kwargs: member)
    monkeypatch.setattr("app.services.nurturing_service.record_event", lambda *_args, **_kwargs: SimpleNamespace())
    monkeypatch.setattr("app.services.nurturing_service.resolve_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.nurturing_service.get_gym_instance", lambda *_args, **_kwargs: "gym_instance")

    def fake_call(payload):
        captured.update(payload)
        return WhatsAppAgentOutcome(
            processed=True,
            fallback_allowed=False,
            detail="agent handled",
            response={
                "event_id": "msg-123",
                "status": "no_reply",
                "action": "no_reply",
                "recipient_phone": "5511999999999",
                "message": "",
                "risk": "low",
                "approval_required": False,
                "metadata": {},
            },
        )

    monkeypatch.setattr("app.services.nurturing_service.call_whatsapp_agent", fake_call)

    result = handle_incoming_whatsapp_webhook(db, _message_payload(), gym_id=gym_id)

    assert result == {"processed": True, "detail": "Agent returned no_reply", "agent": True}
    assert captured["gym_id"] == str(gym_id)
    assert captured["provider_message_id"] == "msg-123"
    assert captured["sender_phone"] == "5511999999999"
    assert captured["audience"] == "external"
    assert captured["context"]["member_id"] == str(member_id)


def test_incoming_whatsapp_falls_back_to_legacy_when_agent_unavailable(monkeypatch):
    gym_id = uuid4()
    lead_id = uuid4()
    db = MagicMock()
    sequence = SimpleNamespace(
        id=uuid4(),
        gym_id=gym_id,
        lead_id=lead_id,
        prospect_name="Lead Teste",
        diagnosis_data={},
    )
    send_calls: list[dict] = []

    monkeypatch.setattr("app.services.nurturing_service.whatsapp_agent_enabled", lambda: True)
    monkeypatch.setattr("app.services.nurturing_service.find_active_sequence_by_phone", lambda *_args, **_kwargs: sequence)
    monkeypatch.setattr("app.services.nurturing_service._find_member_by_phone", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.nurturing_service.record_event", lambda *_args, **_kwargs: SimpleNamespace())
    monkeypatch.setattr("app.services.nurturing_service.resolve_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.nurturing_service._invalidate_sales_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "app.services.nurturing_service.call_whatsapp_agent",
        lambda *_args, **_kwargs: WhatsAppAgentOutcome(False, True, "agent unavailable"),
    )
    monkeypatch.setattr(
        "app.services.nurturing_service.generate_objection_response",
        lambda *_args, **_kwargs: {
            "matched": True,
            "response_text": "Resposta legada",
            "objection_id": None,
            "source": "test",
        },
    )
    monkeypatch.setattr("app.services.nurturing_service._record_detected_objection", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.nurturing_service.get_gym_instance", lambda *_args, **_kwargs: "gym_instance")

    def fake_send(*_args, **kwargs):
        send_calls.append(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr("app.services.nurturing_service.send_whatsapp_sync", fake_send)

    result = handle_incoming_whatsapp_webhook(db, _message_payload(text="Tenho uma objecao"), gym_id=gym_id)

    assert result["detail"] == "Objecao detectada e respondida"
    assert send_calls[0]["message"] == "Resposta legada"


def test_incoming_whatsapp_agent_reply_is_sent_through_backend(monkeypatch):
    gym_id = uuid4()
    member_id = uuid4()
    db = MagicMock()
    member = SimpleNamespace(id=member_id, gym_id=gym_id, full_name="Ana Cliente")
    send_calls: list[dict] = []

    monkeypatch.setattr(settings, "whatsapp_agent_mode", "active")
    monkeypatch.setattr("app.services.nurturing_service.whatsapp_agent_enabled", lambda: True)
    monkeypatch.setattr("app.services.nurturing_service.find_active_sequence_by_phone", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.nurturing_service._find_member_by_phone", lambda *_args, **_kwargs: member)
    monkeypatch.setattr("app.services.nurturing_service.record_event", lambda *_args, **_kwargs: SimpleNamespace())
    monkeypatch.setattr("app.services.nurturing_service.resolve_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.nurturing_service.get_gym_instance", lambda *_args, **_kwargs: "gym_instance")
    monkeypatch.setattr(
        "app.services.nurturing_service.call_whatsapp_agent",
        lambda *_args, **_kwargs: WhatsAppAgentOutcome(
            True,
            False,
            "agent handled",
            {
                "event_id": "msg-123",
                "status": "success",
                "action": "send_reply",
                "recipient_phone": "5511999999999",
                "message": "Resposta do agente",
                "risk": "low",
                "approval_required": False,
                "metadata": {},
            },
        ),
    )

    def fake_send(*_args, **kwargs):
        send_calls.append(kwargs)
        return SimpleNamespace(status="sent")

    monkeypatch.setattr("app.services.whatsapp_agent_service.send_whatsapp_sync", fake_send)

    result = handle_incoming_whatsapp_webhook(db, _message_payload(), gym_id=gym_id)

    assert result == {"processed": True, "detail": "Agent reply sent through backend", "agent": True}
    assert send_calls[0]["phone"] == "5511999999999"
    assert send_calls[0]["message"] == "Resposta do agente"
