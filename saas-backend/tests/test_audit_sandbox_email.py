from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schemas.audit_email import AuditSafeEmail


AUDIT_EMAIL = "TESTE_AUDITORIA_GESTOR@teste-auditoria.invalid"


def test_reserved_audit_email_is_rejected_without_both_runtime_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "audit")
    monkeypatch.delenv("AUDIT_ALLOW_RESERVED_EMAILS", raising=False)

    with pytest.raises(ValidationError):
        TypeAdapter(AuditSafeEmail).validate_python(AUDIT_EMAIL)


def test_reserved_audit_email_is_accepted_only_in_isolated_audit_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "audit")
    monkeypatch.setenv("AUDIT_ALLOW_RESERVED_EMAILS", "true")

    assert TypeAdapter(AuditSafeEmail).validate_python(AUDIT_EMAIL) == AUDIT_EMAIL


def test_other_invalid_domains_remain_rejected_in_audit_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "audit")
    monkeypatch.setenv("AUDIT_ALLOW_RESERVED_EMAILS", "true")

    with pytest.raises(ValidationError):
        TypeAdapter(AuditSafeEmail).validate_python("gestor@outro.invalid")


def test_normal_deliverable_email_keeps_standard_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("AUDIT_ALLOW_RESERVED_EMAILS", raising=False)

    assert TypeAdapter(AuditSafeEmail).validate_python("gestor@example.com") == "gestor@example.com"
