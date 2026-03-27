from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RiskLevel
from app.schemas import PaginatedResponse
from app.schemas.assessment import AssessmentQueueItemOut


class TestAssessmentQueueService:
    @patch("app.services.assessment_analytics_service.get_current_gym_id")
    def test_returns_paginated_queue_items_with_operational_labels(self, mock_get_current_gym_id, gym_id):
        from app.services.assessment_analytics_service import get_assessments_queue

        mock_get_current_gym_id.return_value = gym_id
        db = MagicMock()
        db.scalar.return_value = 2
        execute_result = MagicMock()
        execute_result.all.return_value = [
            SimpleNamespace(
                id="33333333-3333-3333-3333-333333333331",
                full_name="Ana Silva",
                email="ana@teste.com",
                plan_name="Plano Mensal",
                risk_level=RiskLevel.RED,
                risk_score=88,
                last_checkin_at=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
                next_assessment_due=None,
                queue_bucket="never",
                urgency_score=388,
            ),
            SimpleNamespace(
                id="33333333-3333-3333-3333-333333333332",
                full_name="Bruno Lima",
                email="bruno@teste.com",
                plan_name="Plano Anual",
                risk_level=RiskLevel.YELLOW,
                risk_score=51,
                last_checkin_at=datetime(2026, 3, 17, 10, 0, tzinfo=timezone.utc),
                next_assessment_due=date(2026, 3, 10),
                queue_bucket="overdue",
                urgency_score=291,
            ),
        ]
        db.execute.return_value = execute_result

        result = get_assessments_queue(db, page=1, page_size=50)

        assert result.total == 2
        assert result.page == 1
        assert result.page_size == 50
        assert len(result.items) == 2
        assert result.items[0].queue_bucket == "never"
        assert result.items[0].coverage_label == "Nenhuma avaliacao registrada"
        assert result.items[0].due_label == "Primeira avaliacao pendente"
        assert result.items[1].queue_bucket == "overdue"
        assert "10/03/2026" in result.items[1].due_label

    @patch("app.services.assessment_analytics_service.get_current_gym_id")
    def test_search_query_uses_name_email_and_plan_name(self, mock_get_current_gym_id, gym_id):
        from app.services.assessment_analytics_service import get_assessments_queue

        mock_get_current_gym_id.return_value = gym_id
        db = MagicMock()
        db.scalar.return_value = 0
        execute_result = MagicMock()
        execute_result.all.return_value = []
        db.execute.return_value = execute_result

        get_assessments_queue(db, page=1, page_size=50, search="Erica")

        stmt = db.execute.call_args.args[0]
        compiled = str(stmt)
        assert "members.full_name" in compiled
        assert "members.email" in compiled
        assert "members.plan_name" in compiled

    @patch("app.services.assessment_analytics_service.get_current_gym_id")
    def test_search_query_in_all_bucket_does_not_force_operational_window_filters(self, mock_get_current_gym_id, gym_id):
        from app.services.assessment_analytics_service import get_assessments_queue

        mock_get_current_gym_id.return_value = gym_id
        db = MagicMock()
        db.scalar.return_value = 0
        execute_result = MagicMock()
        execute_result.all.return_value = []
        db.execute.return_value = execute_result

        get_assessments_queue(db, page=1, page_size=50, search="Erick", bucket="all")

        stmt = db.execute.call_args.args[0]
        compiled = str(stmt)
        assert "members.join_date >=" not in compiled
        assert "members.last_checkin_at >=" not in compiled

    @patch("app.services.assessment_analytics_service.get_current_gym_id")
    def test_queue_items_expose_resolution_metadata(self, mock_get_current_gym_id, gym_id):
        from app.services.assessment_analytics_service import get_assessments_queue

        mock_get_current_gym_id.return_value = gym_id
        db = MagicMock()
        db.scalar.return_value = 1
        execute_result = MagicMock()
        execute_result.all.return_value = [
            SimpleNamespace(
                id="33333333-3333-3333-3333-333333333335",
                full_name="Erick Bedin",
                email="erick@teste.com",
                plan_name="Plano Mensal",
                risk_level=RiskLevel.YELLOW,
                risk_score=62,
                last_checkin_at=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
                next_assessment_due=date(2026, 3, 28),
                queue_bucket="week",
                urgency_score=242,
                queue_resolution_status="scheduled",
                queue_resolution_note="Ja alinhado com a recepcao",
            )
        ]
        db.execute.return_value = execute_result

        result = get_assessments_queue(db, page=1, page_size=50, search="Erick", bucket="all")

        assert result.items[0].queue_resolution_status == "scheduled"
        assert result.items[0].queue_resolution_label == "Ja foi marcada"
        assert result.items[0].queue_resolution_note == "Ja alinhado com a recepcao"

    @patch("app.services.assessment_analytics_service.get_current_gym_id")
    def test_bucket_filter_and_offset_are_applied(self, mock_get_current_gym_id, gym_id):
        from app.services.assessment_analytics_service import get_assessments_queue

        mock_get_current_gym_id.return_value = gym_id
        db = MagicMock()
        db.scalar.return_value = 0
        execute_result = MagicMock()
        execute_result.all.return_value = []
        db.execute.return_value = execute_result

        get_assessments_queue(db, page=2, page_size=50, bucket="never")

        stmt = db.execute.call_args.args[0]
        compiled = str(stmt)
        assert "last_assessment_date" in compiled
        assert "members.status" in compiled
        assert "members.join_date" in compiled
        assert stmt._limit_clause.value == 50
        assert stmt._offset_clause.value == 50

    @patch("app.services.assessment_analytics_service.get_current_gym_id")
    @patch("app.services.assessment_analytics_service.get_assessments_queue")
    def test_dashboard_counts_scope_assessments_to_active_members(self, mock_get_queue, mock_get_current_gym_id, gym_id):
        from app.services.assessment_analytics_service import get_assessments_dashboard

        mock_get_current_gym_id.return_value = gym_id
        mock_get_queue.return_value = PaginatedResponse(items=[], total=0, page=1, page_size=6)
        db = MagicMock()
        db.scalar.side_effect = [120, 64, 80, 18, 12, 5, 3, 2]
        scalars_result = MagicMock()
        scalars_result.all.return_value = []
        db.scalars.return_value = scalars_result

        payload = get_assessments_dashboard(db)

        assert payload["total_members"] == 120
        assert payload["never_assessed"] == 12
        assert payload["overdue_assessments"] == 18
        assert payload["historical_backlog_total"] == 5
        assert payload["historical_never_assessed"] == 3
        assert payload["historical_overdue_assessments"] == 2

        compiled_scalars = [str(call.args[0]) for call in db.scalar.call_args_list]
        assert any("JOIN members" in stmt and "members.status" in stmt for stmt in compiled_scalars)


class TestAssessmentQueueRoute:
    def test_requires_authentication(self, client):
        response = client.get("/api/v1/assessments/queue")

        assert response.status_code == 401

    def test_returns_paginated_queue_payload(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch(
                "app.routers.assessments.get_assessments_queue",
                return_value=PaginatedResponse(
                    items=[
                        AssessmentQueueItemOut(
                            id="33333333-3333-3333-3333-333333333333",
                            full_name="Ana Silva",
                            email="ana@teste.com",
                            plan_name="Plano Mensal",
                            risk_level=RiskLevel.RED,
                            risk_score=88,
                            last_checkin_at=datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc),
                            next_assessment_due=None,
                            queue_bucket="never",
                            coverage_label="Nenhuma avaliacao registrada",
                            due_label="Primeira avaliacao pendente",
                            urgency_score=388,
                        )
                    ],
                    total=1,
                    page=1,
                    page_size=50,
                ),
            ):
                response = client.get("/api/v1/assessments/queue?page=1&page_size=50&bucket=never")

            assert response.status_code == 200
            body = response.json()
            assert body["total"] == 1
            assert body["items"][0]["queue_bucket"] == "never"
        finally:
            app.dependency_overrides.clear()

    def test_updates_queue_resolution(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with (
                patch("app.routers.assessments.get_request_context", return_value={"ip_address": None, "user_agent": None}),
                patch("app.routers.assessments.log_audit_event"),
                patch(
                    "app.routers.assessments.update_assessment_queue_resolution",
                    return_value=SimpleNamespace(
                        id="33333333-3333-3333-3333-333333333333",
                        extra_data={
                            "assessment_queue_resolution": "scheduled",
                            "assessment_queue_resolution_note": "Ligacao feita",
                            "assessment_queue_resolution_at": "2026-03-27T16:00:00+00:00",
                        },
                    ),
                ) as resolution_mock,
            ):
                response = client.put(
                    "/api/v1/assessments/members/33333333-3333-3333-3333-333333333333/queue-resolution",
                    json={"status": "scheduled", "note": "Ligacao feita"},
                )

            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "scheduled"
            assert body["label"] == "Ja foi marcada"
            assert resolution_mock.call_args.kwargs["resolution_status"] == "scheduled"
        finally:
            app.dependency_overrides.clear()
