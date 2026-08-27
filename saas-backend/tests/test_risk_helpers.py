"""Tests for risk.py helper functions and calculate_risk_score."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models import MemberStatus, RiskLevel
from app.services.risk import RiskResult, _inactivity_points, _retention_alert_result, _should_open_retention_alert


class TestInactivityPoints:
    def test_zero_days(self):
        assert _inactivity_points(0) == 0

    def test_two_days(self):
        assert _inactivity_points(2) == 0

    def test_three_days(self):
        assert _inactivity_points(3) == 10

    def test_seven_days(self):
        assert _inactivity_points(7) == 20

    def test_ten_days(self):
        assert _inactivity_points(10) == 30

    def test_fourteen_days(self):
        assert _inactivity_points(14) == 45

    def test_twenty_one_days(self):
        assert _inactivity_points(21) == 70

    def test_thirty_days(self):
        assert _inactivity_points(30) == 80

    def test_forty_five_days(self):
        assert _inactivity_points(45) == 90


class TestRetentionAlertEligibility:
    def test_opens_operational_alert_from_seven_days_without_changing_risk_model(self):
        result = RiskResult(score=20, level=RiskLevel.GREEN, reasons={}, days_without_checkin=7)

        assert _should_open_retention_alert(result) is True
        alert_result = _retention_alert_result(result)
        assert alert_result.score == 40
        assert alert_result.level == RiskLevel.YELLOW
        assert alert_result.reasons["operational_inactivity_alert"] is True

    def test_does_not_open_operational_alert_before_seven_days(self):
        result = RiskResult(score=10, level=RiskLevel.GREEN, reasons={}, days_without_checkin=6)

        assert _should_open_retention_alert(result) is False
        assert _retention_alert_result(result) is result

    def test_all_operational_retention_windows_are_eligible(self):
        for days in (7, 13, 14, 29, 30, 44, 45, 59, 60):
            result = RiskResult(score=20, level=RiskLevel.GREEN, reasons={}, days_without_checkin=days)
            assert _should_open_retention_alert(result) is True


class TestPrefetchOpenRiskAlerts:
    def test_deduplicates(self):
        member_id = uuid.uuid4()
        alert1 = SimpleNamespace(member_id=member_id, resolved=False, resolved_at=None)
        alert2 = SimpleNamespace(member_id=member_id, resolved=False, resolved_at=None)
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [alert1, alert2]
        db.scalars.return_value = mock_scalars

        from app.services.risk import _prefetch_open_risk_alerts
        result = _prefetch_open_risk_alerts(db, deduplicate=True)
        assert len(result) == 1
        assert alert2.resolved is True  # duplicate was resolved

    def test_no_deduplicate(self):
        member_id = uuid.uuid4()
        alert1 = SimpleNamespace(member_id=member_id, resolved=False, resolved_at=None)
        alert2 = SimpleNamespace(member_id=member_id, resolved=False, resolved_at=None)
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [alert1, alert2]
        db.scalars.return_value = mock_scalars

        from app.services.risk import _prefetch_open_risk_alerts
        result = _prefetch_open_risk_alerts(db, deduplicate=False)
        assert len(result) == 1
        assert alert2.resolved is False  # not resolved without deduplicate

    def test_skips_none_member_id(self):
        alert = SimpleNamespace(member_id=None, resolved=False)
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [alert]
        db.scalars.return_value = mock_scalars

        from app.services.risk import _prefetch_open_risk_alerts
        result = _prefetch_open_risk_alerts(db)
        assert len(result) == 0


class TestPrefetchOpenCallTasks:
    def test_deduplicates_tasks(self):
        member_id = uuid.uuid4()
        task1 = SimpleNamespace(member_id=member_id, deleted_at=None)
        task2 = SimpleNamespace(member_id=member_id, deleted_at=None)
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [task1, task2]
        db.scalars.return_value = mock_scalars

        from app.services.risk import _prefetch_open_call_tasks
        result = _prefetch_open_call_tasks(db, deduplicate=True)
        assert member_id in result
        assert task2.deleted_at is not None

    def test_skips_none_member_id(self):
        task = SimpleNamespace(member_id=None, deleted_at=None)
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [task]
        db.scalars.return_value = mock_scalars

        from app.services.risk import _prefetch_open_call_tasks
        result = _prefetch_open_call_tasks(db)
        assert len(result) == 0
