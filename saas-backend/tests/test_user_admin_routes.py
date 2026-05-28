from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum
from app.utils.email import EmailSendResult


GYM_ID = UUID("11111111-1111-1111-1111-111111111111")


def _current_user(role: RoleEnum, user_id: str = "22222222-2222-2222-2222-222222222222"):
    return SimpleNamespace(
        id=UUID(user_id),
        gym_id=GYM_ID,
        full_name=f"{role.value.title()} Teste",
        email=f"{role.value}@teste.com",
        role=role,
        hashed_password="current_hash",
        refresh_token_hash="old_refresh_hash",
        refresh_token_expires_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        password_reset_token_hash="old_reset_hash",
        password_reset_expires_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        is_active=True,
        job_title=None,
        work_shift=None,
        work_shift_scope=None,
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
        hashed_password="old_hash",
        refresh_token_hash="old_refresh_hash",
        refresh_token_expires_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        password_reset_token_hash="old_reset_hash",
        password_reset_expires_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        is_active=True,
        job_title=None,
        work_shift=None,
        work_shift_scope=None,
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


def test_owner_create_user_route_invites_user_to_define_password(app, client, monkeypatch):
    created = _target_user(RoleEnum.RECEPTIONIST, "77777777-7777-7777-7777-777777777777")
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)
    monkeypatch.setattr("app.routers.users.generate_bootstrap_password", lambda: "BootstrapOnly123")
    setup_calls = []
    monkeypatch.setattr(
        "app.routers.users.send_password_setup_email",
        lambda _db, *, user, commit: setup_calls.append({"user": user, "commit": commit})
        or EmailSendResult(sent=True, blocked=False, reason="sent"),
    )

    calls = []

    def _create_user(_db, payload, *, gym_id, commit=True):
        calls.append(
            {
                "gym_id": gym_id,
                "commit": commit,
                "email": payload.email,
                "password": payload.password,
                "work_shift": payload.work_shift,
                "work_shift_scope": payload.work_shift_scope,
            }
        )
        return created

    monkeypatch.setattr("app.routers.users.create_user", _create_user)

    try:
        response = client.post(
            "/api/v1/users/",
            json={
                "full_name": "Nova Recepcao",
                "email": "recepcao.nova@teste.com",
                "role": "receptionist",
                "password_setup": "invite",
                "work_shift": "morning",
                "work_shift_scope": ["morning", "afternoon"],
            },
        )

        assert response.status_code == 201
        assert calls == [
            {
                "gym_id": GYM_ID,
                "commit": False,
                "email": "recepcao.nova@teste.com",
                "password": "BootstrapOnly123",
                "work_shift": "morning",
                "work_shift_scope": ["morning", "afternoon"],
            }
        ]
        assert setup_calls == [{"user": created, "commit": False}]
        assert response.json()["temporary_password"] is None
        assert response.json()["setup_status"] == "invite_sent"
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_owner_create_user_route_accepts_manual_password_by_default(app, client, monkeypatch):
    created = _target_user(RoleEnum.RECEPTIONIST, "77777777-7777-7777-7777-777777777777")
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)
    send_setup = MagicMock()
    monkeypatch.setattr("app.routers.users.send_password_setup_email", send_setup)

    calls = []

    def _create_user(_db, payload, *, gym_id, commit=True):
        calls.append({"password": payload.password, "commit": commit, "gym_id": gym_id})
        return created

    monkeypatch.setattr("app.routers.users.create_user", _create_user)

    try:
        response = client.post(
            "/api/v1/users/",
            json={
                "full_name": "Nova Recepcao",
                "email": "recepcao.nova@teste.com",
                "role": "receptionist",
                "password": "SenhaManual123",
            },
        )

        assert response.status_code == 201
        assert calls == [{"password": "SenhaManual123", "commit": False, "gym_id": GYM_ID}]
        assert response.json()["temporary_password"] is None
        assert response.json()["setup_status"] == "manual_password_set"
        send_setup.assert_not_called()
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_owner_can_generate_temporary_password_on_create_when_requested(app, client, monkeypatch):
    created = _target_user(RoleEnum.RECEPTIONIST, "77777777-7777-7777-7777-777777777777")
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)
    monkeypatch.setattr("app.routers.users.generate_temporary_password", lambda: "TempPass1234")
    send_setup = MagicMock()
    monkeypatch.setattr("app.routers.users.send_password_setup_email", send_setup)

    def _create_user(_db, payload, *, gym_id, commit=True):
        assert payload.password == "TempPass1234"
        return created

    monkeypatch.setattr("app.routers.users.create_user", _create_user)

    try:
        response = client.post(
            "/api/v1/users/",
            json={
                "full_name": "Nova Recepcao",
                "email": "recepcao.nova@teste.com",
                "role": "receptionist",
                "password_setup": "temporary",
            },
        )

        assert response.status_code == 201
        assert response.json()["temporary_password"] == "TempPass1234"
        assert response.json()["setup_status"] == "temporary_password_generated"
        send_setup.assert_not_called()
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_create_user_invite_rolls_back_when_email_provider_blocks(app, client, monkeypatch):
    created = _target_user(RoleEnum.RECEPTIONIST, "77777777-7777-7777-7777-777777777777")
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)
    monkeypatch.setattr("app.routers.users.generate_bootstrap_password", lambda: "BootstrapOnly123")
    monkeypatch.setattr("app.routers.users.create_user", lambda *_args, **_kwargs: created)
    monkeypatch.setattr(
        "app.routers.users.send_password_setup_email",
        lambda *_args, **_kwargs: EmailSendResult(sent=False, blocked=True, reason="sender_identity_unverified"),
    )

    try:
        response = client.post(
            "/api/v1/users/",
            json={
                "full_name": "Nova Recepcao",
                "email": "recepcao.nova@teste.com",
                "role": "receptionist",
                "password_setup": "invite",
            },
        )

        assert response.status_code == 503
        assert response.json()["detail"] == "Nao foi possivel enviar o convite de senha. Use senha provisoria apenas se o usuario solicitou."
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_list_users_tolerates_legacy_internal_email_domains(app, client):
    owner = _current_user(RoleEnum.OWNER)
    legacy_user = _target_user(RoleEnum.TRAINER, "88888888-8888-8888-8888-888888888888")
    legacy_user.email = "ai-triage-validation@automai.local"

    mock_db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [owner, legacy_user]
    mock_db.scalars.return_value = mock_scalars
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: owner

    try:
        response = client.get("/api/v1/users/")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[1]["email"] == "ai-triage-validation@automai.local"
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
                "work_shift": "morning",
                "work_shift_scope": ["morning", "afternoon"],
                "avatar_url": "https://cdn.exemplo.com/avatar.png",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["full_name"] == "Recepcao Editada"
        assert body["job_title"] == "Atendimento"
        assert body["work_shift"] == "morning"
        assert body["work_shift_scope"] == ["morning", "afternoon"]
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


def test_owner_can_generate_temporary_password_for_non_owner(app, client, monkeypatch):
    target = _target_user(RoleEnum.TRAINER, "99999999-9999-9999-9999-999999999999")
    mock_db = MagicMock()
    mock_db.scalar.return_value = target
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)
    audit_calls = []
    monkeypatch.setattr("app.routers.users.generate_temporary_password", lambda: "TempPass1234")
    monkeypatch.setattr("app.routers.users.hash_password", lambda value: f"hash:{value}")
    monkeypatch.setattr(
        "app.routers.users.log_audit_event",
        lambda *args, **kwargs: audit_calls.append(kwargs),
    )

    try:
        response = client.post(f"/api/v1/users/{target.id}/password-reset")

        assert response.status_code == 200
        assert response.json() == {"temporary_password": "TempPass1234"}
        assert target.hashed_password == "hash:TempPass1234"
        assert target.refresh_token_hash is None
        assert target.refresh_token_expires_at is None
        assert target.password_reset_token_hash is None
        assert target.password_reset_expires_at is None
        assert audit_calls[0]["details"] == {"target_role": "trainer"}
        assert "TempPass1234" not in str(audit_calls[0]["details"])
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_manager_cannot_generate_temporary_password_for_manager(app, client):
    target = _target_user(RoleEnum.MANAGER, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    mock_db = MagicMock()
    mock_db.scalar.return_value = target
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.MANAGER)

    try:
        response = client.post(f"/api/v1/users/{target.id}/password-reset")

        assert response.status_code == 403
        assert response.json()["detail"] == "Gerente nao pode redefinir senha deste usuario"
        mock_db.commit.assert_not_called()
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
                "work_shift": "evening",
                "work_shift_scope": ["evening", "overnight"],
                "avatar_url": "https://cdn.exemplo.com/me.png",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["full_name"] == "Recepcao Piloto"
        assert body["job_title"] == "Front desk"
        assert body["work_shift"] == "evening"
        assert body["work_shift_scope"] == ["evening", "overnight"]
        assert body["avatar_url"] == "https://cdn.exemplo.com/me.png"
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_user_can_update_own_password_and_clear_tokens(app, client, monkeypatch):
    current_user = _current_user(RoleEnum.RECEPTIONIST)
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    audit_calls = []
    monkeypatch.setattr("app.routers.users.verify_password", lambda plain, hashed: plain == "Current123")
    monkeypatch.setattr("app.routers.users.hash_password", lambda value: f"hash:{value}")
    monkeypatch.setattr(
        "app.routers.users.log_audit_event",
        lambda *args, **kwargs: audit_calls.append(kwargs),
    )

    try:
        response = client.post(
            "/api/v1/users/me/password",
            json={"current_password": "Current123", "new_password": "NewSecret123"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Senha atualizada com sucesso. Entre novamente com a nova senha."
        assert current_user.hashed_password == "hash:NewSecret123"
        assert current_user.refresh_token_hash is None
        assert current_user.refresh_token_expires_at is None
        assert current_user.password_reset_token_hash is None
        assert current_user.password_reset_expires_at is None
        assert audit_calls[0]["details"] == {"method": "authenticated_change"}
        assert "NewSecret123" not in str(audit_calls[0]["details"])
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_user_cannot_update_own_password_with_invalid_current_password(app, client, monkeypatch):
    current_user = _current_user(RoleEnum.RECEPTIONIST)
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    monkeypatch.setattr("app.routers.users.verify_password", lambda plain, hashed: False)

    try:
        response = client.post(
            "/api/v1/users/me/password",
            json={"current_password": "WrongPass123", "new_password": "NewSecret123"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Senha atual invalida"
        assert current_user.hashed_password == "current_hash"
        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_user_can_upload_own_avatar_file(app, client):
    current_user = _current_user(RoleEnum.TRAINER)
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    try:
        response = client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\navatar-bytes", "image/png")},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["avatar_url"].startswith("data:image/png;base64,")
        assert current_user.avatar_url == body["avatar_url"]
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_owner_can_upload_team_user_avatar_file(app, client, monkeypatch):
    owner = _current_user(RoleEnum.OWNER)
    target = _target_user(RoleEnum.TRAINER, "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    mock_db = MagicMock()
    mock_db.scalar.return_value = target
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: owner
    audit_calls = []
    monkeypatch.setattr("app.routers.users.log_audit_event", lambda *args, **kwargs: audit_calls.append(kwargs))

    try:
        response = client.post(
            f"/api/v1/users/{target.id}/avatar",
            files={"file": ("trainer.webp", b"RIFFavatar-webp", "image/webp")},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["avatar_url"].startswith("data:image/webp;base64,")
        assert target.avatar_url == body["avatar_url"]
        assert audit_calls[0]["details"] == {
            "target_role": "trainer",
            "content_type": "image/webp",
            "size_bytes": len(b"RIFFavatar-webp"),
        }
        assert "RIFFavatar-webp" not in str(audit_calls[0]["details"])
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_manager_cannot_upload_owner_avatar(app, client):
    owner_target = _target_user(RoleEnum.OWNER, "cccccccc-cccc-cccc-cccc-cccccccccccc")
    mock_db = MagicMock()
    mock_db.scalar.return_value = owner_target
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.MANAGER)

    try:
        response = client.post(
            f"/api/v1/users/{owner_target.id}/avatar",
            files={"file": ("owner.png", b"\x89PNG\r\n\x1a\navatar-bytes", "image/png")},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Gerente nao pode editar avatar do owner"
        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()
