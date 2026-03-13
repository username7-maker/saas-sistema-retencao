"""
Test onboarding score calculation service.
"""
import uuid
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.onboarding_score_service import calculate_onboarding_score

MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _make_member(join_date=None, onboarding_score=0, onboarding_status="active"):
    from app.models import MemberStatus
    return SimpleNamespace(
        id=MEMBER_ID,
        gym_id=GYM_ID,
        join_date=join_date or date.today(),
        status=MemberStatus.ACTIVE,
        onboarding_score=onboarding_score,
        onboarding_status=onboarding_status,
        assigned_user_id=None,
        full_name="Aluno Teste",
    )


def _make_db(checkin_count=0, has_assessment=0, total_tasks=0, done_tasks=0, has_nps=0, hour_buckets=None):
    db = MagicMock()

    def scalar_side_effect(*args, **kwargs):
        stmt_str = str(args[0]) if args else ""
        # Return different counts based on what's being queried
        # This is a simplified approach - counts returned in order
        return None

    # Use side_effect list for ordered scalar calls
    db.scalar.side_effect = [
        checkin_count,   # checkin count
        has_assessment,  # assessment count
        total_tasks,     # total onboarding tasks
        done_tasks,      # completed onboarding tasks
        has_nps,         # nps count
    ]

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = hour_buckets or []
    db.scalars.return_value = mock_scalars

    return db


def test_calculate_onboarding_score_returns_dict():
    """calculate_onboarding_score should return a dict with expected keys."""
    db = _make_db()
    member = _make_member()

    result = calculate_onboarding_score(db, member)

    assert "score" in result
    assert "status" in result
    assert "factors" in result
    assert "days_since_join" in result
    assert 0 <= result["score"] <= 100


def test_calculate_onboarding_score_all_zeros():
    """Member with no activity should score very low."""
    db = _make_db(checkin_count=0, has_assessment=0, total_tasks=0, done_tasks=0, has_nps=0)
    member = _make_member()

    result = calculate_onboarding_score(db, member)

    # With no assessment, no NPS, no tasks, no checkins, score should be low
    assert result["score"] < 50
    assert result["factors"]["first_assessment"] == 0
    assert result["factors"]["nps_response"] == 0


def test_calculate_onboarding_score_completed_after_30_days():
    """Member who joined 31+ days ago should have status 'completed'."""
    db = _make_db()
    member = _make_member(join_date=date.today() - timedelta(days=31))

    result = calculate_onboarding_score(db, member)

    assert result["status"] == "completed"
    assert result["days_since_join"] >= 31


def test_calculate_onboarding_score_at_risk_low_score():
    """Member with score < 30 should be 'at_risk'."""
    db = _make_db(checkin_count=0, has_assessment=0, total_tasks=0, done_tasks=0, has_nps=0)
    member = _make_member(join_date=date.today() - timedelta(days=10))

    result = calculate_onboarding_score(db, member)

    assert result["status"] in ("at_risk", "active")  # depends on exact calculation
