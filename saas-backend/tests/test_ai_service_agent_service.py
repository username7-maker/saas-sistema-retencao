import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.schemas.ai_service_agent import AiServiceAgentSettingsUpdate
from app.services import ai_service_agent_service as service

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
ACTION_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def test_ai_service_agent_classifies_simple_assessment_message():
    result = service.classify_kommo_message("Oi, quero marcar minha avaliacao e falar do treino")

    assert result.intent == "assessment"
    assert result.sensitivity == "normal"
    assert result.recommended_owner_role == "coach"
    assert result.blocked_reasons == []


def test_ai_service_agent_sensitive_cancellation_escalates():
    result = service.classify_kommo_message("Quero cancelar meu plano e falar com gerente")

    assert result.intent == "cancellation"
    assert result.sensitivity == "sensitive"
    assert "sensitive_cancellation" in result.blocked_reasons
    assert result.recommended_owner_role == "manager"


def test_update_ai_service_agent_settings_forces_draft_only(monkeypatch):
    settings = SimpleNamespace(extra_data={})
    db = MagicMock()
    monkeypatch.setattr(service, "get_or_create_autopilot_settings", lambda *_args, **_kwargs: settings)

    result = service.update_ai_service_agent_settings(
        db,
        gym_id=GYM_ID,
        payload=AiServiceAgentSettingsUpdate(enabled=True, auto_send_enabled=True, mode="draft_only"),
    )

    assert result.enabled is True
    assert result.mode == "draft_only"
    assert result.auto_send_enabled is False
    assert settings.extra_data["ai_service_agent"]["auto_send_enabled"] is False


def test_serialize_ai_service_agent_draft_reads_metadata():
    now = datetime.now(tz=timezone.utc)
    action = SimpleNamespace(
        id=ACTION_ID,
        status="draft_ready",
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        lead_id=None,
        domain="retention",
        policy_key="ai_service_agent_retention",
        message_body="Oi, Ana! Posso te ajudar a voltar esta semana?",
        metadata_json={
            "intent": "retention",
            "sensitivity": "normal",
            "summary": "Mensagem Kommo classificada como retention.",
            "next_action": "Revisar resposta sugerida e enviar pela Kommo.",
            "recommended_owner_role": "reception",
            "blocked_reasons": [],
            "evidence": ["kommo_inbound", "intent:retention"],
            "received_message": "Quero voltar a treinar",
        },
        created_at=now,
        updated_at=now,
    )

    output = service.serialize_ai_service_agent_draft(action)

    assert output.id == ACTION_ID
    assert output.status == "draft_ready"
    assert output.intent == "retention"
    assert output.draft_reply.startswith("Oi, Ana")
    assert output.received_message == "Quero voltar a treinar"
