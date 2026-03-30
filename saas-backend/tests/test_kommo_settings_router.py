import uuid
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
        "kommo_enabled": True,
        "kommo_base_url": "https://crm.kommo.example",
        "kommo_has_access_token": True,
        "kommo_default_pipeline_id": "111",
        "kommo_default_stage_id": "222",
        "kommo_default_responsible_user_id": "333",
        "automatic_handoff_ready": True,
    }


def test_get_kommo_settings_requires_owner_or_manager(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.RECEPTIONIST)

    try:
        response = client.get("/api/v1/settings/kommo")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_get_kommo_settings_returns_payload(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)

    with patch("app.routers.settings.get_kommo_settings", return_value=_settings_payload()) as get_mock:
        try:
            response = client.get("/api/v1/settings/kommo")
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["automatic_handoff_ready"] is True
    get_mock.assert_called_once()


def test_update_kommo_settings_logs_and_commits(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.MANAGER)

    with patch("app.routers.settings.update_kommo_settings", return_value=_settings_payload()) as update_mock, patch(
        "app.routers.settings.log_audit_event"
    ) as audit_mock:
        try:
            response = client.put(
                "/api/v1/settings/kommo",
                json={
                    "kommo_enabled": True,
                    "kommo_base_url": "https://crm.kommo.example",
                    "kommo_access_token": "secret-token",
                    "kommo_default_pipeline_id": "111",
                    "kommo_default_stage_id": "222",
                    "kommo_default_responsible_user_id": "333",
                    "clear_access_token": False,
                },
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["kommo_has_access_token"] is True
    update_mock.assert_called_once()
    audit_mock.assert_called_once()
    db.commit.assert_called_once()


def test_test_kommo_connection_returns_result(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)

    with patch(
        "app.routers.settings.test_kommo_connection_for_gym",
        return_value={
            "success": True,
            "automatic_handoff_ready": True,
            "message": "Conexao com a Kommo validada com sucesso.",
            "detail": "Conta identificada: Academia Teste.",
            "base_url": "https://crm.kommo.example",
        },
    ) as test_mock, patch("app.routers.settings.log_audit_event") as audit_mock:
        try:
            response = client.post("/api/v1/settings/kommo/test-connection")
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["success"] is True
    test_mock.assert_called_once()
    audit_mock.assert_called_once()
    db.commit.assert_called_once()
