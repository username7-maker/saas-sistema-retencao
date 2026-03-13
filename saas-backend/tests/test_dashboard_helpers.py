"""Tests for dashboard_service private helpers."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from app.services.dashboard_service import _month_window, _subtract_months


class TestSubtractMonths:
    def test_same_year(self):
        assert _subtract_months(date(2026, 6, 1), 3) == date(2026, 3, 1)

    def test_cross_year(self):
        assert _subtract_months(date(2026, 2, 1), 3) == date(2025, 11, 1)

    def test_zero_months(self):
        assert _subtract_months(date(2026, 5, 1), 0) == date(2026, 5, 1)

    def test_twelve_months(self):
        assert _subtract_months(date(2026, 6, 1), 12) == date(2025, 6, 1)


class TestMonthWindow:
    def test_regular_month(self):
        start, end = _month_window("2026-03")
        assert start == datetime(2026, 3, 1, tzinfo=timezone.utc)
        assert end.month == 3
        assert end.day == 31

    def test_december(self):
        start, end = _month_window("2025-12")
        assert start == datetime(2025, 12, 1, tzinfo=timezone.utc)
        assert end.year == 2025
        assert end.month == 12
        assert end.day == 31

    def test_february(self):
        start, end = _month_window("2026-02")
        assert start.month == 2
        assert end.month == 2
        assert end.day == 28


class TestMonthLabels:
    def test_generates_correct_count(self):
        from app.services.dashboard_service import _month_labels
        labels = _month_labels(3)
        assert len(labels) == 3

    def test_labels_are_sorted(self):
        from app.services.dashboard_service import _month_labels
        labels = _month_labels(6)
        assert labels == sorted(labels)


class TestRevenueSeries:
    @patch("app.services.dashboard_service._monthly_member_kpis_rows")
    def test_uses_materialized(self, mock_kpis):
        mock_kpis.return_value = [
            {"month": "2026-01", "mrr": 10000.0, "active": 100, "cancelled": 5},
        ]
        db = MagicMock()
        from app.services.dashboard_service import _revenue_series
        result = _revenue_series(db, months=1)
        assert len(result) == 1
        assert result[0].value == 10000.0

    @patch("app.services.dashboard_service._monthly_member_kpis_rows", return_value=None)
    @patch("app.services.dashboard_service._month_labels", return_value=["2026-01"])
    @patch("app.services.dashboard_service._month_window")
    def test_fallback_to_sql(self, mock_window, mock_labels, mock_kpis):
        mock_window.return_value = (
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc),
        )
        db = MagicMock()
        db.scalar.return_value = 5000.0
        from app.services.dashboard_service import _revenue_series
        result = _revenue_series(db, months=1)
        assert len(result) == 1
        assert result[0].month == "2026-01"


class TestChurnSeries:
    @patch("app.services.dashboard_service._monthly_member_kpis_rows")
    def test_uses_materialized(self, mock_kpis):
        mock_kpis.return_value = [
            {"month": "2026-01", "mrr": 10000.0, "active": 100, "cancelled": 10},
        ]
        db = MagicMock()
        from app.services.dashboard_service import _churn_series
        result = _churn_series(db, months=1)
        assert len(result) == 1
        assert result[0].churn_rate == 10.0

    @patch("app.services.dashboard_service._monthly_member_kpis_rows", return_value=None)
    @patch("app.services.dashboard_service._month_labels", return_value=["2026-01"])
    @patch("app.services.dashboard_service._month_window")
    def test_fallback_to_sql(self, mock_window, mock_labels, mock_kpis):
        mock_window.return_value = (
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc),
        )
        db = MagicMock()
        db.scalar.side_effect = [5, 100]  # cancelled, active_base
        from app.services.dashboard_service import _churn_series
        result = _churn_series(db, months=1)
        assert len(result) == 1
        assert result[0].churn_rate == 5.0


class TestMembersJoinedCumulative:
    @patch("app.services.dashboard_service._month_window")
    def test_empty_labels(self, mock_window):
        from app.services.dashboard_service import _members_joined_cumulative_by_month
        db = MagicMock()
        result = _members_joined_cumulative_by_month(db, [])
        assert result == {}
