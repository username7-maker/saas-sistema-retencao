from types import SimpleNamespace

from app.schemas.dashboard import OperationalDashboard, RetentionDashboard


def _member_stub() -> SimpleNamespace:
    return SimpleNamespace(
        id="7b41f8a8-b2cc-4f07-a3d7-cc3b8737dd1f",
        full_name="Aluno Demo",
        email="aluno.demo@gmail.com",
        phone="11999999999",
        status="active",
        plan_name="Plano Base",
        monthly_fee="199.90",
        join_date="2026-01-10",
        preferred_shift="manha",
        nps_last_score=8,
        loyalty_months=4,
        risk_score=32,
        risk_level="green",
        last_checkin_at=None,
        created_at="2026-01-10T10:00:00Z",
        updated_at="2026-02-10T10:00:00Z",
    )


def test_operational_dashboard_schema_serializes_member_objects():
    payload = {
        "realtime_checkins": 5,
        "heatmap": [{"weekday": 1, "hour_bucket": 18, "total_checkins": 12}],
        "inactive_7d_total": 1,
        "inactive_7d_items": [_member_stub()],
    }
    parsed = OperationalDashboard.model_validate(payload)
    dumped = parsed.model_dump()
    assert dumped["inactive_7d_total"] == 1
    assert dumped["inactive_7d_items"][0]["full_name"] == "Aluno Demo"


def test_retention_dashboard_schema_serializes_member_objects():
    payload = {
        "red": {"total": 1, "items": [_member_stub()]},
        "yellow": {"total": 0, "items": []},
        "nps_trend": [{"month": "2026-02", "average_score": 8.4, "responses": 30}],
    }
    parsed = RetentionDashboard.model_validate(payload)
    dumped = parsed.model_dump()
    assert dumped["red"]["total"] == 1
    assert dumped["red"]["items"][0]["risk_level"] == "green"
