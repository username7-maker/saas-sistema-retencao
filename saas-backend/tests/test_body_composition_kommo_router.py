import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EVALUATION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


@pytest.fixture
def authed_client(app):
    fake_owner = SimpleNamespace(
        id=uuid.uuid4(),
        gym_id=GYM_ID,
        role=RoleEnum.OWNER,
        is_active=True,
        deleted_at=None,
        full_name="Owner Teste",
        email="owner@teste.com",
    )
    fake_db = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: fake_owner
    app.dependency_overrides[get_db] = lambda: fake_db

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, fake_db

    app.dependency_overrides.clear()


def test_send_body_composition_kommo_returns_dispatch_payload(authed_client):
    client, _fake_db = authed_client
    fake_handoff = SimpleNamespace(
        status="sent",
        lead_id="12345",
        contact_id="67890",
        task_id="54321",
        detail="Handoff entregue para a Kommo.",
    )
    with patch("app.routers.members.send_body_composition_kommo_handoff", return_value=fake_handoff):
        response = client.post(f"/api/v1/members/{MEMBER_ID}/body-composition/{EVALUATION_ID}/send-kommo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "sent"
    assert payload["lead_id"] == "12345"
    assert payload["task_id"] == "54321"


def test_send_body_composition_kommo_returns_conflict_for_operational_issue(authed_client):
    client, _fake_db = authed_client
    with patch("app.routers.members.send_body_composition_kommo_handoff", side_effect=ValueError("Kommo nao configurada")):
        response = client.post(f"/api/v1/members/{MEMBER_ID}/body-composition/{EVALUATION_ID}/send-kommo")

    assert response.status_code == 409
    assert response.json()["detail"] == "Kommo nao configurada"
