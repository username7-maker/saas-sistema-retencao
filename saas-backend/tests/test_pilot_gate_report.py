import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pilot_gate_report.py"
_SPEC = importlib.util.spec_from_file_location("pilot_gate_report", _MODULE_PATH)
pilot_gate_report = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(pilot_gate_report)


def test_active_job_types_follow_pilot_flags(monkeypatch):
    monkeypatch.setenv("PUBLIC_DIAGNOSIS_ENABLED", "false")
    monkeypatch.setenv("MONTHLY_REPORTS_DISPATCH_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_PROPOSAL_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_PROPOSAL_EMAIL_ENABLED", "false")

    assert pilot_gate_report._active_internal_job_types() == ("nps_dispatch",)
    assert pilot_gate_report._active_external_provider_job_types() == ("whatsapp_webhook_setup",)


def test_active_job_types_expand_when_flags_are_enabled(monkeypatch):
    monkeypatch.setenv("PUBLIC_DIAGNOSIS_ENABLED", "true")
    monkeypatch.setenv("MONTHLY_REPORTS_DISPATCH_ENABLED", "true")
    monkeypatch.setenv("PUBLIC_PROPOSAL_ENABLED", "true")
    monkeypatch.setenv("PUBLIC_PROPOSAL_EMAIL_ENABLED", "false")

    assert pilot_gate_report._active_internal_job_types() == (
        "public_diagnosis",
        "nps_dispatch",
        "monthly_reports_dispatch",
    )
    assert pilot_gate_report._active_external_provider_job_types() == (
        "lead_proposal_dispatch",
        "whatsapp_webhook_setup",
    )
