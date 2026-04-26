"""Tests for dashboard_service covering all dashboard endpoints."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models import MemberStatus, RiskLevel
from app.schemas import BICohortPoint, BIFollowUpImpact, LTVPoint, ProjectionPoint
from app.schemas.member import MemberOut


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PT_MONTH_LABELS = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def _today_birthday_label() -> str:
    today = datetime.now(tz=timezone.utc).date()
    return f"{today.day} de {_PT_MONTH_LABELS[today.month]}"


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
            id=uuid.uuid4(),
            full_name="Ana",
            email="ana@teste.com",
            phone="5511999990001",
            birthdate=None,
            plan_name="Plano Base",
            monthly_fee=Decimal("99.90"),
            join_date=date(2026, 1, 1),
            preferred_shift="manha",
            nps_last_score=8,
            loyalty_months=1,
            risk_score=10,
            risk_level=RiskLevel.GREEN,
            last_checkin_at=None,
            extra_data={"birthday_label": _today_birthday_label()},
            status=MemberStatus.ACTIVE,
            suggested_action=None,
            onboarding_score=0,
            onboarding_status="active",
            churn_type=None,
            is_vip=False,
            retention_stage=None,
            created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc),
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
        assert isinstance(result["birthday_today_items"][0], MemberOut)
        cached_payload = mock_cache.set.call_args.args[1]
        assert isinstance(cached_payload["birthday_today_items"][0], dict)
        assert cached_payload["birthday_today_items"][0]["full_name"] == "Ana"


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
        db.scalars.return_value.all.return_value = []
        db.scalar.side_effect = [0, 0, 0]  # conversions
        from app.services.dashboard_service import get_commercial_dashboard
        result = get_commercial_dashboard(db)
        assert "pipeline" in result
        assert "cac" in result


class TestGetRetentionDashboard:
    @patch("app.services.dashboard_service.dashboard_cache")
    @patch("app.services.dashboard_service.nps_evolution", return_value=[])
    @patch("app.services.dashboard_service.classify_churn_type", return_value="involuntary_inactivity")
    def test_serializes_member_snapshots_without_committing(
        self,
        mock_classify,
        mock_nps,
        mock_cache,
    ):
        mock_cache.get.return_value = None
        db = MagicMock()
        db.scalar.side_effect = [2, 1, Decimal("499.90"), 81.2, 47.5]

        red_member = SimpleNamespace(
            id=uuid.uuid4(),
            full_name="Aluno Vermelho",
            email="red@teste.com",
            phone="5511999990001",
            birthdate=None,
            status=MemberStatus.ACTIVE,
            plan_name="Plano Premium",
            monthly_fee=Decimal("249.95"),
            join_date=date(2025, 12, 1),
            preferred_shift="manha",
            nps_last_score=4,
            loyalty_months=3,
            risk_score=82,
            risk_level=RiskLevel.RED,
            last_checkin_at=datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc),
            extra_data={},
            suggested_action=None,
            onboarding_score=0,
            onboarding_status="active",
            churn_type=None,
            is_vip=False,
            retention_stage=None,
            created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc),
        )
        yellow_member = SimpleNamespace(
            id=uuid.uuid4(),
            full_name="Aluno Amarelo",
            email="yellow@teste.com",
            phone="5511999990002",
            birthdate=None,
            status=MemberStatus.ACTIVE,
            plan_name="Plano Base",
            monthly_fee=Decimal("249.95"),
            join_date=date(2026, 1, 10),
            preferred_shift="noite",
            nps_last_score=7,
            loyalty_months=1,
            risk_score=48,
            risk_level=RiskLevel.YELLOW,
            last_checkin_at=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
            extra_data={},
            suggested_action=None,
            onboarding_score=0,
            onboarding_status="active",
            churn_type="voluntary_financial",
            is_vip=False,
            retention_stage=None,
            created_at=datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
        )

        contact_rows = MagicMock()
        contact_rows.all.return_value = []
        churn_rows = MagicMock()
        churn_rows.all.return_value = [
            SimpleNamespace(churn_type="unknown", total=1),
            SimpleNamespace(churn_type="voluntary_financial", total=1),
        ]

        red_scalars = MagicMock()
        red_scalars.all.return_value = [red_member]
        yellow_scalars = MagicMock()
        yellow_scalars.all.return_value = [yellow_member]

        db.scalars.side_effect = [red_scalars, yellow_scalars]
        db.execute.side_effect = [
            churn_rows,
            contact_rows,
        ]

        from app.services.dashboard_service import get_retention_dashboard

        result = get_retention_dashboard(db, red_page=1, yellow_page=1, page_size=20)

        assert isinstance(result["red"]["items"][0], MemberOut)
        assert result["red"]["items"][0].churn_type == "involuntary_inactivity"
        assert result["yellow"]["items"][0].churn_type == "voluntary_financial"
        assert not db.commit.called
        cached_payload = mock_cache.set.call_args.args[1]
        assert isinstance(cached_payload["red"]["items"][0], dict)
        assert cached_payload["red"]["items"][0]["full_name"] == "Aluno Vermelho"
        assert cached_payload["yellow"]["items"][0]["churn_type"] == "voluntary_financial"


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


class TestGetBIFoundationDashboard:
    @patch("app.services.dashboard_service.dashboard_cache")
    @patch("app.services.dashboard_service._resolve_dashboard_gym_id", return_value=GYM_ID)
    @patch("app.services.dashboard_service._follow_up_impact")
    @patch("app.services.dashboard_service.get_retention_dashboard")
    @patch("app.services.dashboard_service.get_financial_dashboard")
    @patch("app.services.dashboard_service.get_ltv_dashboard")
    @patch("app.services.dashboard_service._cohort_points")
    def test_composes_bi_foundation_payload(
        self,
        mock_cohort,
        mock_ltv,
        mock_financial,
        mock_retention,
        mock_impact,
        mock_gym,
        mock_cache,
    ):
        mock_cache.get.return_value = None
        mock_cohort.return_value = [
            BICohortPoint(month="2026-02", joined=10, active=8, retained_rate=80.0, mrr=1200.0)
        ]
        mock_ltv.return_value = [LTVPoint(month="2026-02", ltv=900.0)]
        mock_financial.return_value = {
            "monthly_revenue": [],
            "delinquency_rate": 0.0,
            "projections": [ProjectionPoint(horizon_months=3, projected_revenue=15000.0)],
        }
        mock_retention.return_value = {
            "red": {"total": 2, "items": []},
            "yellow": {"total": 3, "items": []},
            "nps_trend": [],
            "mrr_at_risk": 2500.0,
            "avg_red_score": 80.0,
            "avg_yellow_score": 55.0,
            "churn_distribution": {},
            "last_contact_map": {},
        }
        mock_impact.return_value = BIFollowUpImpact(
            prepared_actions_30d=4,
            positive_outcomes_30d=2,
            completed_followups_30d=3,
            retention_contacts_30d=5,
            acceptance_rate=50.0,
            data_quality="ready",
        )

        from app.services.dashboard_service import get_bi_foundation_dashboard

        result = get_bi_foundation_dashboard(MagicMock(), months=6)

        assert result.cohort[0].retained_rate == 80.0
        assert result.ltv[0].ltv == 900.0
        assert result.forecast[0].projected_revenue == 15000.0
        assert result.revenue_at_risk == 2500.0
        assert result.revenue_at_risk_members == 5
        assert result.follow_up_impact.acceptance_rate == 50.0
        assert result.data_quality_flags == []
        mock_cohort.assert_called_once_with(mock_cohort.call_args.args[0], 6, gym_id=GYM_ID)
        mock_cache.set.assert_called_once()

    @patch("app.services.dashboard_service.dashboard_cache")
    @patch("app.services.dashboard_service._resolve_dashboard_gym_id", return_value=None)
    @patch("app.services.dashboard_service._follow_up_impact")
    @patch("app.services.dashboard_service.get_retention_dashboard")
    @patch("app.services.dashboard_service.get_financial_dashboard")
    @patch("app.services.dashboard_service.get_ltv_dashboard", return_value=[])
    @patch("app.services.dashboard_service._cohort_points", return_value=[])
    def test_flags_missing_operational_base(
        self,
        mock_cohort,
        mock_ltv,
        mock_financial,
        mock_retention,
        mock_impact,
        mock_gym,
        mock_cache,
    ):
        mock_cache.get.return_value = None
        mock_financial.return_value = {"monthly_revenue": [], "delinquency_rate": 0.0, "projections": []}
        mock_retention.return_value = {
            "red": {"total": 1, "items": []},
            "yellow": {"total": 0, "items": []},
            "nps_trend": [],
            "mrr_at_risk": 0.0,
            "avg_red_score": 0.0,
            "avg_yellow_score": 0.0,
            "churn_distribution": {},
            "last_contact_map": {},
        }
        mock_impact.return_value = BIFollowUpImpact(
            prepared_actions_30d=0,
            positive_outcomes_30d=0,
            completed_followups_30d=0,
            retention_contacts_30d=0,
            acceptance_rate=None,
            data_quality="no_base",
        )

        from app.services.dashboard_service import get_bi_foundation_dashboard

        result = get_bi_foundation_dashboard(MagicMock(), months=6)

        assert "missing_cohort_history" in result.data_quality_flags
        assert "missing_ltv_history" in result.data_quality_flags
        assert "missing_follow_up_outcomes" in result.data_quality_flags
        assert "revenue_at_risk_without_fee_base" in result.data_quality_flags
