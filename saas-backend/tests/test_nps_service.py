from types import SimpleNamespace

from app.models import NPSTrigger
from app.services import nps_service


def _member() -> SimpleNamespace:
    return SimpleNamespace(id="member-1", email="member@test.com", full_name="Aluno Teste")


def test_send_nps_email_logs_audit_on_success(monkeypatch):
    logs = []
    monkeypatch.setattr(nps_service, "send_email", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(nps_service, "log_audit_event", lambda *_args, **kwargs: logs.append(kwargs["action"]))

    sent = nps_service._send_nps_email(SimpleNamespace(), _member(), NPSTrigger.MONTHLY)

    assert sent is True
    assert logs == ["nps_sent_monthly"]


def test_send_nps_email_skips_audit_on_failure(monkeypatch):
    logs = []
    monkeypatch.setattr(nps_service, "send_email", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(nps_service, "log_audit_event", lambda *_args, **kwargs: logs.append(kwargs["action"]))

    sent = nps_service._send_nps_email(SimpleNamespace(), _member(), NPSTrigger.MONTHLY)

    assert sent is False
    assert logs == []


def test_execute_nps_dispatch_job_logs_completion_without_commit(monkeypatch):
    audit_calls = []
    monkeypatch.setattr(
        nps_service,
        "run_nps_dispatch",
        lambda *_args, **_kwargs: {"after_signup_7d": 1, "monthly": 2, "yellow_risk": 0, "post_cancellation": 0},
    )
    monkeypatch.setattr(
        nps_service,
        "log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    db = SimpleNamespace(get=lambda *_args, **_kwargs: SimpleNamespace(id="user-1"), flush=lambda: None)
    result = nps_service.execute_nps_dispatch_job(
        db,
        gym_id="gym-1",
        job_id="job-1",
        requested_by_user_id="user-1",
    )

    assert result["monthly"] == 2
    assert audit_calls[0]["action"] == "nps_dispatch_completed"
