import uuid
from datetime import date, datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import MemberStatus, RiskLevel, RoleEnum


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


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


def test_export_member_route_passes_current_gym_id(authed_client):
    client, fake_db = authed_client
    with patch(
        "app.routers.lgpd.export_member_pdf",
        return_value=(BytesIO(b"%PDF-1.4"), "lgpd-test.pdf"),
    ) as mock_export:
        response = client.get(f"/api/v1/lgpd/export/member/{MEMBER_ID}")

    assert response.status_code == 200
    assert mock_export.call_args.args[1] == MEMBER_ID
    assert mock_export.call_args.args[2] == GYM_ID
    fake_db.commit.assert_called_once()


def test_anonymize_member_route_passes_current_gym_id(authed_client):
    client, fake_db = authed_client
    anonymized_member = SimpleNamespace(
        id=MEMBER_ID,
        gym_id=GYM_ID,
        full_name="anon-33333333",
        email=None,
        phone=None,
        status=MemberStatus.CANCELLED,
        plan_name="Gold",
        monthly_fee=99.90,
        join_date=date(2026, 4, 1),
        cancellation_date=None,
        preferred_shift=None,
        nps_last_score=7,
        loyalty_months=1,
        risk_score=0,
        risk_level=RiskLevel.GREEN,
        last_checkin_at=None,
        extra_data={"anonymized_at": "2026-04-16T00:00:00+00:00"},
        onboarding_score=0,
        onboarding_status="active",
        churn_type=None,
        is_vip=False,
        retention_stage=None,
        assigned_user_id=None,
        birthdate=None,
        cpf_encrypted=None,
        deleted_at=datetime(2026, 4, 16, tzinfo=timezone.utc),
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 16, tzinfo=timezone.utc),
    )

    with patch("app.routers.lgpd.anonymize_member", return_value=anonymized_member) as mock_anonymize:
        response = client.post(f"/api/v1/lgpd/anonymize/member/{MEMBER_ID}")

    assert response.status_code == 200
    assert mock_anonymize.call_args.args[1] == MEMBER_ID
    assert mock_anonymize.call_args.args[2] == GYM_ID
    fake_db.commit.assert_called_once()
