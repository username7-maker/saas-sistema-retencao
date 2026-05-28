from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers.whatsapp import (
    WhatsAppAgentReplyIn,
    connect_whatsapp,
    get_webhook_setup_status,
    whatsapp_agent_reply,
    whatsapp_webhook,
)


class _RequestStub:
    def __init__(self, body: dict) -> None:
        self._body = body

    async def json(self) -> dict:
        return self._body


def test_connect_whatsapp_enqueues_webhook_setup_without_query_secret(monkeypatch):
    gym_id = uuid4()
    gym = SimpleNamespace(
        id=gym_id,
        whatsapp_instance=None,
        whatsapp_status="disconnected",
        whatsapp_phone=None,
        whatsapp_connected_at=None,
    )
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4(), gym_id=gym_id)
    queued_jobs: list[dict] = []
    ensure_calls: list[dict] = []

    monkeypatch.setattr("app.routers.whatsapp.settings.whatsapp_api_url", "https://evolution.example.com")
    monkeypatch.setattr("app.routers.whatsapp.settings.whatsapp_api_token", "secret")
    monkeypatch.setattr("app.routers.whatsapp.settings.public_backend_url", "https://api.example.com")
    monkeypatch.setattr("app.routers.whatsapp.settings.whatsapp_webhook_token", "webhook-secret")
    monkeypatch.setattr("app.routers.whatsapp._get_gym", lambda *_args, **_kwargs: gym)
    def fake_ensure_instance(*_args, **kwargs):
        ensure_calls.append(kwargs)
        return "gym_instance"

    monkeypatch.setattr("app.routers.whatsapp.ensure_instance", fake_ensure_instance)
    monkeypatch.setattr("app.routers.whatsapp.get_qr_code", lambda *_args, **_kwargs: {"status": "connecting", "qrcode": "data:image/png;base64,abc"})
    job_id = uuid4()
    monkeypatch.setattr(
        "app.routers.whatsapp.enqueue_whatsapp_webhook_setup_job",
        lambda *_args, **kwargs: (
            queued_jobs.append(kwargs) or (SimpleNamespace(id=job_id, status="pending"), True)
        ),
    )

    result = connect_whatsapp(db=db, current_user=current_user)

    assert result.status == "connecting"
    assert ensure_calls[0]["fresh"] is True
    assert ensure_calls[0]["instance_name"] is None
    assert result.job_id == str(job_id)
    assert result.job_status == "pending"
    assert result.webhook_setup_created is True
    assert queued_jobs
    queued = queued_jobs[0]
    assert queued["instance"] == "gym_instance"
    assert queued["webhook_url"] == "https://api.example.com/api/v1/whatsapp/webhook"
    assert queued["webhook_headers"] == {"X-Webhook-Token": "webhook-secret"}
    db.commit.assert_called_once()


def test_get_webhook_setup_status_returns_serialized_job(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(gym_id=uuid4())
    job_id = uuid4()
    job = SimpleNamespace(id=job_id, job_type="whatsapp_webhook_setup")

    monkeypatch.setattr("app.routers.whatsapp.get_core_async_job", lambda *_args, **_kwargs: job)
    monkeypatch.setattr(
        "app.routers.whatsapp.serialize_core_async_job",
        lambda _job: {
            "job_id": job_id,
            "job_type": "whatsapp_webhook_setup",
            "status": "completed",
            "attempt_count": 1,
            "max_attempts": 5,
            "next_retry_at": None,
            "started_at": None,
            "completed_at": None,
            "queue_wait_seconds": None,
            "error_code": None,
            "error_message": None,
            "result": {"configured": True},
            "related_entity_type": "gym",
            "related_entity_id": current_user.gym_id,
        },
    )

    response = get_webhook_setup_status(job_id=job_id, db=db, current_user=current_user)

    assert response.job_id == job_id
    assert response.job_type == "whatsapp_webhook_setup"
    assert response.result == {"configured": True}


def test_get_webhook_setup_status_rejects_missing_or_wrong_type(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(gym_id=uuid4())
    job_id = uuid4()

    monkeypatch.setattr(
        "app.routers.whatsapp.get_core_async_job",
        lambda *_args, **_kwargs: SimpleNamespace(id=job_id, job_type="public_diagnosis"),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_webhook_setup_status(job_id=job_id, db=db, current_user=current_user)

    assert exc_info.value.status_code == 404


def test_whatsapp_agent_reply_uses_backend_send(monkeypatch):
    db = MagicMock()
    gym_id = uuid4()
    log_id = uuid4()

    monkeypatch.setattr("app.routers.whatsapp.settings.cordex_agent_service_token", "service-token")
    monkeypatch.setattr("app.routers.whatsapp.settings.whatsapp_agent_mode", "active")
    monkeypatch.setattr("app.routers.whatsapp.get_gym_instance", lambda *_args, **_kwargs: "gym_instance")
    monkeypatch.setattr(
        "app.routers.whatsapp.send_agent_reply_from_service_token",
        lambda *_args, **_kwargs: SimpleNamespace(id=log_id, status="sent"),
    )

    result = whatsapp_agent_reply(
        payload=WhatsAppAgentReplyIn(
            gym_id=gym_id,
            recipient_phone="5511999999999",
            message="Resposta do agente",
        ),
        authorization="Bearer service-token",
        x_cordex_agent_token=None,
        db=db,
    )

    assert result.status == "sent"
    assert result.message_log_id == str(log_id)
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_whatsapp_webhook_accepts_header_token(monkeypatch):
    gym = SimpleNamespace(
        id=uuid4(),
        whatsapp_instance="gym_instance",
        whatsapp_status="connecting",
        whatsapp_phone=None,
        whatsapp_connected_at=None,
    )
    db = MagicMock()
    db.scalar.return_value = gym

    monkeypatch.setattr("app.routers.whatsapp.settings.whatsapp_webhook_token", "webhook-secret")

    body = {
        "event": "STATUS_INSTANCE",
        "instance": "gym_instance",
        "data": {"state": "open", "ownerJid": "5511999999999@s.whatsapp.net"},
    }

    result = await whatsapp_webhook(
        request=_RequestStub(body),
        x_webhook_token="webhook-secret",
        authorization=None,
        db=db,
    )

    assert result == {"ok": True}
    assert gym.whatsapp_status == "connected"
    assert gym.whatsapp_phone == "5511999999999"
    assert isinstance(gym.whatsapp_connected_at, datetime)
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_whatsapp_webhook_rejects_missing_token(monkeypatch):
    monkeypatch.setattr("app.routers.whatsapp.settings.whatsapp_webhook_token", "webhook-secret")
    with pytest.raises(HTTPException) as exc_info:
        await whatsapp_webhook(
            request=_RequestStub({}),
            x_webhook_token=None,
            authorization=None,
            db=MagicMock(),
        )

    assert exc_info.value.status_code == 403
