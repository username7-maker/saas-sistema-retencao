from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum, RiskLevel
from app.schemas import PaginatedResponse
from app.schemas.assessment import AssessmentQueueItemOut


def _mock_trainer():
    return SimpleNamespace(
        id="trainer-1",
        gym_id="11111111-1111-1111-1111-111111111111",
        full_name="Trainer Teste",
        email="trainer@teste.com",
        role=RoleEnum.TRAINER,
        is_active=True,
        deleted_at=None,
    )


def test_trainer_can_access_assessments_queue(app, client):
    mock_db = SimpleNamespace()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = _mock_trainer

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
            response = client.get("/api/v1/assessments/queue")

        assert response.status_code == 200
        assert response.json()["items"][0]["full_name"] == "Ana Silva"
    finally:
        app.dependency_overrides.clear()


def test_trainer_cannot_access_user_admin_routes(app, client):
    mock_db = SimpleNamespace()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = _mock_trainer

    try:
        response = client.get("/api/v1/users/")
        assert response.status_code == 403
        assert response.json()["detail"] == "Permissao insuficiente"
    finally:
        app.dependency_overrides.clear()
