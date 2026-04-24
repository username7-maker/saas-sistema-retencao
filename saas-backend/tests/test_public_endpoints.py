from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4
from unittest.mock import MagicMock

from app.database import get_db


def _override_db(app, db):
    app.dependency_overrides[get_db] = lambda: db


def test_public_booking_confirm_rate_limit(app, client, monkeypatch):
    app.state.limiter.reset()
    db = MagicMock()
    _override_db(app, db)
    monkeypatch.setattr("app.routers.public.settings.public_booking_confirm_enabled", True)
    monkeypatch.setattr("app.routers.public.settings.public_booking_confirm_token", "booking-secret")
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
            response = client.post(
                "/api/v1/public/booking/confirm",
                json=payload,
                headers={"X-Public-Booking-Token": "booking-secret"},
            )
            statuses.append(response.status_code)
            if response.status_code == 429:
                break
    finally:
        app.dependency_overrides.clear()

    assert 429 in statuses


def test_public_diagnostico_rate_limit_still_applies(app, client, monkeypatch):
    app.state.limiter.reset()
    db = MagicMock()
    _override_db(app, db)
    monkeypatch.setattr("app.routers.public.settings.public_diagnosis_enabled", True)
    monkeypatch.setattr("app.routers.public.resolve_public_gym_id", lambda: UUID("11111111-1111-1111-1111-111111111111"))
    monkeypatch.setattr("app.routers.public.create_public_diagnosis_lead", lambda *_args, **_kwargs: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(
        "app.routers.public.enqueue_public_diagnosis_job",
        lambda *_args, diagnosis_id, **_kwargs: SimpleNamespace(id=diagnosis_id, status="pending"),
    )

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


def test_public_diagnostico_returns_job_metadata(app, client, monkeypatch):
    app.state.limiter.reset()
    db = MagicMock()
    _override_db(app, db)
    public_gym_id = UUID("11111111-1111-1111-1111-111111111111")
    lead_id = uuid4()
    diagnosis_id = uuid4()
    monkeypatch.setattr("app.routers.public.settings.public_diagnosis_enabled", True)
    monkeypatch.setattr("app.routers.public.resolve_public_gym_id", lambda: public_gym_id)
    monkeypatch.setattr("app.routers.public.new_diagnosis_id", lambda: diagnosis_id)
    monkeypatch.setattr("app.routers.public.create_public_diagnosis_lead", lambda *_args, **_kwargs: SimpleNamespace(id=lead_id))
    monkeypatch.setattr(
        "app.routers.public.enqueue_public_diagnosis_job",
        lambda *_args, **_kwargs: SimpleNamespace(id=diagnosis_id, status="pending"),
    )

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
        response = client.post("/api/v1/public/diagnostico", data=form, files=files)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["diagnosis_id"] == str(diagnosis_id)
    assert body["job_id"] == str(diagnosis_id)
    assert body["lead_id"] == str(lead_id)
    assert body["status"] == "pending"


def test_public_diagnostico_status_returns_serialized_job(app, client, monkeypatch):
    app.state.limiter.reset()
    db = MagicMock()
    _override_db(app, db)
    public_gym_id = UUID("11111111-1111-1111-1111-111111111111")
    diagnosis_id = uuid4()
    lead_id = uuid4()
    monkeypatch.setattr("app.routers.public.resolve_public_gym_id", lambda: public_gym_id)
    monkeypatch.setattr(
        "app.routers.public.get_public_diagnosis_job",
        lambda *_args, **_kwargs: SimpleNamespace(id=diagnosis_id, status="completed"),
    )
    monkeypatch.setattr(
        "app.routers.public.serialize_core_async_job",
        lambda _job: {
            "job_id": diagnosis_id,
            "job_type": "public_diagnosis",
            "status": "completed",
            "attempt_count": 1,
            "max_attempts": 5,
            "next_retry_at": None,
            "started_at": None,
            "completed_at": None,
            "error_code": None,
            "error_message": None,
            "result": {"diagnosis_id": str(diagnosis_id)},
            "related_entity_type": "lead",
            "related_entity_id": lead_id,
        },
    )

    try:
        response = client.get(f"/api/v1/public/diagnostico/{diagnosis_id}/status", params={"lead_id": str(lead_id)})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["diagnosis_id"] == str(diagnosis_id)
    assert body["lead_id"] == str(lead_id)
    assert body["status"] == "completed"


def test_public_diagnostico_status_returns_404_when_lead_binding_does_not_match(app, client, monkeypatch):
    app.state.limiter.reset()
    db = MagicMock()
    _override_db(app, db)
    public_gym_id = UUID("11111111-1111-1111-1111-111111111111")
    monkeypatch.setattr("app.routers.public.resolve_public_gym_id", lambda: public_gym_id)
    monkeypatch.setattr("app.routers.public.get_public_diagnosis_job", lambda *_args, **_kwargs: None)

    try:
        response = client.get(f"/api/v1/public/diagnostico/{uuid4()}/status", params={"lead_id": str(uuid4())})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "Diagnostico nao encontrado" in response.json()["detail"]


def test_public_diagnostico_returns_503_when_disabled(app, client):
    app.state.limiter.reset()
    form = {
        "full_name": "Academia Teste",
        "email": "owner@example.com",
        "whatsapp": "11999999999",
        "gym_name": "Academia Teste",
        "total_members": "120",
        "avg_monthly_fee": "149.90",
    }
    files = {"csv_file": ("checkins.csv", b"member_id,checkin_at\n1,2026-03-20T10:00:00Z\n", "text/csv")}
    response = client.post("/api/v1/public/diagnostico", data=form, files=files)
    assert response.status_code == 503
    assert "temporariamente desabilitado" in response.json()["detail"]


def test_public_booking_confirm_returns_503_when_disabled(app, client):
    app.state.limiter.reset()
    payload = {
        "prospect_name": "Lead Teste",
        "email": "lead@example.com",
        "whatsapp": "11999999999",
        "scheduled_for": (datetime.now(tz=timezone.utc) + timedelta(days=1)).isoformat(),
        "provider_name": "cal.com",
        "metadata": {},
    }
    response = client.post("/api/v1/public/booking/confirm", json=payload)
    assert response.status_code == 503
    assert "temporariamente desabilitado" in response.json()["detail"]


def test_public_booking_confirm_requires_shared_token(app, client, monkeypatch):
    app.state.limiter.reset()
    db = MagicMock()
    _override_db(app, db)
    monkeypatch.setattr("app.routers.public.settings.public_booking_confirm_enabled", True)
    monkeypatch.setattr("app.routers.public.settings.public_booking_confirm_token", "booking-secret")
    payload = {
        "prospect_name": "Lead Teste",
        "email": "lead@example.com",
        "whatsapp": "11999999999",
        "scheduled_for": (datetime.now(tz=timezone.utc) + timedelta(days=1)).isoformat(),
        "provider_name": "cal.com",
        "metadata": {},
    }
    try:
        response = client.post("/api/v1/public/booking/confirm", json=payload)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401


def test_public_proposal_does_not_hydrate_from_lead_or_send_email_by_default(app, client, monkeypatch):
    app.state.limiter.reset()
    db = MagicMock()
    _override_db(app, db)
    monkeypatch.setattr("app.routers.public.settings.public_proposal_enabled", True)

    calls: dict[str, object] = {}

    def _hydrate(_db, payload, *, allow_lead_lookup=False):
        calls["allow_lead_lookup"] = allow_lead_lookup
        return payload

    monkeypatch.setattr("app.routers.public.hydrate_proposal_from_lead", _hydrate)
    monkeypatch.setattr("app.routers.public.generate_proposal_pdf", lambda payload: (b"pdf", "proposal.pdf"))
    monkeypatch.setattr(
        "app.routers.public.send_proposal_email_if_needed",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("nao deveria enviar email publico por padrao")),
    )

    payload = {
        "lead_id": str(uuid4()),
        "prospect_name": "Lead Teste",
        "gym_name": "Academia Teste",
        "total_members": 200,
        "avg_monthly_fee": "149.90",
        "diagnosed_red": 10,
        "diagnosed_yellow": 20,
        "email": "lead@example.com",
    }

    try:
        response = client.post("/api/v1/public/proposal", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls["allow_lead_lookup"] is False


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
