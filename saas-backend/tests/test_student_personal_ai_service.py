import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.schemas.student_personal_ai import StudentPersonalAiSettingsUpdate
from app.services import student_personal_ai_service as service

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
ACTION_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def test_student_personal_ai_candidate_detects_technical_message():
    assert service.is_student_personal_ai_candidate("Pode explicar minha bioimpedancia e o treino?")


def test_student_personal_ai_candidate_ignores_general_message():
    assert not service.is_student_personal_ai_candidate("Oi, qual o horario de funcionamento?")


def test_extract_kommo_media_reference_detects_video_url():
    payload = {
        "message": {
            "text": "Agachamento",
            "attachments": [
                {
                    "type": "video",
                    "url": "https://cdn.example.com/video.mp4",
                    "mime_type": "video/mp4",
                    "size": 1234,
                    "duration": 20,
                }
            ],
        }
    }

    media = service.extract_kommo_media_reference(payload)

    assert media.is_video is True
    assert media.media_url == "https://cdn.example.com/video.mp4"
    assert media.media_type in {"video", "video/mp4"}
    assert media.file_size_bytes == 1234
    assert media.duration_seconds == 20


def test_update_student_personal_ai_settings_forces_draft_only(monkeypatch):
    settings = SimpleNamespace(extra_data={})
    db = MagicMock()
    monkeypatch.setattr(service, "get_or_create_autopilot_settings", lambda *_args, **_kwargs: settings)

    result = service.update_student_personal_ai_settings(
        db,
        gym_id=GYM_ID,
        payload=StudentPersonalAiSettingsUpdate(enabled=True, auto_send_enabled=True, mode="draft_only"),
    )

    assert result.enabled is True
    assert result.mode == "draft_only"
    assert result.auto_send_enabled is False
    assert settings.extra_data["student_personal_ai"]["auto_send_enabled"] is False


def test_serialize_student_personal_ai_draft_reads_metadata():
    now = datetime.now(tz=timezone.utc)
    action = SimpleNamespace(
        id=ACTION_ID,
        status="draft_ready",
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        lead_id=None,
        domain="trainer",
        policy_key="student_personal_ai_training_guidance",
        message_body="Oi, Ana! Vou pedir para o professor revisar.",
        metadata_json={
            "intent": "training_guidance",
            "sensitivity": "normal",
            "summary": "Solicitacao tecnica classificada como training_guidance.",
            "next_action": "Professor revisa e responde pela Kommo.",
            "recommended_owner_role": "coach",
            "blocked_reasons": [],
            "evidence": ["kommo_inbound", "student_message"],
            "received_message": "Pode revisar meu treino?",
        },
        created_at=now,
        updated_at=now,
    )

    output = service.serialize_student_personal_ai_draft(action)

    assert output.id == ACTION_ID
    assert output.status == "draft_ready"
    assert output.intent == "training_guidance"
    assert output.draft_reply.startswith("Oi, Ana")
    assert output.received_message == "Pode revisar meu treino?"
