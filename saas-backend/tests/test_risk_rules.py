from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from app.models import RiskLevel
from app.services import risk as risk_service


class DummyDB:
    def __init__(self) -> None:
        self.values = []

    def scalar(self, _query):
        if not self.values:
            return 0
        return self.values.pop(0)


def _make_member(
    *,
    last_checkin_days_ago: int,
    nps_last_score: int = 5,
    loyalty_months: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        id="member-1",
        join_date=date.today() - timedelta(days=60),
        last_checkin_at=datetime.now(tz=timezone.utc) - timedelta(days=last_checkin_days_ago),
        nps_last_score=nps_last_score,
        loyalty_months=loyalty_months,
    )


def test_risk_score_red_for_high_inactivity_and_low_nps(monkeypatch):
    db = DummyDB()
    member = _make_member(last_checkin_days_ago=21, nps_last_score=3, loyalty_months=0)

    monkeypatch.setattr(risk_service, "_frequency_drop_points", lambda *_: (20, 70.0))
    monkeypatch.setattr(risk_service, "_shift_change_points", lambda *_: (10, 4))

    result = risk_service.calculate_risk_score(db, member)

    assert result.score >= 70
    assert result.level == RiskLevel.RED


def test_risk_score_can_drop_with_loyalty_factor(monkeypatch):
    db = DummyDB()
    member = _make_member(last_checkin_days_ago=7, nps_last_score=8, loyalty_months=30)

    monkeypatch.setattr(risk_service, "_frequency_drop_points", lambda *_: (6, 25.0))
    monkeypatch.setattr(risk_service, "_shift_change_points", lambda *_: (5, 2))

    result = risk_service.calculate_risk_score(db, member)

    assert result.score < 40
    assert result.level == RiskLevel.GREEN
