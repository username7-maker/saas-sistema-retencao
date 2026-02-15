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


def test_automation_14d_generates_in_app_notification(monkeypatch):
    member = SimpleNamespace(
        id="member-14d",
        full_name="Aluno Teste",
        assigned_user_id=None,
        email=None,
        risk_level=RiskLevel.YELLOW,
        risk_score=45,
    )

    monkeypatch.setattr(risk_service, "_can_trigger_stage", lambda *_: True)
    monkeypatch.setattr(risk_service, "_record_stage", lambda *_: None)
    monkeypatch.setattr(risk_service, "_ensure_call_task", lambda *_: None)
    monkeypatch.setattr(
        risk_service,
        "create_notification",
        lambda *_args, **_kwargs: SimpleNamespace(id="notif-1"),
    )

    actions = risk_service._run_inactivity_automations(
        db=DummyDB(),
        member=member,
        days_without_checkin=14,
        level=RiskLevel.YELLOW,
    )

    in_app_actions = [item for item in actions if item["type"] == "in_app_notification"]
    assert in_app_actions
    assert in_app_actions[0]["notification_id"] == "notif-1"
    assert member.risk_level == RiskLevel.RED
    assert member.risk_score >= 70
