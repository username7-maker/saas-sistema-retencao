from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers.sales import booking_status_endpoint, proposal_dispatch_status_endpoint


def test_proposal_dispatch_status_endpoint_scopes_lookup_to_current_user_gym(monkeypatch):
    lead_id = uuid4()
    job_id = uuid4()
    gym_id = uuid4()
    db = SimpleNamespace()
    current_user = SimpleNamespace(gym_id=gym_id)
    captured: dict[str, object] = {}
    job = SimpleNamespace(related_entity_type="lead", related_entity_id=lead_id)

    def _get_core_async_job(_db, *, job_id, gym_id):
        captured["job_id"] = job_id
        captured["gym_id"] = gym_id
        return job

    monkeypatch.setattr("app.routers.sales.get_core_async_job", _get_core_async_job)
    monkeypatch.setattr(
        "app.routers.sales.serialize_core_async_job",
        lambda _job: {
            "job_id": job_id,
            "job_type": "lead_proposal_dispatch",
            "status": "completed",
            "attempt_count": 1,
            "max_attempts": 5,
            "next_retry_at": None,
            "started_at": None,
            "completed_at": None,
            "error_code": None,
            "error_message": None,
            "result": {"ok": True},
            "related_entity_type": "lead",
            "related_entity_id": lead_id,
        },
    )

    result = proposal_dispatch_status_endpoint(
        lead_id=lead_id,
        job_id=job_id,
        db=db,
        current_user=current_user,
    )

    assert captured == {"job_id": job_id, "gym_id": gym_id}
    assert result.lead_id == lead_id
    assert result.job_id == job_id
    assert result.status == "completed"


def test_proposal_dispatch_status_endpoint_returns_404_for_lead_binding_mismatch(monkeypatch):
    lead_id = uuid4()
    job_id = uuid4()
    db = SimpleNamespace()
    current_user = SimpleNamespace(gym_id=uuid4())
    job = SimpleNamespace(related_entity_type="lead", related_entity_id=uuid4())

    monkeypatch.setattr("app.routers.sales.get_core_async_job", lambda *_args, **_kwargs: job)

    with pytest.raises(HTTPException) as exc:
        proposal_dispatch_status_endpoint(
            lead_id=lead_id,
            job_id=job_id,
            db=db,
            current_user=current_user,
        )

    assert exc.value.status_code == 404
    assert "Job de proposta nao encontrado" in exc.value.detail


def test_booking_status_endpoint_returns_booking_service_payload(monkeypatch):
    lead_id = uuid4()
    scheduled_for = "2026-04-20T10:00:00+00:00"

    monkeypatch.setattr(
        "app.routers.sales.get_booking_status",
        lambda _db, provided_lead_id: {
            "has_booking": True,
            "booking_id": uuid4(),
            "scheduled_for": scheduled_for,
            "status": "confirmed",
            "provider_name": "cal.com",
        }
        if provided_lead_id == lead_id
        else None,
    )

    result = booking_status_endpoint(
        lead_id=lead_id,
        db=SimpleNamespace(),
        _=SimpleNamespace(gym_id=uuid4()),
    )

    assert result.has_booking is True
    assert result.status == "confirmed"
    assert result.provider_name == "cal.com"
