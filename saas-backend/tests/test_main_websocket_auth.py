from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app, _allowed_websocket_origins, _extract_websocket_auth_token, _resolve_websocket_origin


def test_extract_websocket_auth_token_returns_token_for_valid_auth_message():
    token = _extract_websocket_auth_token('{"type":"auth","token":"jwt-token"}')
    assert token == "jwt-token"


def test_extract_websocket_auth_token_rejects_non_auth_messages():
    token = _extract_websocket_auth_token('{"type":"ping","token":"jwt-token"}')
    assert token is None


def test_extract_websocket_auth_token_rejects_invalid_json():
    token = _extract_websocket_auth_token("not-json")
    assert token is None


def test_resolve_websocket_origin_prefers_origin_header():
    websocket = SimpleNamespace(headers={"origin": settings.frontend_url, "referer": "https://evil.example/path"})
    assert _resolve_websocket_origin(websocket) == settings.frontend_url


def test_resolve_websocket_origin_falls_back_to_referer_origin():
    websocket = SimpleNamespace(headers={"referer": f"{settings.frontend_url}/dashboard"})
    assert _resolve_websocket_origin(websocket) == settings.frontend_url


def test_allowed_websocket_origins_include_frontend_url():
    assert settings.frontend_url in _allowed_websocket_origins()


def test_updates_websocket_authenticates_after_initial_accept(monkeypatch):
    user_id = uuid4()
    gym_id = uuid4()
    fake_user = SimpleNamespace(id=user_id, gym_id=gym_id, is_active=True, deleted_at=None)
    fake_db = SimpleNamespace(get=lambda model, id_: fake_user, close=lambda: None)

    monkeypatch.setattr("app.main.decode_token", lambda token: {"sub": str(user_id), "gym_id": str(gym_id), "type": "access"})
    monkeypatch.setattr("app.main.SessionLocal", lambda: fake_db)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/updates", headers={"origin": settings.frontend_url}) as websocket:
            websocket.send_text('{"type":"auth","token":"jwt-token"}')
            payload = websocket.receive_json()

    assert payload["event"] == "connected"
    assert payload["payload"]["user_id"] == str(user_id)
    assert payload["payload"]["gym_id"] == str(gym_id)
