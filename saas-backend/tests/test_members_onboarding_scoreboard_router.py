import uuid
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import MemberStatus, RoleEnum


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


def _member(member_id: str, *, join_days_ago: int, onboarding_status: str):
    return SimpleNamespace(
        id=uuid.UUID(member_id),
        gym_id=GYM_ID,
        join_date=date.today() - timedelta(days=join_days_ago),
        onboarding_status=onboarding_status,
        status=MemberStatus.ACTIVE,
    )


def test_onboarding_scoreboard_returns_only_active_window_members(authed_client):
    client, fake_db = authed_client
    in_window = _member("33333333-3333-3333-3333-333333333333", join_days_ago=6, onboarding_status="active")
    at_risk = _member("44444444-4444-4444-4444-444444444444", join_days_ago=21, onboarding_status="at_risk")
    completed = _member("55555555-5555-5555-5555-555555555555", join_days_ago=10, onboarding_status="completed")
    too_old = _member("66666666-6666-6666-6666-666666666666", join_days_ago=45, onboarding_status="active")

    with (
        patch("app.routers.members.list_member_index", return_value=[in_window, at_risk, completed, too_old]),
        patch(
            "app.routers.members.calculate_onboarding_score",
            side_effect=[
                {"score": 74, "status": "active"},
                {"score": 28, "status": "at_risk"},
            ],
        ) as calculate_mock,
    ):
        response = client.get("/api/v1/members/onboarding-scoreboard")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["expires"] == "0"
    assert response.json() == [
        {"member_id": str(in_window.id), "score": 74, "status": "active"},
        {"member_id": str(at_risk.id), "score": 28, "status": "at_risk"},
    ]
    assert calculate_mock.call_count == 2
    fake_db.assert_not_called()
