import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def authed_client(app):
    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        gym_id=GYM_ID,
        role=RoleEnum.OWNER,
        is_active=True,
        deleted_at=None,
        full_name="Owner Teste",
        email="owner@teste.com",
    )
    fake_db = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: fake_db

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, fake_db

    app.dependency_overrides.clear()


def test_onboarding_scoreboard_returns_persisted_snapshots_without_recalculating_scores(authed_client):
    client, fake_db = authed_client
    in_window_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    at_risk_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    fake_db.execute.return_value.all.return_value = [
        (in_window_id, 74, "active"),
        (at_risk_id, 28, "at_risk"),
    ]

    with (
        patch("app.routers.members.list_member_index", side_effect=AssertionError("scoreboard must not load full member index")),
        patch("app.routers.members.calculate_onboarding_score", side_effect=AssertionError("scoreboard must use snapshots")) as calculate_mock,
    ):
        response = client.get("/api/v1/members/onboarding-scoreboard")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["expires"] == "0"
    assert response.json() == [
        {"member_id": str(in_window_id), "score": 74, "status": "active"},
        {"member_id": str(at_risk_id), "score": 28, "status": "at_risk"},
    ]
    fake_db.execute.assert_called_once()
    calculate_mock.assert_not_called()
