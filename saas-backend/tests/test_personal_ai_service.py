import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.schemas.personal_ai import PersonalAiContextOut, PersonalAiSettingsUpdate
from app.services import personal_ai_service as service

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
ACTION_ID = uuid.UUID("77777777-7777-7777-7777-777777777777")


def test_personal_ai_classifies_body_composition_request():
    result = service.classify_personal_ai_request("Explique a bioimpedancia do aluno")

    assert result.intent == "body_composition_explanation"
    assert result.sensitivity == "normal"
    assert result.recommended_owner_role == "coach"
    assert result.blocked_reasons == []


def test_personal_ai_blocks_injury_request():
    result = service.classify_personal_ai_request("Aluno relatou dor forte no joelho, o que responder?")

    assert result.intent == "injury"
    assert result.sensitivity == "sensitive"
    assert "sensitive_injury_or_pain" in result.blocked_reasons


def test_personal_ai_blocks_autonomous_prescription():
    result = service.classify_personal_ai_request("Monte um treino novo para hipertrofia")

    assert result.intent == "training_guidance"
    assert "autonomous_prescription_not_allowed" in result.blocked_reasons


def test_personal_ai_only_requires_active_member_for_training_or_routine():
    assert service._requires_active_member_for_personal_ai("routine_support") is True
    assert service._requires_active_member_for_personal_ai("training_guidance") is True
    assert service._requires_active_member_for_personal_ai("assessment_explanation") is False
    assert service._requires_active_member_for_personal_ai("body_composition_explanation") is False


def test_update_personal_ai_settings_forces_coach_review(monkeypatch):
    settings = SimpleNamespace(extra_data={})
    db = MagicMock()
    monkeypatch.setattr(service, "get_or_create_autopilot_settings", lambda *_args, **_kwargs: settings)

    result = service.update_personal_ai_settings(
        db,
        gym_id=GYM_ID,
        payload=PersonalAiSettingsUpdate(enabled=True, auto_send_enabled=True, mode="coach_review"),
    )

    assert result.enabled is True
    assert result.mode == "coach_review"
    assert result.auto_send_enabled is False
    assert settings.extra_data["personal_ai"]["auto_send_enabled"] is False


def test_serialize_personal_ai_draft_reads_context_snapshot():
    now = datetime.now(tz=timezone.utc)
    context = PersonalAiContextOut(
        member_id=MEMBER_ID,
        member_name="Ana Silva",
        active_training_plan={"name": "Treino Base", "sessions_per_week": 3},
        evidence=["active_training_plan"],
    )
    action = SimpleNamespace(
        id=ACTION_ID,
        status="draft_ready",
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        policy_key="personal_ai_routine_support",
        message_body="Oi, Ana! Mantenha a rotina do treino atual.",
        metadata_json={
            "intent": "routine_support",
            "sensitivity": "normal",
            "summary": "Solicitacao tecnica classificada como routine_support.",
            "next_action": "Professor revisa o rascunho antes de usar com o aluno.",
            "recommended_owner_role": "coach",
            "blocked_reasons": [],
            "evidence": ["active_training_plan"],
            "question": "Como orientar a rotina?",
            "context_snapshot": context.model_dump(mode="json"),
        },
        created_at=now,
        updated_at=now,
    )

    output = service.serialize_personal_ai_draft(action)

    assert output.id == ACTION_ID
    assert output.intent == "routine_support"
    assert output.context_snapshot is not None
    assert output.context_snapshot.member_name == "Ana Silva"
    assert output.draft_reply.startswith("Oi, Ana")
