"""
Test that get_member_profile_360 handles partial sub-query failures gracefully.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.assessment_service import get_member_profile_360

MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _make_mock_member():
    from app.models import MemberStatus, RiskLevel
    m = MagicMock()
    m.id = MEMBER_ID
    m.deleted_at = None
    m.full_name = "Aluno Teste"
    m.status = MemberStatus.ACTIVE
    return m


def test_profile_360_returns_partial_on_sub_query_failure():
    """If one sub-query raises, get_member_profile_360 still returns a partial result."""
    member = _make_mock_member()

    db = MagicMock()
    # First scalar call returns member, subsequent calls raise
    call_count = {"n": 0}

    def scalar_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return member  # get_member_or_404
        raise RuntimeError("simulated DB failure")

    db.scalar.side_effect = scalar_side_effect

    mock_scalars = MagicMock()
    mock_scalars.all.side_effect = RuntimeError("simulated scalars failure")
    db.scalars.return_value = mock_scalars

    result = get_member_profile_360(db, MEMBER_ID)

    # Should not raise; partial fields should be None/[]
    assert result["member"] is member
    assert result["latest_assessment"] is None
    assert result["constraints"] is None
    assert result["goals"] == []
    assert result["active_training_plan"] is None


def test_profile_360_raises_404_for_missing_member():
    """get_member_profile_360 must raise 404 if member not found."""
    db = MagicMock()
    db.scalar.return_value = None  # member not found

    with pytest.raises(HTTPException) as exc:
        get_member_profile_360(db, MEMBER_ID)

    assert exc.value.status_code == 404
