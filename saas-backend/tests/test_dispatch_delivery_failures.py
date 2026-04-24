from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.call_script_service import execute_lead_proposal_dispatch_job
from app.services.core_async_job_service import CoreAsyncJobNonRetryableError
from app.services.report_service import execute_monthly_reports_dispatch_job, send_monthly_reports
from app.utils.email import EmailSendResult


def test_send_monthly_reports_exposes_blocked_delivery_metadata(monkeypatch):
    monkeypatch.setattr(
        "app.services.report_service.generate_dashboard_pdf",
        lambda *_args, **_kwargs: (SimpleNamespace(getvalue=lambda: b"%PDF-1.4 monthly"), "report_consolidated.pdf"),
    )
    monkeypatch.setattr(
        "app.services.report_service.send_email_with_attachment_result",
        lambda *args, **kwargs: EmailSendResult(sent=False, blocked=True, reason="sendgrid_permission_denied"),
    )

    leadership = [SimpleNamespace(email="owner@teste.com"), SimpleNamespace(email="manager@teste.com")]
    db = MagicMock()
    db.scalars.return_value.all.return_value = leadership

    result = send_monthly_reports(db)

    assert result["sent"] == 0
    assert result["failed"] == 2
    assert result["blocked"] == 2
    assert result["blocked_reasons"] == {"sendgrid_permission_denied": 2}
    assert result["total_recipients"] == 2


def test_execute_monthly_reports_dispatch_job_raises_when_no_email_is_delivered(monkeypatch):
    monkeypatch.setattr(
        "app.services.report_service.send_monthly_reports",
        lambda *_args, **_kwargs: {
            "sent": 0,
            "failed": 2,
            "blocked": 2,
            "blocked_reasons": {"sendgrid_permission_denied": 2},
            "total_recipients": 2,
        },
    )

    db = SimpleNamespace(get=lambda *_args, **_kwargs: SimpleNamespace(id="user-1"), flush=lambda: None)

    with pytest.raises(CoreAsyncJobNonRetryableError) as exc_info:
        execute_monthly_reports_dispatch_job(
            db,
            gym_id="gym-1",
            job_id="job-1",
            requested_by_user_id="user-1",
        )

    assert exc_info.value.code == "sendgrid_permission_denied"


def test_execute_lead_proposal_dispatch_job_raises_when_email_is_not_sent(monkeypatch):
    lead = SimpleNamespace(id="lead-1", gym_id="gym-1", deleted_at=None, email="lead@teste.com", notes=[])
    db = MagicMock()
    db.get.return_value = lead

    monkeypatch.setattr(
        "app.services.call_script_service.generate_and_send_for_lead",
        lambda *_args, **_kwargs: {
            "job_id": "job-1",
            "lead_id": "lead-1",
            "filename": "proposal.pdf",
            "emailed": False,
            "email_error_code": "sendgrid_permission_denied",
            "whatsapp_status": None,
        },
    )

    with pytest.raises(CoreAsyncJobNonRetryableError) as exc_info:
        execute_lead_proposal_dispatch_job(db, lead_id="lead-1", job_id="job-1")

    assert exc_info.value.code == "sendgrid_permission_denied"
