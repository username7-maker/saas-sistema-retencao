import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models import MovementVideoReview
from app.schemas.movement_video import (
    MovementVideoAiSettingsOut,
    MovementVideoAiSettingsUpdate,
    MovementVideoAnalyzeInput,
    MovementVideoApproveInput,
    MovementVideoReviewCreate,
)
from app.services import movement_video_service as service

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
TRAINER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
REVIEW_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _settings(**overrides):
    data = dict(service.DEFAULT_MOVEMENT_VIDEO_AI_SETTINGS)
    data.update({"enabled": True})
    data.update(overrides)
    return MovementVideoAiSettingsOut(**service._merge_settings(data))


def _review(**overrides):
    now = datetime.now(tz=timezone.utc)
    data = {
        "id": REVIEW_ID,
        "gym_id": GYM_ID,
        "member_id": MEMBER_ID,
        "trainer_user_id": TRAINER_ID,
        "exercise_name": "Agachamento",
        "video_asset_url": "https://example.com/agachamento.mp4",
        "video_asset_hash": None,
        "media_type": "video/mp4",
        "file_size_bytes": 1024,
        "duration_seconds": 30,
        "original_video_stored": False,
        "status": "pending_review",
        "analysis_status": "not_started",
        "safety_level": "coach_review",
        "summary": None,
        "detected_points": [],
        "suggested_feedback": None,
        "coach_feedback": None,
        "blocked_reasons": [],
        "metadata_json": {},
        "created_at": now,
        "updated_at": now,
        "reviewed_at": None,
        "rejected_at": None,
    }
    data.update(overrides)
    return MovementVideoReview(**data)


def test_update_movement_video_settings_forces_safe_defaults(monkeypatch):
    settings = SimpleNamespace(extra_data={})
    db = MagicMock()
    monkeypatch.setattr(service, "get_or_create_autopilot_settings", lambda *_args, **_kwargs: settings)

    result = service.update_movement_video_ai_settings(
        db,
        gym_id=GYM_ID,
        payload=MovementVideoAiSettingsUpdate(enabled=True, auto_send_enabled=True, store_original_video=True),
    )

    assert result.enabled is True
    assert result.mode == "coach_review"
    assert result.auto_send_enabled is False
    assert result.store_original_video is False
    assert settings.extra_data["movement_video_ai"]["auto_send_enabled"] is False


def test_create_movement_video_review_blocks_missing_image_consent(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(service, "_get_member_or_404", lambda *_args, **_kwargs: SimpleNamespace(id=MEMBER_ID))
    monkeypatch.setattr(service, "get_movement_video_ai_settings", lambda *_args, **_kwargs: _settings())
    monkeypatch.setattr(service, "current_consent_status_map", lambda *_args, **_kwargs: {"image": False})
    monkeypatch.setattr(service, "record_event", lambda *_args, **_kwargs: None)

    result = service.create_movement_video_review(
        db,
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        trainer_user_id=TRAINER_ID,
        payload=MovementVideoReviewCreate(
            exercise_name="Agachamento",
            video_asset_url="https://example.com/agachamento.mp4",
            media_type="video/mp4",
            file_size_bytes=1024,
            duration_seconds=30,
        ),
    )

    assert result.status == "blocked"
    assert result.analysis_status == "blocked"
    assert "missing_image_consent" in result.blocked_reasons
    assert result.original_video_stored is False


def test_analyze_movement_video_review_stays_manual_observation(monkeypatch):
    db = MagicMock()
    review = _review()
    monkeypatch.setattr(service, "_get_review_or_404", lambda *_args, **_kwargs: review)
    monkeypatch.setattr(service, "record_event", lambda *_args, **_kwargs: None)

    result = service.analyze_movement_video_review(
        db,
        gym_id=GYM_ID,
        review_id=REVIEW_ID,
        payload=MovementVideoAnalyzeInput(coach_observation="Joelho entrou levemente."),
    )

    assert result.status == "needs_coach_review"
    assert result.analysis_status == "manual_observation"
    assert result.safety_level == "coach_review"
    assert "nao emite veredito tecnico autonomo" in result.detected_points[0]["description"]
    assert any(point["label"] == "Observacao inicial do professor" for point in result.detected_points)


def test_approve_blocked_review_is_rejected(monkeypatch):
    db = MagicMock()
    review = _review(status="blocked", blocked_reasons=["missing_image_consent"])
    monkeypatch.setattr(service, "_get_review_or_404", lambda *_args, **_kwargs: review)

    with pytest.raises(HTTPException) as exc:
        service.approve_movement_video_review(
            db,
            gym_id=GYM_ID,
            review_id=REVIEW_ID,
            payload=MovementVideoApproveInput(coach_feedback="Boa execucao, ajuste postura."),
        )

    assert exc.value.status_code == 409
