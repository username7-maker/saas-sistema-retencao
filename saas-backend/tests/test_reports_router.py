from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.routers.reports import dispatch_monthly_reports, get_monthly_dispatch_status


def test_dispatch_monthly_reports_is_blocked_when_disabled():
    with patch("app.routers.reports.settings.monthly_reports_dispatch_enabled", False):
        with pytest.raises(HTTPException) as exc_info:
            dispatch_monthly_reports(
                request=MagicMock(),
                db=MagicMock(),
                current_user=SimpleNamespace(),
            )

    assert exc_info.value.status_code == 503


def test_dispatch_monthly_reports_enqueues_job_and_returns_metadata(monkeypatch):
    request = MagicMock()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4(), gym_id=uuid4())
    job_id = uuid4()

    monkeypatch.setattr("app.routers.reports.settings.monthly_reports_dispatch_enabled", True)
    monkeypatch.setattr(
        "app.routers.reports.enqueue_monthly_reports_dispatch_job",
        lambda *_args, **_kwargs: (
            SimpleNamespace(id=job_id, job_type="monthly_reports_dispatch", status="pending"),
            True,
        ),
    )
    monkeypatch.setattr(
        "app.routers.reports.get_request_context",
        lambda *_args, **_kwargs: {"ip_address": "127.0.0.1", "user_agent": "pytest"},
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr(
        "app.routers.reports.log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    response = dispatch_monthly_reports(request=request, db=db, current_user=current_user)

    assert response.job_id == job_id
    assert response.job_type == "monthly_reports_dispatch"
    assert response.status == "pending"
    assert response.message == "Disparo mensal enfileirado."
    db.commit.assert_called_once()
    assert audit_calls[0]["action"] == "monthly_reports_dispatch_queued"


def test_get_monthly_dispatch_status_returns_serialized_job(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(gym_id=uuid4())
    job_id = uuid4()
    job = SimpleNamespace(id=job_id, job_type="monthly_reports_dispatch")

    monkeypatch.setattr("app.routers.reports.get_core_async_job", lambda *_args, **_kwargs: job)
    monkeypatch.setattr(
        "app.routers.reports.serialize_core_async_job",
        lambda _job: {
            "job_id": job_id,
            "job_type": "monthly_reports_dispatch",
            "status": "completed",
            "attempt_count": 1,
            "max_attempts": 5,
            "next_retry_at": None,
            "started_at": None,
            "completed_at": None,
            "error_code": None,
            "error_message": None,
            "result": {"sent": 2, "failed": 0},
            "related_entity_type": "gym",
            "related_entity_id": current_user.gym_id,
        },
    )

    response = get_monthly_dispatch_status(job_id=job_id, db=db, current_user=current_user)

    assert response.job_id == job_id
    assert response.status == "completed"
    assert response.result == {"sent": 2, "failed": 0}


def test_get_monthly_dispatch_status_rejects_missing_or_wrong_type(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(gym_id=uuid4())
    job_id = uuid4()

    monkeypatch.setattr(
        "app.routers.reports.get_core_async_job",
        lambda *_args, **_kwargs: SimpleNamespace(id=job_id, job_type="public_diagnosis"),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_monthly_dispatch_status(job_id=job_id, db=db, current_user=current_user)

    assert exc_info.value.status_code == 404
