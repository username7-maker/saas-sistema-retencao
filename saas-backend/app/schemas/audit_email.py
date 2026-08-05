"""Narrow email escape hatch for the isolated audit sandbox.

RFC-reserved ``.invalid`` addresses are intentionally rejected by EmailStr.
The audit harness needs those addresses so it can prove no deliverable address
or real account is ever used.  The exception below is double-gated and accepts
only the dedicated TESTE_AUDITORIA namespace.
"""

from __future__ import annotations

import os
import re
from typing import Annotated

from pydantic import BeforeValidator, EmailStr, TypeAdapter, WithJsonSchema


_EMAIL_ADAPTER = TypeAdapter(EmailStr)
_AUDIT_EMAIL = re.compile(
    r"^TESTE_AUDITORIA_[A-Z0-9_.+\-]+@teste-auditoria\.invalid$",
    re.IGNORECASE,
)


def _audit_reserved_emails_enabled() -> bool:
    return (
        os.getenv("ENVIRONMENT", "").strip().lower() == "audit"
        and os.getenv("AUDIT_ALLOW_RESERVED_EMAILS", "").strip().lower() == "true"
    )


def validate_audit_safe_email(value: object) -> str:
    raw = str(value).strip()
    if _audit_reserved_emails_enabled() and _AUDIT_EMAIL.fullmatch(raw):
        return raw
    return str(_EMAIL_ADAPTER.validate_python(raw))


AuditSafeEmail = Annotated[
    str,
    BeforeValidator(validate_audit_safe_email),
    WithJsonSchema({"type": "string", "format": "email"}),
]
