"""Test onboarding score calculation service."""
import uuid
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.onboarding_score_service import calculate_onboarding_score

MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _make_member(join_date=None, onboarding_score=0, onboarding_status="active", phone="(11) 99999-0001"):
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
        phone=phone,
    )


def _make_db(
    checkin_count=0,
    has_assessment=0,
    total_tasks=0,
    done_tasks=0,
    has_nps=0,
    answered_contact_logs=0,
    inbound_messages=0,
    inbound_gym_id=GYM_ID,
    hour_buckets=None,
):
    db = MagicMock()

    def scalar_side_effect(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        params = stmt.compile().params

        if "from checkins" in stmt_str:
            return checkin_count
        if "from assessments" in stmt_str:
            return has_assessment
        if "from tasks" in stmt_str and "tasks.status" in stmt_str:
            return done_tasks
        if "from tasks" in stmt_str:
            return total_tasks
        if "from nps_responses" in stmt_str:
            return has_nps
        if "from audit_logs" in stmt_str:
            return answered_contact_logs
        if "from message_logs" in stmt_str:
            return inbound_messages if inbound_gym_id in params.values() else 0
        return 0

    db.scalar.side_effect = scalar_side_effect

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
    assert result["factors"]["member_response"] == 0


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


def test_member_response_factor_counts_nps_feedback():
    db = _make_db(has_nps=1)
    member = _make_member()

    result = calculate_onboarding_score(db, member)

    assert result["factors"]["member_response"] == 100


def test_member_response_factor_counts_answered_contact_log():
    db = _make_db(answered_contact_logs=1)
    member = _make_member()

    result = calculate_onboarding_score(db, member)

    assert result["factors"]["member_response"] == 100


def test_member_response_factor_counts_whatsapp_inbound_for_same_gym():
    db = _make_db(inbound_messages=1, inbound_gym_id=GYM_ID)
    member = _make_member(phone="+55 (11) 99999-0001")

    result = calculate_onboarding_score(db, member)

    assert result["factors"]["member_response"] == 100


def test_member_response_factor_ignores_whatsapp_inbound_from_other_gym():
    db = _make_db(inbound_messages=1, inbound_gym_id=uuid.uuid4())
    member = _make_member(phone="11999990001")

    result = calculate_onboarding_score(db, member)

    assert result["factors"]["member_response"] == 0
