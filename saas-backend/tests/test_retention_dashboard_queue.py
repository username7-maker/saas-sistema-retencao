from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import Member, RiskLevel
from app.schemas import PaginatedResponse
from app.schemas.dashboard import RetentionPlaybookStep, RetentionQueueItem


class TestRetentionQueueService:
    def test_plan_cycle_filter_prioritizes_visible_plan_name_over_stale_extra_data(self):
        from app.services.dashboard_service import _retention_plan_cycle_filter
        from sqlalchemy import select

        stmt = select(Member.id).where(_retention_plan_cycle_filter("annual"))
        compiled = str(stmt)
        params = stmt.compile().params

        assert "members.plan_name" in compiled
        assert "%mensal%" in params.values()
        assert "%semestral%" in params.values()
        assert "%anual%" in params.values()
        assert "annual" in params.values()

    @patch("app.services.dashboard_service.get_assessment_forecast")
    @patch("app.services.dashboard_service.classify_churn_type")
    @patch("app.services.dashboard_service.build_retention_playbook")
    @patch("app.services.dashboard_service.get_current_gym_id")
    def test_computes_missing_churn_type_and_forecast_for_queue_without_committing(
        self,
        mock_get_current_gym_id,
        mock_build_playbook,
        mock_classify_churn_type,
        mock_get_assessment_forecast,
        gym_id,
    ):
        from app.services.dashboard_service import get_retention_queue

        mock_get_current_gym_id.return_value = gym_id
        mock_build_playbook.return_value = [
            {
                "action": "call",
                "priority": "high",
                "title": "Ligar hoje",
                "message": "Contato imediato.",
                "due_days": 0,
                "owner": "reception",
            }
        ]
        mock_classify_churn_type.return_value = "voluntary_dissatisfaction"
        mock_get_assessment_forecast.return_value = {"probability_60d": 41}

        member_id = UUID("33333333-3333-3333-3333-333333333339")
        db = MagicMock()
        db.scalar.return_value = 1
        db.scalars.return_value.all.return_value = [member_id]

        member = SimpleNamespace(
            id=member_id,
            full_name="Membro Sem Contexto",
            email="membro@teste.com",
            phone="5511999991111",
            plan_name="Plano Mensal",
            risk_score=82,
            risk_level=RiskLevel.RED,
            nps_last_score=4,
            last_checkin_at=datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc),
            churn_type=None,
            extra_data={},
            join_date=date(2025, 9, 1),
        )
        queue_rows = MagicMock()
        queue_rows.all.return_value = [
            (
                SimpleNamespace(
                    id=UUID("44444444-4444-4444-4444-444444444449"),
                    score=82,
                    level=RiskLevel.RED,
                    reasons={"frequency_drop_pct": 48},
                    action_history=[],
                    automation_stage="d14",
                    created_at=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
                ),
                member,
            )
        ]

        contact_rows = MagicMock()
        contact_rows.all.return_value = []
        db.execute.side_effect = [queue_rows, contact_rows]

        result = get_retention_queue(db, page=1, page_size=50)

        assert not db.commit.called
        assert member.churn_type is None
        assert member.extra_data == {}
        assert result.items[0].churn_type == "voluntary_dissatisfaction"
        assert result.items[0].forecast_60d == 41

    @patch("app.services.dashboard_service.build_retention_playbook")
    @patch("app.services.dashboard_service.get_current_gym_id")
    def test_returns_paginated_alert_queue_with_member_snapshot(self, mock_get_current_gym_id, mock_build_playbook, gym_id):
        from app.services.dashboard_service import get_retention_queue

        mock_get_current_gym_id.return_value = gym_id
        mock_build_playbook.return_value = [
            {
                "action": "whatsapp",
                "priority": "high",
                "title": "Mensagem de reengajamento",
                "message": "Retome o treino esta semana.",
                "due_days": 0,
                "owner": "reception",
            }
        ]

        member_red_id = UUID("33333333-3333-3333-3333-333333333331")
        member_yellow_id = UUID("33333333-3333-3333-3333-333333333332")
        db = MagicMock()
        db.scalar.return_value = 2
        db.scalars.return_value.all.return_value = [member_red_id]

        queue_rows = MagicMock()
        queue_rows.all.return_value = [
            (
                SimpleNamespace(
                    id=UUID("44444444-4444-4444-4444-444444444441"),
                    score=88,
                    level=RiskLevel.RED,
                    reasons={"frequency_drop_pct": 62, "shift_change_hours": 3},
                    action_history=[{"type": "email"}],
                    automation_stage="d14",
                    created_at=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
                ),
                SimpleNamespace(
                    id=member_red_id,
                    full_name="Ana Silva",
                    email="ana@teste.com",
                    phone="5511999990001",
                    plan_name="Plano Premium",
                    risk_score=88,
                    risk_level=RiskLevel.RED,
                    nps_last_score=5,
                    last_checkin_at=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
                    churn_type="voluntary_dissatisfaction",
                    extra_data={"retention_forecast_60d": 34},
                    join_date=date(2025, 12, 1),
                ),
            ),
            (
                SimpleNamespace(
                    id=UUID("44444444-4444-4444-4444-444444444442"),
                    score=51,
                    level=RiskLevel.YELLOW,
                    reasons={},
                    action_history=[],
                    automation_stage="d7",
                    created_at=datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc),
                ),
                SimpleNamespace(
                    id=member_yellow_id,
                    full_name="Bruno Lima",
                    email="bruno@teste.com",
                    phone=None,
                    plan_name="Plano Mensal",
                    risk_score=51,
                    risk_level=RiskLevel.YELLOW,
                    nps_last_score=8,
                    last_checkin_at=datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc),
                    churn_type="involuntary_inactivity",
                    extra_data={},
                    join_date=date(2026, 1, 10),
                ),
            ),
        ]

        contact_rows = MagicMock()
        contact_rows.all.return_value = [
            SimpleNamespace(member_id=member_red_id, last_at=datetime(2026, 3, 15, 18, 0, tzinfo=timezone.utc))
        ]

        db.execute.side_effect = [queue_rows, contact_rows]

        result = get_retention_queue(db, page=1, page_size=50)

        assert result.total == 2
        assert result.page == 1
        assert result.page_size == 50
        assert len(result.items) == 2
        assert result.items[0].risk_level == RiskLevel.RED
        assert result.items[0].full_name == "Ana Silva"
        assert result.items[0].forecast_60d == 34
        assert result.items[0].next_action == "Mensagem de reengajamento"
        assert result.items[0].assistant is not None
        assert result.items[0].assistant.recommended_channel == "Ligacao"
        assert result.items[0].playbook_steps == [
            RetentionPlaybookStep(
                action="whatsapp",
                priority="high",
                title="Mensagem de reengajamento",
                message="Retome o treino esta semana.",
                due_days=0,
                owner="reception",
            )
        ]
        assert result.items[0].last_contact_at == datetime(2026, 3, 15, 18, 0, tzinfo=timezone.utc)
        assert "queda de 62% na frequência" in result.items[0].signals_summary
        assert result.items[1].risk_level == RiskLevel.RED

    @patch("app.services.dashboard_service.get_assessment_forecast")
    @patch("app.services.dashboard_service.build_retention_playbook")
    @patch("app.services.dashboard_service.get_current_gym_id")
    def test_hides_artificial_drop_and_forecast_without_baseline_or_assessment_context(
        self,
        mock_get_current_gym_id,
        mock_build_playbook,
        mock_get_assessment_forecast,
        gym_id,
    ):
        from app.services.dashboard_service import get_retention_queue

        mock_get_current_gym_id.return_value = gym_id
        mock_build_playbook.return_value = []

        member_id = UUID("33333333-3333-3333-3333-333333333338")
        db = MagicMock()
        db.scalar.return_value = 1
        db.scalars.return_value.all.return_value = []

        queue_rows = MagicMock()
        queue_rows.all.return_value = [
            (
                SimpleNamespace(
                    id=UUID("44444444-4444-4444-4444-444444444448"),
                    score=74,
                    level=RiskLevel.RED,
                    reasons={"frequency_drop_pct": 100.0, "baseline_avg_weekly": 0.22},
                    action_history=[],
                    automation_stage="d21",
                    created_at=datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc),
                ),
                SimpleNamespace(
                    id=member_id,
                    full_name="Sem Baseline",
                    email="sem-baseline@teste.com",
                    phone="5511999991112",
                    plan_name="Plano Mensal",
                    risk_score=74,
                    risk_level=RiskLevel.RED,
                    nps_last_score=7,
                    last_checkin_at=datetime(2026, 3, 27, 8, 0, tzinfo=timezone.utc),
                    churn_type="involuntary_inactivity",
                    extra_data={"retention_forecast_60d": 31, "retention_forecast_source": "assessment_fallback"},
                    join_date=date(2025, 9, 1),
                ),
            )
        ]

        contact_rows = MagicMock()
        contact_rows.all.return_value = []
        db.execute.side_effect = [queue_rows, contact_rows]

        result = get_retention_queue(db, page=1, page_size=50)

        assert result.items[0].forecast_60d is None
        assert result.items[0].reasons["frequency_drop_pct"] is None
        assert "queda de" not in result.items[0].signals_summary
        assert "forecast em" not in result.items[0].signals_summary
        assert not mock_get_assessment_forecast.called

    @patch("app.services.dashboard_service.get_current_gym_id")
    def test_search_filters_and_pagination_are_applied(self, mock_get_current_gym_id, gym_id):
        from app.services.dashboard_service import get_retention_queue

        mock_get_current_gym_id.return_value = gym_id
        db = MagicMock()
        db.scalar.return_value = 0
        execute_result = MagicMock()
        execute_result.all.return_value = []
        db.execute.return_value = execute_result

        get_retention_queue(
            db,
            page=2,
            page_size=50,
            search="retencao",
            level="red",
            churn_type="voluntary_dissatisfaction",
            plan_cycle="annual",
            preferred_shift="morning",
        )

        stmt = db.execute.call_args.args[0]
        compiled = str(stmt)
        params = stmt.compile().params
        assert "members.full_name" in compiled
        assert "members.email" in compiled
        assert "members.plan_name" in compiled
        assert "risk_alerts.gym_id" in compiled
        assert "members.churn_type" in compiled
        assert "members.preferred_shift" in compiled
        assert "annual" in params.values()
        assert "%anual%" in params.values()
        assert any(value == "morning" or (isinstance(value, list) and "morning" in value) for value in params.values())
        assert stmt._limit_clause.value == 50
        assert stmt._offset_clause.value == 50


    @patch("app.services.dashboard_service.build_retention_playbook")
    @patch("app.services.dashboard_service.get_current_gym_id")
    def test_escalates_stale_yellow_alert_to_red_when_inactivity_is_already_extreme(self, mock_get_current_gym_id, mock_build_playbook, gym_id):
        from app.services.dashboard_service import get_retention_queue

        mock_get_current_gym_id.return_value = gym_id
        mock_build_playbook.return_value = []

        member_id = UUID("33333333-3333-3333-3333-333333333337")
        db = MagicMock()
        db.scalar.return_value = 1
        db.scalars.return_value.all.return_value = []

        queue_rows = MagicMock()
        queue_rows.all.return_value = [
            (
                SimpleNamespace(
                    id=UUID("44444444-4444-4444-4444-444444444447"),
                    score=52,
                    level=RiskLevel.YELLOW,
                    reasons={},
                    action_history=[],
                    automation_stage="d14",
                    created_at=datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
                ),
                SimpleNamespace(
                    id=member_id,
                    full_name="Christian Da Rosa",
                    email="christian@teste.com",
                    phone="5554999305274",
                    plan_name="LIVRE MENSAL",
                    risk_score=52,
                    risk_level=RiskLevel.YELLOW,
                    nps_last_score=7,
                    last_checkin_at=datetime(2026, 2, 24, 8, 0, tzinfo=timezone.utc),
                    churn_type="involuntary_seasonal",
                    extra_data={},
                    join_date=date(2025, 1, 10),
                ),
            ),
        ]

        contact_rows = MagicMock()
        contact_rows.all.return_value = []
        db.execute.side_effect = [queue_rows, contact_rows]

        result = get_retention_queue(db, page=1, page_size=50)

        assert result.items[0].days_without_checkin >= 58
        assert result.items[0].risk_level == RiskLevel.RED
        assert result.items[0].risk_score >= 90


class TestRetentionQueueRoute:
    def test_requires_authentication(self, client):
        response = client.get("/api/v1/dashboards/retention/queue")

        assert response.status_code == 401

    def test_returns_paginated_queue_payload(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch(
                "app.routers.dashboards.get_retention_queue",
                return_value=PaginatedResponse(
                    items=[
                        RetentionQueueItem(
                            alert_id="44444444-4444-4444-4444-444444444441",
                            member_id="33333333-3333-3333-3333-333333333331",
                            full_name="Ana Silva",
                            email="ana@teste.com",
                            phone="5511999990001",
                            plan_name="Plano Premium",
                            risk_level=RiskLevel.RED,
                            risk_score=88,
                            nps_last_score=5,
                            days_without_checkin=9,
                            last_checkin_at=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
                            last_contact_at=datetime(2026, 3, 15, 18, 0, tzinfo=timezone.utc),
                            churn_type="voluntary_dissatisfaction",
                            automation_stage="d14",
                            created_at=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
                            forecast_60d=34,
                            signals_summary="9 dias sem check-in · queda de 62% na frequência",
                            next_action="Mensagem de reengajamento",
                            reasons={"frequency_drop_pct": 62},
                            action_history=[],
                            playbook_steps=[],
                            assistant=None,
                        )
                    ],
                    total=1,
                    page=1,
                    page_size=50,
                ),
            ):
                response = client.get(
                    "/api/v1/dashboards/retention/queue?page=1&page_size=50&level=red&search=Ana"
                )

            assert response.status_code == 200
            body = response.json()
            assert body["total"] == 1
            assert body["items"][0]["alert_id"] == "44444444-4444-4444-4444-444444444441"
            assert body["items"][0]["risk_level"] == "red"
            assert "assistant" in body["items"][0]
        finally:
            app.dependency_overrides.clear()

    def test_forwards_plan_cycle_filter(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch(
                "app.routers.dashboards.get_retention_queue",
                return_value=PaginatedResponse(items=[], total=0, page=1, page_size=50),
            ) as mock_get_retention_queue:
                response = client.get("/api/v1/dashboards/retention/queue?plan_cycle=semiannual")

            assert response.status_code == 200
            assert mock_get_retention_queue.call_args.kwargs["plan_cycle"] == "semiannual"
        finally:
            app.dependency_overrides.clear()

    def test_forwards_preferred_shift_filter(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch(
                "app.routers.dashboards.get_retention_queue",
                return_value=PaginatedResponse(items=[], total=0, page=1, page_size=50),
            ) as mock_get_retention_queue:
                response = client.get("/api/v1/dashboards/retention/queue?preferred_shift=evening")

            assert response.status_code == 200
            assert mock_get_retention_queue.call_args.kwargs["preferred_shift"] == "evening"
        finally:
            app.dependency_overrides.clear()
