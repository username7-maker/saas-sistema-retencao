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
