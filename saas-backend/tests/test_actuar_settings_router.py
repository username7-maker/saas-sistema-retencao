import uuid
from datetime import datetime
from types import SimpleNamespace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _current_user(role: RoleEnum) -> SimpleNamespace:
    return SimpleNamespace(
        id=USER_ID,
        gym_id=GYM_ID,
        role=role,
        is_active=True,
        deleted_at=None,
    )


def _settings_payload():
    return {
        "actuar_enabled": True,
        "actuar_auto_sync_body_composition": True,
        "actuar_base_url": "https://actuar.example",
        "actuar_username": "owner",
        "actuar_has_password": True,
        "environment_enabled": True,
        "environment_sync_mode": "csv_export",
        "effective_sync_mode": "assisted_rpa",
        "automatic_sync_ready": True,
        "bridge_device_count": 0,
        "bridge_online_device_count": 0,
        "bridge_devices": [],
    }


def test_get_actuar_settings_requires_owner_or_manager(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.RECEPTIONIST)

    try:
        response = client.get("/api/v1/settings/actuar")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_get_actuar_settings_returns_payload(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)

    with patch("app.routers.settings.get_actuar_settings", return_value=_settings_payload()) as get_mock:
        try:
            response = client.get("/api/v1/settings/actuar")
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["effective_sync_mode"] == "assisted_rpa"
    get_mock.assert_called_once()


def test_update_actuar_settings_logs_and_commits(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.MANAGER)

    with patch("app.routers.settings.update_actuar_settings", return_value=_settings_payload()) as update_mock, patch(
        "app.routers.settings.log_audit_event"
    ) as audit_mock:
        try:
            response = client.put(
                "/api/v1/settings/actuar",
                json={
                    "actuar_enabled": True,
                    "actuar_auto_sync_body_composition": True,
                    "actuar_base_url": "https://actuar.example",
                    "actuar_username": "owner",
                    "actuar_password": "segredo",
                    "clear_password": False,
                },
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["automatic_sync_ready"] is True
    update_mock.assert_called_once()
    audit_mock.assert_called_once()
    db.commit.assert_called_once()


def test_test_actuar_connection_returns_result(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)

    with patch(
        "app.routers.settings.test_actuar_connection",
        return_value={
            "success": True,
            "provider": "actuar_assisted_rpa",
            "effective_sync_mode": "assisted_rpa",
            "automatic_sync_ready": True,
            "message": "Conexao com o Actuar validada com sucesso.",
            "detail": "ok",
        },
    ) as test_mock, patch("app.routers.settings.log_audit_event") as audit_mock:
        try:
            response = client.post("/api/v1/settings/actuar/test-connection")
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["success"] is True
    test_mock.assert_called_once()
    audit_mock.assert_called_once()
    db.commit.assert_called_once()


def test_issue_actuar_bridge_pairing_code_logs_and_commits(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)

    with patch(
        "app.routers.settings.issue_actuar_bridge_pairing_code",
        return_value=SimpleNamespace(
            device_id=uuid.uuid4(),
            pairing_code="ABCD-1234",
            expires_at=datetime(2026, 3, 30, 23, 59, 0),
        ),
    ) as pairing_mock, patch("app.routers.settings.log_audit_event") as audit_mock:
        try:
            response = client.post("/api/v1/settings/actuar/bridge/pairing-code")
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    pairing_mock.assert_called_once()
    audit_mock.assert_called_once()
    db.commit.assert_called_once()
