import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.database import get_db


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEVICE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
JOB_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _device():
    return SimpleNamespace(id=DEVICE_ID, gym_id=GYM_ID, status="online")


def test_bridge_pair_returns_token(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    with patch(
        "app.routers.actuar_bridge.pair_actuar_bridge_device",
        return_value={
            "device_token": "bridge-token",
            "api_base_url": "https://api.example.com",
            "poll_interval_seconds": 15,
            "device": {
                "id": str(DEVICE_ID),
                "gym_id": str(GYM_ID),
                "device_name": "Recepcao",
                "status": "offline",
                "bridge_version": "0.1.0",
                "browser_name": "Chrome",
                "paired_at": None,
                "last_seen_at": None,
                "last_job_claimed_at": None,
                "last_job_completed_at": None,
                "last_error_code": None,
                "last_error_message": None,
                "revoked_at": None,
                "created_at": "2026-03-30T00:00:00Z",
                "updated_at": "2026-03-30T00:00:00Z",
            },
        },
    ) as pair_mock:
        try:
            response = client.post(
                "/api/v1/actuar-bridge/pair",
                json={
                    "pairing_code": "ABCD-1234",
                    "device_name": "Recepcao",
                    "bridge_version": "0.1.0",
                    "browser_name": "Chrome",
                },
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["device_token"] == "bridge-token"
    pair_mock.assert_called_once()
    db.commit.assert_called_once()


def test_bridge_heartbeat_requires_token_and_returns_device(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    with patch("app.routers.actuar_bridge.authenticate_actuar_bridge_device", return_value=_device()) as auth_mock, patch(
        "app.routers.actuar_bridge.heartbeat_actuar_bridge_device",
        return_value={"device": {"id": str(DEVICE_ID), "gym_id": str(GYM_ID), "device_name": "Recepcao", "status": "online", "bridge_version": None, "browser_name": None, "paired_at": None, "last_seen_at": None, "last_job_claimed_at": None, "last_job_completed_at": None, "last_error_code": None, "last_error_message": None, "revoked_at": None, "created_at": "2026-03-30T00:00:00Z", "updated_at": "2026-03-30T00:00:00Z"}, "poll_interval_seconds": 15},
    ) as heartbeat_mock:
        try:
            response = client.post("/api/v1/actuar-bridge/heartbeat", headers={"X-Actuar-Bridge-Token": "token"})
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["device"]["status"] == "online"
    auth_mock.assert_called_once()
    heartbeat_mock.assert_called_once()
    db.commit.assert_called_once()


def test_bridge_claim_returns_null_when_no_job(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    with patch("app.routers.actuar_bridge.authenticate_actuar_bridge_device", return_value=_device()), patch(
        "app.routers.actuar_bridge.claim_next_actuar_bridge_job",
        return_value=None,
    ) as claim_mock:
        try:
            response = client.post("/api/v1/actuar-bridge/jobs/claim", headers={"X-Actuar-Bridge-Token": "token"})
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text.strip() == "null"
    claim_mock.assert_called_once()
    db.commit.assert_called_once()
