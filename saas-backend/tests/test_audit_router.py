from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.dependencies import get_current_user
from app.database import get_db


def test_create_ui_event_logs_audit_event(app, mock_owner):
    fake_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: mock_owner
    app.dependency_overrides[get_db] = lambda: fake_db

    try:
        from fastapi.testclient import TestClient

        with TestClient(app, raise_server_exceptions=False) as client:
            with patch("app.routers.audit.log_audit_event", return_value=SimpleNamespace()) as mock_log:
                response = client.post(
                    "/api/v1/audit/events",
                    json={
                        "event_name": "action_center_viewed",
                        "surface": "action_center",
                        "details": {"total_items": 12},
                    },
                )

        assert response.status_code == 202
        assert response.json()["message"] == "Evento registrado"
        assert mock_log.call_args.kwargs["action"] == "ui_event_action_center_viewed"
        assert mock_log.call_args.kwargs["entity"] == "action_center"
        assert mock_log.call_args.kwargs["details"]["total_items"] == 12
        fake_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()
