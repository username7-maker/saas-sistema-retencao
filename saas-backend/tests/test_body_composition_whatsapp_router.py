import uuid
from datetime import datetime, timezone
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


def test_send_body_composition_summary_returns_dispatch_payload(authed_client):
    client, _fake_db = authed_client
    fake_log = SimpleNamespace(
        id=uuid.uuid4(),
        status="sent",
        recipient="5511999999999",
        error_detail=None,
        extra_data={"file_name": "bioimpedancia_erick_2026-03-30.pdf"},
        member_id=MEMBER_ID,
        lead_id=None,
        automation_rule_id=None,
        channel="whatsapp",
        template_name="body_composition_summary",
        content="Oi Erick",
        created_at=datetime.now(tz=timezone.utc),
        direction="outbound",
        event_type="body_composition_summary_pdf",
        provider_message_id=None,
    )
    with patch("app.routers.members.send_body_composition_whatsapp_summary", return_value=fake_log):
        response = client.post(f"/api/v1/members/{MEMBER_ID}/body-composition/{EVALUATION_ID}/send-whatsapp")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "sent"
    assert payload["pdf_filename"] == "bioimpedancia_erick_2026-03-30.pdf"


def test_send_body_composition_summary_returns_conflict_for_missing_phone(authed_client):
    client, _fake_db = authed_client
    with patch("app.routers.members.send_body_composition_whatsapp_summary", side_effect=ValueError("Aluno sem telefone cadastrado")):
        response = client.post(f"/api/v1/members/{MEMBER_ID}/body-composition/{EVALUATION_ID}/send-whatsapp")

    assert response.status_code == 409
    assert response.json()["detail"] == "Aluno sem telefone cadastrado"
