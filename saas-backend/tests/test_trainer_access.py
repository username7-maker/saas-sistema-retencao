from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum, RiskLevel, TaskPriority, TaskStatus
from app.schemas import PaginatedResponse, TaskOut
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


def test_trainer_cannot_access_member_timeline(app, client):
    mock_db = SimpleNamespace()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = _mock_trainer

    try:
        response = client.get("/api/v1/members/11111111-1111-1111-1111-111111111111/timeline")
        assert response.status_code == 403
        assert response.json()["detail"] == "Permissao insuficiente"
    finally:
        app.dependency_overrides.clear()


def _technical_task_out():
    return TaskOut(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        title="Professor revisar restricoes de Ana Silva",
        description="Task tecnica",
        member_id=UUID("33333333-3333-3333-3333-333333333333"),
        lead_id=None,
        assigned_to_user_id=None,
        member_name="Ana Silva",
        lead_name=None,
        priority=TaskPriority.HIGH,
        status=TaskStatus.TODO,
        kanban_column="todo",
        due_date=None,
        completed_at=None,
        suggested_message=None,
        extra_data={"source": "assessment_intelligence", "owner_role": "coach"},
        created_at=datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc),
    )


def test_trainer_can_list_technical_tasks(app, client):
    mock_db = SimpleNamespace()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = _mock_trainer

    try:
        with patch(
            "app.routers.tasks.list_tasks",
            return_value=PaginatedResponse(items=[_technical_task_out()], total=1, page=1, page_size=20),
        ) as list_mock:
            response = client.get("/api/v1/tasks/")

        assert response.status_code == 200
        assert response.json()["items"][0]["title"] == "Professor revisar restricoes de Ana Silva"
        assert list_mock.call_args.kwargs["current_user"].role == RoleEnum.TRAINER
    finally:
        app.dependency_overrides.clear()


def test_trainer_can_patch_technical_task_status(app, client):
    mock_db = SimpleNamespace(commit=lambda: None)
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = _mock_trainer

    try:
        with (
            patch("app.routers.tasks.get_request_context", return_value={"ip_address": None, "user_agent": None}),
            patch("app.routers.tasks.log_audit_event"),
            patch("app.routers.tasks.update_task", return_value=_technical_task_out()) as update_mock,
        ):
            response = client.patch(
                "/api/v1/tasks/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                json={"status": "done"},
            )

        assert response.status_code == 200
        assert update_mock.call_args.kwargs["current_user"].role == RoleEnum.TRAINER
        assert update_mock.call_args.kwargs["commit"] is False
    finally:
        app.dependency_overrides.clear()


def test_trainer_cannot_create_tasks(app, client):
    mock_db = SimpleNamespace()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = _mock_trainer

    try:
        response = client.post(
            "/api/v1/tasks/",
            json={"title": "Nova task tecnica", "priority": "high", "status": "todo"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Permissao insuficiente"
    finally:
        app.dependency_overrides.clear()


def test_trainer_cannot_delete_tasks(app, client):
    mock_db = SimpleNamespace()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = _mock_trainer

    try:
        response = client.delete("/api/v1/tasks/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

        assert response.status_code == 403
        assert response.json()["detail"] == "Permissao insuficiente"
    finally:
        app.dependency_overrides.clear()
