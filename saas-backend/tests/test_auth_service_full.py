"""Comprehensive tests for auth_service covering all major paths."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models import RoleEnum
from app.schemas import UserLogin, UserRegister
from app.services.auth_service import (
    _normalize_gym_slug,
    authenticate_user,
    create_gym,
    create_user,
    issue_tokens,
    logout,
    refresh_access_token,
    request_password_reset,
    reset_password,
)

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


# ---------------------------------------------------------------------------
# _normalize_gym_slug
# ---------------------------------------------------------------------------

class TestNormalizeGymSlug:
    def test_simple(self):
        assert _normalize_gym_slug("academia-teste") == "academia-teste"

    def test_strips_special_chars(self):
        # "Academia Teste!" -> lowercase -> regex replaces non-alnum to "-" -> strip("-")
        assert _normalize_gym_slug("Academia Teste!") == "academia-teste"

    def test_collapses_dashes(self):
        result = _normalize_gym_slug("a---b")
        assert "--" not in result

    def test_short_slug_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            _normalize_gym_slug("ab")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# create_gym
# ---------------------------------------------------------------------------

class TestCreateGym:
    def test_creates_gym(self):
        db = MagicMock()
        db.scalar.return_value = None  # No existing gym
        result = create_gym(db, name="Minha Gym", slug="minha-gym")
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_can_skip_commit(self):
        db = MagicMock()
        db.scalar.return_value = None
        db.refresh = MagicMock()

        create_gym(db, name="Minha Gym", slug="minha-gym", commit=False)

        db.commit.assert_not_called()
        db.flush.assert_called_once()

    def test_duplicate_slug_raises(self):
        db = MagicMock()
        db.scalar.return_value = SimpleNamespace(slug="minha-gym")  # Existing gym
        with pytest.raises(HTTPException) as exc_info:
            create_gym(db, name="Minha Gym", slug="minha-gym")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_creates_user(self):
        db = MagicMock()
        db.scalar.return_value = None  # No existing user
        payload = UserRegister(full_name="Test", email="t@t.com", password="Secret123!", role=RoleEnum.MANAGER)
        create_user(db, payload, gym_id=GYM_ID)
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_can_skip_commit(self):
        db = MagicMock()
        db.scalar.return_value = None
        db.refresh = MagicMock()
        payload = UserRegister(full_name="Test", email="t@t.com", password="Secret123!", role=RoleEnum.MANAGER)

        create_user(db, payload, gym_id=GYM_ID, commit=False)

        db.commit.assert_not_called()
        db.flush.assert_called_once()

    def test_duplicate_email_raises(self):
        db = MagicMock()
        db.scalar.return_value = SimpleNamespace(email="t@t.com")  # Existing
        payload = UserRegister(full_name="Test", email="t@t.com", password="Secret123!", role=RoleEnum.MANAGER)
        with pytest.raises(HTTPException) as exc_info:
            create_user(db, payload, gym_id=GYM_ID)
        assert exc_info.value.status_code == 400

    def test_force_role_overrides(self):
        db = MagicMock()
        db.scalar.return_value = None
        payload = UserRegister(full_name="Test", email="t@t.com", password="Secret123!", role=RoleEnum.MANAGER)
        create_user(db, payload, gym_id=GYM_ID, force_role=RoleEnum.OWNER)
        added_user = db.add.call_args[0][0]
        assert added_user.role == RoleEnum.OWNER

    def test_accepts_trainer_role(self):
        db = MagicMock()
        db.scalar.return_value = None
        payload = UserRegister(full_name="Trainer Test", email="trainer@t.com", password="Secret123!", role=RoleEnum.TRAINER)
        create_user(db, payload, gym_id=GYM_ID)
        added_user = db.add.call_args[0][0]
        assert added_user.role == RoleEnum.TRAINER


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------

class TestAuthenticateUser:
    def test_invalid_gym_raises(self):
        db = MagicMock()
        db.scalar.return_value = None  # No gym
        payload = UserLogin(email="t@t.com", password="password123", gym_slug="missing-gym")
        with pytest.raises(HTTPException) as exc_info:
            authenticate_user(db, payload)
        assert exc_info.value.status_code == 401

    def test_invalid_password_raises(self):
        gym = SimpleNamespace(id=GYM_ID, slug="my-gym", is_active=True)
        user = SimpleNamespace(
            id=USER_ID, gym_id=GYM_ID, email="t@t.com",
            hashed_password="$2b$12$fakehash", is_active=True, deleted_at=None,
        )
        db = MagicMock()
        db.scalar.side_effect = [gym, user]
        payload = UserLogin(email="t@t.com", password="wrong12345", gym_slug="my-gym")
        with patch("app.services.auth_service.verify_password", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                authenticate_user(db, payload)
            assert exc_info.value.status_code == 401

    def test_inactive_user_raises_403(self):
        gym = SimpleNamespace(id=GYM_ID, slug="my-gym", is_active=True)
        user = SimpleNamespace(
            id=USER_ID, gym_id=GYM_ID, email="t@t.com",
            hashed_password="hash", is_active=False, deleted_at=None,
        )
        db = MagicMock()
        db.scalar.side_effect = [gym, user]
        payload = UserLogin(email="t@t.com", password="correct123", gym_slug="my-gym")
        with patch("app.services.auth_service.verify_password", return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                authenticate_user(db, payload)
            assert exc_info.value.status_code == 403

    def test_success(self):
        gym = SimpleNamespace(id=GYM_ID, slug="my-gym", is_active=True)
        user = SimpleNamespace(
            id=USER_ID, gym_id=GYM_ID, email="t@t.com",
            hashed_password="hash", is_active=True, deleted_at=None,
            last_login_at=None,
        )
        db = MagicMock()
        db.scalar.side_effect = [gym, user]
        payload = UserLogin(email="t@t.com", password="correct123", gym_slug="my-gym")
        with patch("app.services.auth_service.verify_password", return_value=True):
            result = authenticate_user(db, payload)
        assert result.id == USER_ID
        db.commit.assert_called_once()

    def test_success_can_skip_commit(self):
        gym = SimpleNamespace(id=GYM_ID, slug="my-gym", is_active=True)
        user = SimpleNamespace(
            id=USER_ID, gym_id=GYM_ID, email="t@t.com",
            hashed_password="hash", is_active=True, deleted_at=None,
            last_login_at=None,
        )
        db = MagicMock()
        db.scalar.side_effect = [gym, user]
        payload = UserLogin(email="t@t.com", password="correct123", gym_slug="my-gym")
        with patch("app.services.auth_service.verify_password", return_value=True):
            result = authenticate_user(db, payload, commit=False)
        assert result.id == USER_ID
        db.commit.assert_not_called()
        db.flush.assert_called_once()


# ---------------------------------------------------------------------------
# issue_tokens
# ---------------------------------------------------------------------------

class TestIssueTokens:
    def test_returns_token_pair(self):
        user = SimpleNamespace(
            id=USER_ID, gym_id=GYM_ID, role=RoleEnum.OWNER,
            refresh_token_hash=None, refresh_token_expires_at=None,
        )
        db = MagicMock()
        result = issue_tokens(db, user)
        assert result.access_token
        assert result.refresh_token
        assert user.refresh_token_hash is not None

    def test_can_skip_commit(self):
        user = SimpleNamespace(
            id=USER_ID, gym_id=GYM_ID, role=RoleEnum.OWNER,
            refresh_token_hash=None, refresh_token_expires_at=None,
        )
        db = MagicMock()

        issue_tokens(db, user, commit=False)

        db.commit.assert_not_called()
        db.flush.assert_called_once()


# ---------------------------------------------------------------------------
# refresh_access_token
# ---------------------------------------------------------------------------

class TestRefreshAccessToken:
    def test_invalid_token_raises(self):
        db = MagicMock()
        with patch("app.services.auth_service.decode_token", side_effect=KeyError("sub")):
            with pytest.raises(HTTPException):
                refresh_access_token(db, "bad-token")

    def test_wrong_type_raises(self):
        db = MagicMock()
        with patch("app.services.auth_service.decode_token", return_value={"type": "access", "sub": str(USER_ID), "gym_id": str(GYM_ID)}):
            with pytest.raises(HTTPException):
                refresh_access_token(db, "token")

    def test_expired_raises(self):
        user = SimpleNamespace(
            id=USER_ID, gym_id=GYM_ID, deleted_at=None,
            is_active=True,
            refresh_token_hash="hash",
            refresh_token_expires_at=datetime.now(tz=timezone.utc) - timedelta(days=1),
        )
        db = MagicMock()
        db.scalar.return_value = user
        with patch("app.services.auth_service.decode_token", return_value={"type": "refresh", "sub": str(USER_ID), "gym_id": str(GYM_ID)}):
            with patch("app.services.auth_service.verify_refresh_token", return_value=True):
                with pytest.raises(HTTPException):
                    refresh_access_token(db, "token")

    def test_inactive_user_raises(self):
        user = SimpleNamespace(
            id=USER_ID,
            gym_id=GYM_ID,
            deleted_at=None,
            is_active=False,
            refresh_token_hash="hash",
            refresh_token_expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
        )
        db = MagicMock()
        db.scalar.return_value = user
        with patch("app.services.auth_service.decode_token", return_value={"type": "refresh", "sub": str(USER_ID), "gym_id": str(GYM_ID)}):
            with patch("app.services.auth_service.verify_refresh_token", return_value=True):
                with pytest.raises(HTTPException) as exc_info:
                    refresh_access_token(db, "token")
        assert exc_info.value.status_code == 401

    def test_deleted_user_raises(self):
        user = SimpleNamespace(
            id=USER_ID,
            gym_id=GYM_ID,
            deleted_at=datetime.now(tz=timezone.utc),
            is_active=True,
            refresh_token_hash="hash",
            refresh_token_expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
        )
        db = MagicMock()
        db.scalar.return_value = user
        with patch("app.services.auth_service.decode_token", return_value={"type": "refresh", "sub": str(USER_ID), "gym_id": str(GYM_ID)}):
            with patch("app.services.auth_service.verify_refresh_token", return_value=True):
                with pytest.raises(HTTPException) as exc_info:
                    refresh_access_token(db, "token")
        assert exc_info.value.status_code == 401

    def test_tenant_mismatch_raises(self):
        user = SimpleNamespace(
            id=USER_ID,
            gym_id=uuid.uuid4(),
            deleted_at=None,
            is_active=True,
            refresh_token_hash="hash",
            refresh_token_expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
        )
        db = MagicMock()
        db.scalar.return_value = user
        with patch("app.services.auth_service.decode_token", return_value={"type": "refresh", "sub": str(USER_ID), "gym_id": str(GYM_ID)}):
            with patch("app.services.auth_service.verify_refresh_token", return_value=True):
                with pytest.raises(HTTPException) as exc_info:
                    refresh_access_token(db, "token")
        assert exc_info.value.status_code == 401

    def test_valid_active_user_returns_new_tokens(self):
        user = SimpleNamespace(
            id=USER_ID,
            gym_id=GYM_ID,
            deleted_at=None,
            is_active=True,
            refresh_token_hash="hash",
            refresh_token_expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
        )
        tokens = SimpleNamespace(access_token="new-access", refresh_token="new-refresh")
        db = MagicMock()
        db.scalar.return_value = user
        with patch("app.services.auth_service.decode_token", return_value={"type": "refresh", "sub": str(USER_ID), "gym_id": str(GYM_ID)}):
            with patch("app.services.auth_service.verify_refresh_token", return_value=True):
                with patch("app.services.auth_service.issue_tokens", return_value=tokens) as mock_issue_tokens:
                    result = refresh_access_token(db, "token")
        assert result is tokens
        mock_issue_tokens.assert_called_once_with(db, user, commit=True)

    def test_can_skip_commit(self):
        user = SimpleNamespace(
            id=USER_ID,
            gym_id=GYM_ID,
            deleted_at=None,
            is_active=True,
            refresh_token_hash="hash",
            refresh_token_expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
        )
        tokens = SimpleNamespace(access_token="new-access", refresh_token="new-refresh")
        db = MagicMock()
        db.scalar.return_value = user
        with patch("app.services.auth_service.decode_token", return_value={"type": "refresh", "sub": str(USER_ID), "gym_id": str(GYM_ID)}):
            with patch("app.services.auth_service.verify_refresh_token", return_value=True):
                with patch("app.services.auth_service.issue_tokens", return_value=tokens) as mock_issue_tokens:
                    result = refresh_access_token(db, "token", commit=False)
        assert result is tokens
        mock_issue_tokens.assert_called_once_with(db, user, commit=False)


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_clears_refresh_token(self):
        user = SimpleNamespace(refresh_token_hash="hash", refresh_token_expires_at=datetime.now(tz=timezone.utc))
        db = MagicMock()
        logout(db, user)
        assert user.refresh_token_hash is None
        assert user.refresh_token_expires_at is None
        db.commit.assert_called_once()

    def test_can_skip_commit(self):
        user = SimpleNamespace(refresh_token_hash="hash", refresh_token_expires_at=datetime.now(tz=timezone.utc))
        db = MagicMock()

        logout(db, user, commit=False)

        assert user.refresh_token_hash is None
        assert user.refresh_token_expires_at is None
        db.commit.assert_not_called()
        db.flush.assert_called_once()


# ---------------------------------------------------------------------------
# request_password_reset
# ---------------------------------------------------------------------------

class TestRequestPasswordReset:
    def test_no_gym_does_nothing(self):
        db = MagicMock()
        db.scalar.return_value = None
        request_password_reset(db, email="t@t.com", gym_slug="fake-gym")

    def test_no_user_does_nothing(self):
        gym = SimpleNamespace(id=GYM_ID, slug="my-gym", is_active=True)
        db = MagicMock()
        db.scalar.side_effect = [gym, None]
        request_password_reset(db, email="missing@t.com", gym_slug="my-gym")

    @patch("app.services.auth_service.send_email")
    def test_sends_email(self, mock_send):
        gym = SimpleNamespace(id=GYM_ID, slug="my-gym", is_active=True)
        user = SimpleNamespace(
            id=USER_ID, full_name="Test", email="t@t.com",
            password_reset_token_hash=None, password_reset_expires_at=None,
        )
        db = MagicMock()
        db.scalar.side_effect = [gym, user]
        request_password_reset(db, email="t@t.com", gym_slug="my-gym")
        mock_send.assert_called_once()
        assert user.password_reset_token_hash is not None


# ---------------------------------------------------------------------------
# reset_password
# ---------------------------------------------------------------------------

class TestResetPassword:
    def test_invalid_token_raises(self):
        db = MagicMock()
        db.scalar.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            reset_password(db, token="invalid", new_password="NewPass123!")
        assert exc_info.value.status_code == 400

    @patch("app.services.auth_service.hash_password", return_value="new_hash")
    def test_success(self, mock_hash):
        user = SimpleNamespace(
            hashed_password="old_hash",
            password_reset_token_hash="hash",
            password_reset_expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1),
            refresh_token_hash="rt", refresh_token_expires_at=datetime.now(tz=timezone.utc),
        )
        db = MagicMock()
        db.scalar.return_value = user
        reset_password(db, token="valid-token", new_password="NewPass123!")
        assert user.hashed_password == "new_hash"
        assert user.password_reset_token_hash is None
        assert user.refresh_token_hash is None
        db.commit.assert_called_once()
