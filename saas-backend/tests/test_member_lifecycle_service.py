from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.models import MemberStatus, RiskLevel
from app.services.member_lifecycle_service import build_member_lifecycle_state


NOW = datetime(2026, 5, 7, tzinfo=timezone.utc)


def member(**overrides):
    data = {
        "status": MemberStatus.ACTIVE,
        "join_date": date(2026, 1, 1),
        "last_checkin_at": datetime(2026, 5, 5, tzinfo=timezone.utc),
        "onboarding_status": "completed",
        "retention_stage": None,
        "risk_level": RiskLevel.GREEN,
        "onboarding_score": 80,
        "risk_score": 10,
        "is_vip": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_onboarding_member_uses_onboarding_lane():
    payload = build_member_lifecycle_state(
        member(join_date=date(2026, 5, 1), onboarding_status="active"),
        now=NOW,
    )

    assert payload["lifecycle_stage"] == "onboarding"
    assert payload["recommended_queue"] == "onboarding"
    assert payload["recommended_owner_role"] == "receptionist"


def test_inactive_35_days_becomes_reactivation():
    payload = build_member_lifecycle_state(
        member(last_checkin_at=datetime(2026, 4, 1, tzinfo=timezone.utc)),
        now=NOW,
    )

    assert payload["lifecycle_stage"] == "reactivation"
    assert payload["operational_lane"] == "reactivation"
    assert payload["recommended_owner_role"] == "trainer"


def test_cold_base_is_not_daily_queue_default():
    payload = build_member_lifecycle_state(
        member(last_checkin_at=datetime(2026, 2, 1, tzinfo=timezone.utc)),
        now=NOW,
    )

    assert payload["lifecycle_stage"] == "cold_base"
    assert payload["is_daily_queue_default"] is False


def test_cancelled_member_is_closed():
    payload = build_member_lifecycle_state(
        member(status=MemberStatus.CANCELLED, risk_level=RiskLevel.RED),
        now=NOW,
    )

    assert payload["lifecycle_stage"] == "cancelled"
    assert payload["lifecycle_priority"] == 0


def test_yellow_risk_without_absence_still_needs_attention():
    payload = build_member_lifecycle_state(
        member(risk_level=RiskLevel.YELLOW, last_checkin_at=datetime(2026, 5, 7, tzinfo=timezone.utc)),
        now=NOW,
    )

    assert payload["lifecycle_stage"] == "attention"
