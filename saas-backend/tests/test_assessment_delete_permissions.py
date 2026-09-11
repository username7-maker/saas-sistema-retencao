from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum


def _user(role: RoleEnum) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), gym_id=uuid4(), role=role, is_active=True, deleted_at=None)


def _override_actor(app, actor: SimpleNamespace, db: MagicMock) -> None:
    app.dependency_overrides[get_current_user] = lambda: actor
    app.dependency_overrides[get_db] = lambda: db


def _clear_actor(app) -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def test_trainer_can_delete_body_composition(app, client):
    actor = _user(RoleEnum.TRAINER)
    db = MagicMock()
    member_id = uuid4()
    evaluation_id = uuid4()
    evaluation = SimpleNamespace(
        id=evaluation_id,
        evaluation_date=date(2026, 9, 10),
        source="manual",
        deleted_at=datetime(2026, 9, 11, tzinfo=UTC),
    )
    _override_actor(app, actor, db)
    try:
        with patch(
            "app.routers.members.delete_body_composition_evaluation",
            return_value=evaluation,
        ), patch("app.routers.members.log_audit_event"):
            response = client.delete(f"/api/v1/members/{member_id}/body-composition/{evaluation_id}")
    finally:
        _clear_actor(app)

    assert response.status_code == 200
    assert response.json()["message"] == "Avaliacao de bioimpedancia excluida"


def test_trainer_can_delete_anthropometry(app, client):
    actor = _user(RoleEnum.TRAINER)
    db = MagicMock()
    member_id = uuid4()
    assessment_id = uuid4()
    assessment = SimpleNamespace(id=assessment_id)
    _override_actor(app, actor, db)
    try:
        with patch(
            "app.routers.assessments.settings.anthropometric_assessment_v1",
            True,
        ), patch(
            "app.routers.assessments.delete_anthropometric_assessment",
            return_value=(assessment, {"id": str(assessment_id)}),
        ), patch("app.routers.assessments.log_audit_event"):
            response = client.delete(
                f"/api/v1/assessments/members/{member_id}/anthropometry/{assessment_id}"
            )
    finally:
        _clear_actor(app)

    assert response.status_code == 200
    assert "recuperavel" in response.json()["message"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/members/{member_id}/body-composition/{assessment_id}",
        "/api/v1/assessments/members/{member_id}/anthropometry/{assessment_id}",
    ],
)
def test_receptionist_cannot_delete_assessments(app, client, path):
    actor = _user(RoleEnum.RECEPTIONIST)
    db = MagicMock()
    _override_actor(app, actor, db)
    try:
        response = client.delete(path.format(member_id=uuid4(), assessment_id=uuid4()))
    finally:
        _clear_actor(app)

    assert response.status_code == 403
    assert response.json()["detail"] == "Permissao insuficiente"
