from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum


GYM_ID = UUID("11111111-1111-1111-1111-111111111111")


def _current_user(role: RoleEnum, user_id: str = "22222222-2222-2222-2222-222222222222"):
    return SimpleNamespace(
        id=UUID(user_id),
        gym_id=GYM_ID,
        full_name=f"{role.value.title()} Teste",
        email=f"{role.value}@teste.com",
        role=role,
        is_active=True,
        job_title=None,
        avatar_url=None,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        deleted_at=None,
    )


def _target_user(role: RoleEnum, user_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=UUID(user_id),
        gym_id=GYM_ID,
        full_name=f"{role.value.title()} Alvo",
        email=f"{role.value}.alvo@teste.com",
        role=role,
        is_active=True,
        job_title=None,
        avatar_url=None,
        deleted_at=None,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )


def test_manager_cannot_create_owner_or_manager(app, client):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.MANAGER)

    try:
        response = client.post(
            "/api/v1/users/",
            json={
                "full_name": "Novo Owner",
                "email": "owner.novo@teste.com",
                "password": "Secret123!",
                "role": "owner",
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Gerente nao pode criar owner ou gerente"
    finally:
        app.dependency_overrides.clear()


def test_owner_create_user_route_defers_commit_until_after_audit(app, client, monkeypatch):
    created = _target_user(RoleEnum.RECEPTIONIST, "77777777-7777-7777-7777-777777777777")
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)

    calls = []

    def _create_user(_db, payload, *, gym_id, commit=True):
        calls.append({"gym_id": gym_id, "commit": commit, "email": payload.email})
        return created

    monkeypatch.setattr("app.routers.users.create_user", _create_user)

    try:
        response = client.post(
            "/api/v1/users/",
            json={
                "full_name": "Nova Recepcao",
                "email": "recepcao.nova@teste.com",
                "password": "Secret123!",
                "role": "receptionist",
            },
        )

        assert response.status_code == 201
        assert calls == [{"gym_id": GYM_ID, "commit": False, "email": "recepcao.nova@teste.com"}]
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_manager_can_toggle_non_owner_activation(app, client):
    target = _target_user(RoleEnum.RECEPTIONIST, "33333333-3333-3333-3333-333333333333")
    mock_db = MagicMock()
    mock_db.scalar.return_value = target
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.MANAGER)

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/activation",
            json={"is_active": False},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_manager_cannot_toggle_owner_activation(app, client):
    target = _target_user(RoleEnum.OWNER, "44444444-4444-4444-4444-444444444444")
    mock_db = MagicMock()
    mock_db.scalar.return_value = target
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.MANAGER)

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/activation",
            json={"is_active": False},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Gerente nao pode ativar ou desativar owner"
    finally:
        app.dependency_overrides.clear()


def test_owner_can_update_team_profile_fields(app, client):
    target = _target_user(RoleEnum.RECEPTIONIST, "55555555-5555-5555-5555-555555555555")
    mock_db = MagicMock()
    mock_db.scalar.return_value = target
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/profile",
            json={
                "full_name": "Recepcao Editada",
                "job_title": "Atendimento",
                "avatar_url": "https://cdn.exemplo.com/avatar.png",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["full_name"] == "Recepcao Editada"
        assert body["job_title"] == "Atendimento"
        assert body["avatar_url"] == "https://cdn.exemplo.com/avatar.png"
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_manager_cannot_edit_owner_profile(app, client):
    target = _target_user(RoleEnum.OWNER, "66666666-6666-6666-6666-666666666666")
    mock_db = MagicMock()
    mock_db.scalar.return_value = target
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.MANAGER)

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/profile",
            json={"job_title": "Diretoria"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Gerente nao pode editar perfil do owner"
    finally:
        app.dependency_overrides.clear()


def test_user_can_update_own_profile(app, client):
    current_user = _current_user(RoleEnum.RECEPTIONIST)
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    try:
        response = client.patch(
            "/api/v1/users/me/profile",
            json={
                "full_name": "Recepcao Piloto",
                "job_title": "Front desk",
                "avatar_url": "https://cdn.exemplo.com/me.png",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["full_name"] == "Recepcao Piloto"
        assert body["job_title"] == "Front desk"
        assert body["avatar_url"] == "https://cdn.exemplo.com/me.png"
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()
