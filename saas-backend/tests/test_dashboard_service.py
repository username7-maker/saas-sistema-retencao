"""Tests for dashboard_service covering all dashboard endpoints."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models import MemberStatus, RiskLevel


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _db_with_counts(total=100, active=80, mrr=Decimal("9990"), nps=8.5, green=60, yellow=15, red=5):
    """Create a mock DB that returns values for executive dashboard queries."""
    db = MagicMock()
    db.scalar.side_effect = [total, active, mrr, nps, green, yellow, red]
    return db


class TestGetExecutiveDashboard:
    @patch("app.services.dashboard_service.dashboard_cache")
    @patch("app.services.dashboard_service._churn_series", return_value=[])
    def test_returns_dashboard(self, mock_churn, mock_cache):
        mock_cache.get.return_value = None
        db = _db_with_counts()
        from app.services.dashboard_service import get_executive_dashboard
        result = get_executive_dashboard(db)
        assert result.total_members == 100
        assert result.active_members == 80
        assert result.mrr == 9990.0
        assert result.nps_avg == 8.5
        assert result.risk_distribution["green"] == 60
        mock_cache.set.assert_called_once()

    @patch("app.services.dashboard_service.dashboard_cache")
    def test_returns_cached(self, mock_cache):
        cached_data = SimpleNamespace(total_members=50, active_members=40)
        mock_cache.get.return_value = cached_data
        db = MagicMock()
        from app.services.dashboard_service import get_executive_dashboard
        result = get_executive_dashboard(db)
        assert result.total_members == 50
        db.scalar.assert_not_called()


class TestGetMrrDashboard:
    @patch("app.services.dashboard_service.dashboard_cache")
    @patch("app.services.dashboard_service._revenue_series", return_value=[])
    def test_returns_series(self, mock_rev, mock_cache):
        mock_cache.get.return_value = None
        db = MagicMock()
        from app.services.dashboard_service import get_mrr_dashboard
        result = get_mrr_dashboard(db, months=6)
        assert result == []
        mock_cache.set.assert_called_once()


class TestGetChurnDashboard:
    @patch("app.services.dashboard_service.dashboard_cache")
    @patch("app.services.dashboard_service._churn_series", return_value=[])
    def test_returns_series(self, mock_churn, mock_cache):
        mock_cache.get.return_value = None
        db = MagicMock()
        from app.services.dashboard_service import get_churn_dashboard
        result = get_churn_dashboard(db, months=6)
        assert result == []


class TestGetLtvDashboard:
    @patch("app.services.dashboard_service.dashboard_cache")
    @patch("app.services.dashboard_service._monthly_member_kpis_rows")
    def test_with_materialized_data(self, mock_kpis, mock_cache):
        mock_cache.get.return_value = None
        mock_kpis.return_value = [
            {"month": "2026-01", "active": 100, "cancelled": 5, "mrr": 10000.0},
            {"month": "2026-02", "active": 95, "cancelled": 8, "mrr": 9500.0},
        ]
        db = MagicMock()
        from app.services.dashboard_service import get_ltv_dashboard
        result = get_ltv_dashboard(db, months=2)
        assert len(result) == 2
        assert result[0].month == "2026-01"
        assert result[0].ltv > 0


class TestGetGrowthDashboard:
    @patch("app.services.dashboard_service.dashboard_cache")
    @patch("app.services.dashboard_service._members_joined_cumulative_by_month")
    @patch("app.services.dashboard_service._month_labels")
    def test_calculates_growth(self, mock_labels, mock_cumulative, mock_cache):
        mock_cache.get.return_value = None
        mock_labels.return_value = ["2026-01", "2026-02", "2026-03"]
        mock_cumulative.return_value = {"2026-01": 80, "2026-02": 100, "2026-03": 110}
        db = MagicMock()
        from app.services.dashboard_service import get_growth_mom_dashboard
        result = get_growth_mom_dashboard(db, months=3)
        assert len(result) == 3
        assert result[0].growth_mom == 0.0  # First month, no previous
        assert result[1].growth_mom == 25.0  # (100-80)/80 * 100


class TestGetOperationalDashboard:
    @patch("app.services.dashboard_service.dashboard_cache")
    def test_returns_operational_data(self, mock_cache):
        mock_cache.get.return_value = None
        db = MagicMock()
        db.scalar.side_effect = [5, 10]  # realtime_checkins, total_inactive
        db.execute.return_value.all.return_value = []  # heatmap
        mock_scalars = MagicMock()
        birthday_member = SimpleNamespace(
            id="birthday-1",
            full_name="Ana",
            birthdate=None,
            extra_data={"birthday_label": "24 de Março"},
            status="active",
            deleted_at=None,
        )
        mock_scalars.all.side_effect = [
            [],  # inactive_7d_items
            [],  # direct birthdate matches
            [birthday_member],  # birthday label candidates
        ]
        db.scalars.return_value = mock_scalars
        from app.services.dashboard_service import get_operational_dashboard
        result = get_operational_dashboard(db)
        assert result["realtime_checkins"] == 5
        assert result["heatmap"] == []
        assert result["birthday_today_total"] == 1
        assert result["birthday_today_items"][0].full_name == "Ana"


class TestGetCommercialDashboard:
    @patch("app.services.dashboard_service.dashboard_cache")
    @patch("app.services.dashboard_service.nps_evolution", return_value=[])
    @patch("app.services.dashboard_service.calculate_cac", return_value=0.0)
    def test_returns_commercial_data(self, mock_cac, mock_nps, mock_cache):
        mock_cache.get.return_value = None
        db = MagicMock()
        db.execute.return_value.all.side_effect = [
            [],  # pipeline_rows
            [],  # source_rows
        ]
        db.scalar.side_effect = [0, 0, 0]  # conversions
        from app.services.dashboard_service import get_commercial_dashboard
        result = get_commercial_dashboard(db)
        assert "pipeline" in result
        assert "cac" in result


class TestGetFinancialDashboard:
    @patch("app.services.dashboard_service.dashboard_cache")
    @patch("app.services.dashboard_service.get_growth_mom_dashboard", return_value=[])
    @patch("app.services.dashboard_service._revenue_series")
    def test_returns_financial_data(self, mock_rev, mock_growth, mock_cache):
        mock_cache.get.return_value = None
        mock_rev.return_value = [SimpleNamespace(month="2026-01", value=10000.0)]
        db = MagicMock()
        db.scalar.side_effect = [0, 100]  # delinquent, active
        from app.services.dashboard_service import get_financial_dashboard
        result = get_financial_dashboard(db)
        assert "monthly_revenue" in result
        assert "delinquency_rate" in result
        assert "projections" in result
