from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4
from unittest.mock import MagicMock

from app.database import get_db


def _override_db(app, db):
    app.dependency_overrides[get_db] = lambda: db


def test_public_booking_confirm_rate_limit(app, client, monkeypatch):
    db = MagicMock()
    _override_db(app, db)
    monkeypatch.setattr(
        "app.routers.public.confirm_public_booking",
        lambda *_args, **_kwargs: (
            SimpleNamespace(id=uuid4()),
            SimpleNamespace(id=uuid4()),
        ),
    )

    payload = {
        "prospect_name": "Lead Teste",
        "email": "lead@example.com",
        "whatsapp": "11999999999",
        "scheduled_for": (datetime.now(tz=timezone.utc) + timedelta(days=1)).isoformat(),
        "provider_name": "cal.com",
        "metadata": {},
    }

    try:
        statuses = []
        for _ in range(12):
            response = client.post("/api/v1/public/booking/confirm", json=payload)
            statuses.append(response.status_code)
            if response.status_code == 429:
                break
    finally:
        app.dependency_overrides.clear()

    assert 429 in statuses


def test_public_diagnostico_rate_limit_still_applies(app, client, monkeypatch):
    db = MagicMock()
    _override_db(app, db)
    monkeypatch.setattr("app.routers.public.resolve_public_gym_id", lambda: UUID("11111111-1111-1111-1111-111111111111"))
    monkeypatch.setattr("app.routers.public.process_public_diagnosis_background", lambda **_kwargs: None)
    monkeypatch.setattr("app.routers.public.create_public_diagnosis_lead", lambda *_args, **_kwargs: SimpleNamespace(id=uuid4()))

    form = {
        "full_name": "Academia Teste",
        "email": "owner@example.com",
        "whatsapp": "11999999999",
        "gym_name": "Academia Teste",
        "total_members": "120",
        "avg_monthly_fee": "149.90",
    }
    files = {"csv_file": ("checkins.csv", b"member_id,checkin_at\n1,2026-03-20T10:00:00Z\n", "text/csv")}

    try:
        statuses = []
        for _ in range(7):
            response = client.post("/api/v1/public/diagnostico", data=form, files=files)
            statuses.append(response.status_code)
            if response.status_code == 429:
                break
    finally:
        app.dependency_overrides.clear()

    assert 429 in statuses


def test_public_proposal_returns_503_when_disabled(app, client):
    payload = {
        "prospect_name": "Lead Teste",
        "gym_name": "Academia Teste",
        "total_members": 200,
        "avg_monthly_fee": "149.90",
        "diagnosed_red": 10,
        "diagnosed_yellow": 20,
        "email": "lead@example.com",
    }
    response = client.post("/api/v1/public/proposal", json=payload)
    assert response.status_code == 503
    assert "temporariamente desabilitado" in response.json()["detail"]


def test_public_objection_response_returns_503_when_disabled(app, client):
    response = client.post("/api/v1/public/objection-response", json={"message_text": "esta caro"})
    assert response.status_code == 503
    assert "temporariamente desabilitado" in response.json()["detail"]


def test_public_proposal_invalid_payload_returns_422(app, client):
    response = client.post("/api/v1/public/proposal", json={"prospect_name": "Lead Incompleto"})
    assert response.status_code == 422
