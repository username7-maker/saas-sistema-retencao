"""Tests for /health and /health/ready endpoints."""
from unittest.mock import MagicMock, patch

from app.core.config import settings


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"
    assert (
        response.headers["Content-Security-Policy"]
        == "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'"
    )


def test_health_ready_returns_ok_when_db_up(client):
    mock_session = MagicMock()
    with patch("app.main.SessionLocal", return_value=mock_session):
        mock_session.execute.return_value = None
        response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data["checks"]
    assert "error" not in data["checks"]["database"]


def test_health_ready_returns_503_when_db_down(client):
    mock_session = MagicMock()
    mock_session.execute.side_effect = Exception("Connection refused")
    with patch("app.main.SessionLocal", return_value=mock_session):
        response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["database"]["status"] == "error"
    assert "error" not in data["checks"]["database"]


def test_health_ready_returns_ok_when_redis_not_required(client):
    mock_session = MagicMock()
    with (
        patch("app.main.SessionLocal", return_value=mock_session),
        patch("app.main.dashboard_cache.healthcheck", return_value={"available": False, "backend": "memory"}),
        patch.object(settings, "redis_url", ""),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["cache"]["status"] == "ok"


def test_health_ready_returns_503_when_required_redis_is_down(client):
    mock_session = MagicMock()
    with (
        patch("app.main.SessionLocal", return_value=mock_session),
        patch("app.main.dashboard_cache.healthcheck", return_value={"available": False, "backend": "redis"}),
        patch.object(settings, "redis_url", "redis://redis:6379/0"),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["cache"]["status"] == "error"


def test_health_ready_hides_dependency_details_in_production(client):
    mock_session = MagicMock()
    with (
        patch("app.main.SessionLocal", return_value=mock_session),
        patch("app.main.dashboard_cache.healthcheck", return_value={"available": True, "backend": "redis"}),
        patch.object(settings, "environment", "production"),
    ):
        response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}
    assert response.headers["Strict-Transport-Security"] == "max-age=63072000; includeSubDomains; preload"
