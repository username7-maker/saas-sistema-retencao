"""Unit tests for member service functions."""
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests.conftest import make_mock_db, GYM_ID, USER_ID, MEMBER_ID


class TestListMembers:
    def test_returns_paginated_result(self, mock_member):
        from app.services.member_service import list_members

        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_member]
        db.scalars.return_value = mock_scalars
        db.scalar.return_value = 1  # total count

        result = list_members(db, page=1, page_size=20)
        assert result.total == 1
        assert len(result.items) == 1

    def test_empty_returns_zero(self):
        from app.services.member_service import list_members

        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars
        db.scalar.return_value = 0

        result = list_members(db, page=1, page_size=20)
        assert result.total == 0
        assert result.items == []


class TestGetMemberOr404:
    def test_raises_404_when_not_found(self):
        from fastapi import HTTPException
        from app.services.member_service import get_member_or_404

        db = make_mock_db(scalar_returns=None)
        with pytest.raises(HTTPException) as exc_info:
            get_member_or_404(db, uuid.uuid4())
        assert exc_info.value.status_code == 404

    def test_returns_member_when_found(self, mock_member):
        from app.services.member_service import get_member_or_404

        db = make_mock_db(scalar_returns=mock_member)
        result = get_member_or_404(db, MEMBER_ID)
        assert result.id == MEMBER_ID
