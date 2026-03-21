"""Testes do endpoint POST /automations/whatsapp/send."""
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
    fake_db.scalar.return_value = 0

    app.dependency_overrides[get_current_user] = lambda: fake_owner
    app.dependency_overrides[get_db] = lambda: fake_db

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, fake_db

    app.dependency_overrides.clear()


def test_manual_send_uses_gym_instance(authed_client):
    client, fake_db = authed_client
    fake_db.get.return_value = SimpleNamespace(
        id=GYM_ID,
        whatsapp_instance="gym_xyz789",
        whatsapp_status="connected",
    )
    fake_log = SimpleNamespace(
        id=uuid.uuid4(),
        status="sent",
        channel="whatsapp",
        recipient="5511999990001",
        content="Oi",
        created_at=datetime.now(tz=timezone.utc),
        direction="outbound",
        event_type=None,
        template_name=None,
        extra_data={},
        member_id=None,
        lead_id=None,
        automation_rule_id=None,
        error_detail=None,
        provider_message_id=None,
    )
    with patch("app.routers.automations.send_whatsapp_sync", return_value=fake_log) as mock_send:
        response = client.post(
            "/api/v1/automations/whatsapp/send",
            json={"phone": "11999990001", "message": "Oi"},
        )

    assert response.status_code == 200
    assert mock_send.call_args.kwargs["instance"] == "gym_xyz789"


def test_manual_send_skipped_without_connected_instance(authed_client):
    client, fake_db = authed_client
    fake_db.get.return_value = SimpleNamespace(
        id=GYM_ID,
        whatsapp_instance=None,
        whatsapp_status="disconnected",
    )
    fake_log = SimpleNamespace(
        id=uuid.uuid4(),
        status="skipped",
        channel="whatsapp",
        recipient="5511999990001",
        content="Oi",
        created_at=datetime.now(tz=timezone.utc),
        direction="outbound",
        event_type=None,
        template_name=None,
        extra_data={"instance_source": "none", "instance_used": None},
        member_id=None,
        lead_id=None,
        automation_rule_id=None,
        error_detail="not configured or not connected",
        provider_message_id=None,
    )
    with patch("app.routers.automations.send_whatsapp_sync", return_value=fake_log):
        response = client.post(
            "/api/v1/automations/whatsapp/send",
            json={"phone": "11999990001", "message": "Oi"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
