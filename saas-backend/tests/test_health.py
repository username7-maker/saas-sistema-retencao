"""Tests for /health and /health/ready endpoints."""
from unittest.mock import MagicMock, patch


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_returns_ok_when_db_up(client):
    mock_session = MagicMock()
    with patch("app.main.SessionLocal", return_value=mock_session):
        mock_session.execute.return_value = None
        response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data["checks"]


def test_health_ready_returns_503_when_db_down(client):
    mock_session = MagicMock()
    mock_session.execute.side_effect = Exception("Connection refused")
    with patch("app.main.SessionLocal", return_value=mock_session):
        response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["database"]["status"] == "error"
