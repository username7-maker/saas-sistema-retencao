"""Unit tests for auth service functions."""
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.auth_service import issue_tokens
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_refresh_token,
)
from tests.conftest import make_mock_db, GYM_ID, USER_ID


class TestHashAndVerify:
    def test_hash_password_returns_bcrypt(self):
        hashed = hash_password("SenhaForte123!")
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        hashed = hash_password("SenhaForte123!")
        assert verify_password("SenhaForte123!", hashed) is True

    def test_verify_password_wrong(self):
        hashed = hash_password("SenhaForte123!")
        assert verify_password("ErradaXXX", hashed) is False

    def test_refresh_token_hash_uses_full_token_digest(self):
        common_prefix = "x" * 72
        first_token = f"{common_prefix}-first"
        second_token = f"{common_prefix}-second"

        stored_hash = hash_refresh_token(first_token)

        assert stored_hash.startswith("sha256$")
        assert verify_refresh_token(first_token, stored_hash) is True
        assert verify_refresh_token(second_token, stored_hash) is False

    def test_refresh_token_rotation_rejects_previous_token(self):
        first_token = create_refresh_token(USER_ID, GYM_ID)
        rotated_token = create_refresh_token(USER_ID, GYM_ID)
        rotated_hash = hash_refresh_token(rotated_token)

        assert first_token != rotated_token
        assert verify_refresh_token(rotated_token, rotated_hash) is True
        assert verify_refresh_token(first_token, rotated_hash) is False


class TestCreateAccessToken:
    def test_creates_token_with_sub(self):
        token = create_access_token({"sub": str(USER_ID), "gym_id": str(GYM_ID)})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_is_decodeable(self):
        from app.core.security import decode_token
        payload = {"sub": str(USER_ID), "gym_id": str(GYM_ID)}
        token = create_access_token(payload)
        decoded = decode_token(token)
        assert decoded["sub"] == str(USER_ID)
        assert decoded["gym_id"] == str(GYM_ID)


class TestIssueTokens:
    def test_issue_tokens_returns_token_pair(self):
        from app.models import RoleEnum
        user = SimpleNamespace(
            id=USER_ID,
            gym_id=GYM_ID,
            role=RoleEnum.OWNER,
            email="owner@test.com",
        )
        db = make_mock_db()
        result = issue_tokens(db, user)
        assert hasattr(result, "access_token")
        assert hasattr(result, "refresh_token")
        assert result.access_token
        assert result.refresh_token
