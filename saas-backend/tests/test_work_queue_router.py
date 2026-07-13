import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum
from app.schemas.work_queue import WorkQueueItemOut


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def wq_client(app):
    fake_owner = SimpleNamespace(
        id=USER_ID,
        gym_id=GYM_ID,
        role=RoleEnum.OWNER,
        work_shift="morning",
        work_shift_scope=None,
        is_active=True,
        deleted_at=None,
        full_name="Operador Sintetico",
    )
    fake_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: fake_owner
    app.dependency_overrides[get_db] = lambda: fake_db

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, fake_db

    app.dependency_overrides.clear()


def _synthetic_item() -> WorkQueueItemOut:
    return WorkQueueItemOut(
        source_type="task",
        source_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        subject_name="Aluna Sintetica",
        domain="onboarding",
        severity="high",
        preferred_shift="morning",
        reason="Acompanhamento sintetico",
        primary_action_label="Abrir contexto",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )


def _synthetic_envelope(*, include_item: bool = False) -> dict:
    return {
        "items": [_synthetic_item()] if include_item else [],
        "total": 1 if include_item else 0,
        "page": 1,
        "page_size": 25,
        "state_counts": {"do_now": 1 if include_item else 0, "awaiting_outcome": 0, "done": 0},
        "truncated_sources": [],
    }


def _synthetic_action_result() -> dict:
    return {
        "item": _synthetic_item(),
        "detail": "Resultado sintetico registrado.",
        "prepared_message": None,
        "context_path": "/tasks",
        "task_id": _synthetic_item().source_id,
        "supported": True,
    }


def test_wq_list_route_forwards_search_and_returns_exact_envelope(wq_client):
    client, _fake_db = wq_client
    service = MagicMock(return_value=_synthetic_envelope())

    with patch("app.routers.work_queue.list_work_queue_items", service):
        response = client.get(
            "/api/v1/work-queue/items",
            params={"q": "  ALVO  ", "page": 1, "page_size": 25},
        )

    assert response.status_code == 200
    assert service.call_args.kwargs.get("q") == "ALVO"
    assert service.call_args.kwargs["current_user"].gym_id == GYM_ID
    assert set(response.json()) == {
        "items",
        "total",
        "page",
        "page_size",
        "state_counts",
        "truncated_sources",
    }


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 0},
        {"page_size": 101},
    ],
)
def test_wq_list_route_rejects_invalid_pagination(wq_client, params):
    client, _fake_db = wq_client

    response = client.get("/api/v1/work-queue/items", params=params)

    assert response.status_code == 422


def test_wq_synthetic_smoke_uses_in_process_overrides_only(wq_client):
    client, fake_db = wq_client
    service = MagicMock(return_value=_synthetic_envelope(include_item=True))

    with patch("app.routers.work_queue.list_work_queue_items", service):
        response = client.get("/api/v1/work-queue/items", params={"q": "aluna", "page": 1, "page_size": 25})

    assert response.status_code == 200
    assert response.json() == {
        "items": [_synthetic_item().model_dump(mode="json")],
        "total": 1,
        "page": 1,
        "page_size": 25,
        "state_counts": {"do_now": 1, "awaiting_outcome": 0, "done": 0},
        "truncated_sources": [],
    }
    assert service.call_args.kwargs["current_user"].gym_id == GYM_ID
    fake_db.commit.assert_called_once()


def test_wq_outcome_route_rejects_naive_scheduled_for_with_clear_422(wq_client):
    client, _fake_db = wq_client
    service = MagicMock(return_value=_synthetic_action_result())

    with patch("app.routers.work_queue.update_work_queue_outcome", service):
        response = client.patch(
            f"/api/v1/work-queue/items/task/{_synthetic_item().source_id}/outcome",
            json={
                "outcome": "postponed",
                "snooze_preset": "custom",
                "scheduled_for": "2026-07-14T09:00:00",
            },
        )

    assert response.status_code == 422
    assert "fuso horario" in response.text.casefold()
    service.assert_not_called()


def test_wq_outcome_route_accepts_timezone_aware_scheduled_for(wq_client):
    client, _fake_db = wq_client
    service = MagicMock(return_value=_synthetic_action_result())

    with patch("app.routers.work_queue.update_work_queue_outcome", service):
        response = client.patch(
            f"/api/v1/work-queue/items/task/{_synthetic_item().source_id}/outcome",
            json={
                "outcome": "postponed",
                "snooze_preset": "custom",
                "scheduled_for": "2026-07-14T09:00:00-03:00",
            },
        )

    assert response.status_code == 200
    scheduled_for = service.call_args.kwargs["payload"].scheduled_for
    assert scheduled_for is not None
    assert scheduled_for.utcoffset() is not None
