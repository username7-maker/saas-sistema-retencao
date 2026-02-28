"""Unit tests for auth service functions."""
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.auth_service import issue_tokens
from app.core.security import verify_password, hash_password, create_access_token
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
