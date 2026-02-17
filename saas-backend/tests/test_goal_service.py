from app.services import goal_service


def test_progress_pct_gte():
    pct = goal_service._progress_pct("gte", 100.0, 80.0)
    assert pct == 80.0


def test_progress_pct_lte():
    pct = goal_service._progress_pct("lte", 5.0, 10.0)
    assert pct == 50.0


def test_status_achieved_gte():
    status, message = goal_service._status(
        comparator="gte",
        target_value=100.0,
        current_value=120.0,
        alert_threshold_pct=80,
        progress_pct=120.0,
    )
    assert status == "achieved"
    assert "Meta atingida" in message


def test_status_at_risk_lte():
    status, message = goal_service._status(
        comparator="lte",
        target_value=5.0,
        current_value=12.0,
        alert_threshold_pct=80,
        progress_pct=41.0,
    )
    assert status == "at_risk"
    assert "risco" in message
