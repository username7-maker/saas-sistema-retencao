from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers.nps import dispatch_nps_endpoint, get_nps_dispatch_status


def test_dispatch_nps_enqueues_job_and_returns_metadata(monkeypatch):
    request = MagicMock()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4(), gym_id=uuid4())
    job_id = uuid4()

    monkeypatch.setattr(
        "app.routers.nps.enqueue_nps_dispatch_job",
        lambda *_args, **_kwargs: (
            SimpleNamespace(id=job_id, job_type="nps_dispatch", status="pending"),
            True,
        ),
    )
    monkeypatch.setattr(
        "app.routers.nps.get_request_context",
        lambda *_args, **_kwargs: {"ip_address": "127.0.0.1", "user_agent": "pytest"},
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr(
        "app.routers.nps.log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    response = dispatch_nps_endpoint(request=request, db=db, current_user=current_user)

    assert response.job_id == job_id
    assert response.job_type == "nps_dispatch"
    assert response.status == "pending"
    assert response.message == "Disparo de NPS enfileirado."
    db.commit.assert_called_once()
    assert audit_calls[0]["action"] == "nps_dispatch_queued"


def test_get_nps_dispatch_status_returns_serialized_job(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(gym_id=uuid4())
    job_id = uuid4()
    job = SimpleNamespace(id=job_id, job_type="nps_dispatch")

    monkeypatch.setattr("app.routers.nps.get_core_async_job", lambda *_args, **_kwargs: job)
    monkeypatch.setattr(
        "app.routers.nps.serialize_core_async_job",
        lambda _job: {
            "job_id": job_id,
            "job_type": "nps_dispatch",
            "status": "completed",
            "attempt_count": 1,
            "max_attempts": 5,
            "next_retry_at": None,
            "started_at": None,
            "completed_at": None,
            "error_code": None,
            "error_message": None,
            "result": {"after_signup_7d": 1, "monthly": 2, "yellow_risk": 0, "post_cancellation": 0},
            "related_entity_type": "gym",
            "related_entity_id": current_user.gym_id,
        },
    )

    response = get_nps_dispatch_status(job_id=job_id, db=db, current_user=current_user)

    assert response.job_id == job_id
    assert response.status == "completed"
    assert response.result == {"after_signup_7d": 1, "monthly": 2, "yellow_risk": 0, "post_cancellation": 0}


def test_get_nps_dispatch_status_rejects_missing_or_wrong_type(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(gym_id=uuid4())
    job_id = uuid4()

    monkeypatch.setattr(
        "app.routers.nps.get_core_async_job",
        lambda *_args, **_kwargs: SimpleNamespace(id=job_id, job_type="monthly_reports_dispatch"),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_nps_dispatch_status(job_id=job_id, db=db, current_user=current_user)

    assert exc_info.value.status_code == 404
