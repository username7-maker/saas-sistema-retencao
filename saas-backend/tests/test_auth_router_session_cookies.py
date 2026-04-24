from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum


USER_ID = UUID("22222222-2222-2222-2222-222222222222")
GYM_ID = UUID("11111111-1111-1111-1111-111111111111")


def _current_user():
    return SimpleNamespace(
        id=USER_ID,
        gym_id=GYM_ID,
        full_name="Owner Teste",
        email="owner@teste.com",
        role=RoleEnum.OWNER,
        is_active=True,
        deleted_at=None,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


def test_login_sets_refresh_cookie_and_hides_refresh_token(app, client, monkeypatch):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    user = _current_user()
    tokens = SimpleNamespace(
        access_token="access-token",
        refresh_token="refresh-token",
        token_type="bearer",
        expires_in=900,
    )

    monkeypatch.setattr("app.routers.auth.authenticate_user", lambda *_args, **_kwargs: user)
    monkeypatch.setattr("app.routers.auth.issue_tokens", lambda *_args, **_kwargs: tokens)
    monkeypatch.setattr("app.routers.auth.log_audit_event", lambda *_args, **_kwargs: None)

    try:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "owner@teste.com",
                "password": "Secret123!",
                "gym_slug": "academia-teste",
            },
        )

        assert response.status_code == 200
        assert response.json()["access_token"] == "access-token"
        assert response.json()["refresh_token"] is None
        assert settings.refresh_cookie_name in response.cookies
        set_cookie_header = response.headers["set-cookie"]
        assert "HttpOnly" in set_cookie_header
        assert f"samesite={settings.resolved_refresh_cookie_samesite}" in set_cookie_header.lower()
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_refresh_accepts_cookie_when_body_missing(app, client, monkeypatch):
    mock_db = MagicMock()
    mock_db.get.return_value = _current_user()
    app.dependency_overrides[get_db] = lambda: mock_db

    observed = {}
    tokens = SimpleNamespace(
        access_token="new-access-token",
        refresh_token="new-refresh-token",
        token_type="bearer",
        expires_in=900,
    )

    def _refresh(_db, refresh_token, *, commit=True):
        observed["refresh_token"] = refresh_token
        observed["commit"] = commit
        return tokens

    monkeypatch.setattr("app.routers.auth.refresh_access_token", _refresh)
    monkeypatch.setattr(
        "app.routers.auth.decode_token",
        lambda _token: {"sub": str(USER_ID), "type": "refresh", "gym_id": str(GYM_ID)},
    )
    monkeypatch.setattr("app.routers.auth.log_audit_event", lambda *_args, **_kwargs: None)

    try:
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Origin": settings.frontend_url},
            cookies={settings.refresh_cookie_name: "cookie-refresh-token"},
        )

        assert response.status_code == 200
        assert observed == {"refresh_token": "cookie-refresh-token", "commit": False}
        assert response.json()["access_token"] == "new-access-token"
        assert response.json()["refresh_token"] is None
        assert response.cookies.get(settings.refresh_cookie_name) == "new-refresh-token"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_logout_clears_refresh_cookie(app, client, monkeypatch):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = _current_user

    called = {"logout": False}

    def _logout(_db, _user, *, commit=True):
        called["logout"] = True
        assert commit is False

    monkeypatch.setattr("app.routers.auth.logout", _logout)
    monkeypatch.setattr("app.routers.auth.log_audit_event", lambda *_args, **_kwargs: None)

    try:
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer fake-access-token", "Origin": settings.frontend_url},
            cookies={settings.refresh_cookie_name: "cookie-refresh-token"},
        )

        assert response.status_code == 200
        assert called["logout"] is True
        set_cookie_header = response.headers["set-cookie"]
        assert f"{settings.refresh_cookie_name}=" in set_cookie_header
        assert "Max-Age=0" in set_cookie_header or "expires=" in set_cookie_header.lower()
        assert response.headers["Clear-Site-Data"] == "\"storage\""
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_refresh_accepts_allowed_referer_when_origin_missing(app, client, monkeypatch):
    mock_db = MagicMock()
    mock_db.get.return_value = _current_user()
    app.dependency_overrides[get_db] = lambda: mock_db

    tokens = SimpleNamespace(
        access_token="new-access-token",
        refresh_token="new-refresh-token",
        token_type="bearer",
        expires_in=900,
    )

    monkeypatch.setattr("app.routers.auth.refresh_access_token", lambda *_args, **_kwargs: tokens)
    monkeypatch.setattr(
        "app.routers.auth.decode_token",
        lambda _token: {"sub": str(USER_ID), "type": "refresh", "gym_id": str(GYM_ID)},
    )
    monkeypatch.setattr("app.routers.auth.log_audit_event", lambda *_args, **_kwargs: None)

    try:
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Referer": f"{settings.frontend_url}/dashboard"},
            cookies={settings.refresh_cookie_name: "cookie-refresh-token"},
        )

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
    finally:
        app.dependency_overrides.clear()


def test_refresh_rejects_disallowed_origin(app, client):
    response = client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "https://evil.example"},
        cookies={settings.refresh_cookie_name: "cookie-refresh-token"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Origem nao autorizada"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"


def test_logout_rejects_disallowed_origin(app, client):
    app.dependency_overrides[get_current_user] = _current_user
    try:
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer fake-access-token", "Origin": "https://evil.example"},
            cookies={settings.refresh_cookie_name: "cookie-refresh-token"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Origem nao autorizada"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"
    finally:
        app.dependency_overrides.clear()


def test_logout_accepts_allowed_referer_when_origin_missing(app, client, monkeypatch):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = _current_user

    monkeypatch.setattr("app.routers.auth.logout", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.routers.auth.log_audit_event", lambda *_args, **_kwargs: None)

    try:
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer fake-access-token", "Referer": f"{settings.frontend_url}/dashboard"},
            cookies={settings.refresh_cookie_name: "cookie-refresh-token"},
        )

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
    finally:
        app.dependency_overrides.clear()
