from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers.whatsapp import connect_whatsapp, whatsapp_webhook


class _BackgroundTasksRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def add_task(self, func, *args, **kwargs) -> None:
        self.calls.append((func, args, kwargs))


class _RequestStub:
    def __init__(self, body: dict) -> None:
        self._body = body

    async def json(self) -> dict:
        return self._body


def test_connect_whatsapp_configures_webhook_without_query_secret(monkeypatch):
    gym_id = uuid4()
    gym = SimpleNamespace(
        id=gym_id,
        whatsapp_instance=None,
        whatsapp_status="disconnected",
        whatsapp_phone=None,
        whatsapp_connected_at=None,
    )
    db = MagicMock()
    background_tasks = _BackgroundTasksRecorder()
    current_user = SimpleNamespace(gym_id=gym_id)

    monkeypatch.setattr("app.routers.whatsapp.settings.whatsapp_api_url", "https://evolution.example.com")
    monkeypatch.setattr("app.routers.whatsapp.settings.whatsapp_api_token", "secret")
    monkeypatch.setattr("app.routers.whatsapp.settings.public_backend_url", "https://api.example.com")
    monkeypatch.setattr("app.routers.whatsapp.settings.whatsapp_webhook_token", "webhook-secret")
    monkeypatch.setattr("app.routers.whatsapp._get_gym", lambda *_args, **_kwargs: gym)
    monkeypatch.setattr("app.routers.whatsapp.ensure_instance", lambda *_args, **_kwargs: "gym_instance")
    monkeypatch.setattr("app.routers.whatsapp.get_qr_code", lambda *_args, **_kwargs: {"status": "connecting", "qrcode": "data:image/png;base64,abc"})

    result = connect_whatsapp(db=db, current_user=current_user, background_tasks=background_tasks)

    assert result.status == "connecting"
    assert background_tasks.calls
    _, args, _ = background_tasks.calls[0]
    assert args[0] == "gym_instance"
    assert args[1] == "https://api.example.com/api/v1/whatsapp/webhook"
    assert args[2] == {"X-Webhook-Token": "webhook-secret"}


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
        token=None,
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
            token=None,
            x_webhook_token=None,
            authorization=None,
            db=MagicMock(),
        )

    assert exc_info.value.status_code == 403
