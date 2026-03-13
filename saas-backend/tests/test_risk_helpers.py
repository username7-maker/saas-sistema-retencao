"""Tests for risk.py helper functions and calculate_risk_score."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models import MemberStatus, RiskLevel
from app.services.risk import _inactivity_points


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
        assert _inactivity_points(21) == 60

    def test_thirty_days(self):
        assert _inactivity_points(30) == 60


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
