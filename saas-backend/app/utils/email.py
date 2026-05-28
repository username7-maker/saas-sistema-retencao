import logging
from base64 import b64encode
from dataclasses import dataclass

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)
RESEND_EMAILS_URL = "https://api.resend.com/emails"


@dataclass(frozen=True)
class EmailSendResult:
    sent: bool
    blocked: bool = False
    reason: str | None = None


_email_provider_block_reason: str | None = None


def _extract_resend_error_text(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text
    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("error")
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            return f"{message or ''} {errors}".strip()
        return str(message or payload)
    return str(payload)


def _classify_resend_response(response: httpx.Response) -> EmailSendResult:
    body_text = _extract_resend_error_text(response)
    normalized = body_text.lower()
    if any(fragment in normalized for fragment in ("domain is not verified", "verify a domain", "verified domain", "sender identity")):
        return EmailSendResult(sent=False, blocked=True, reason="sender_identity_unverified")
    if response.status_code in {401, 403}:
        return EmailSendResult(sent=False, blocked=True, reason="resend_permission_denied")
    if response.status_code == 429:
        return EmailSendResult(sent=False, blocked=False, reason="resend_rate_limited")
    if response.status_code in {400, 422}:
        return EmailSendResult(sent=False, blocked=False, reason="resend_validation_error")
    return EmailSendResult(sent=False, blocked=False, reason="resend_http_error")


def _record_blocked_reason(reason: str) -> None:
    global _email_provider_block_reason
    if _email_provider_block_reason == reason:
        return
    _email_provider_block_reason = reason
    logger.error("Envio de email bloqueado por configuracao do provedor: %s", reason, extra={"reason": reason})


def _resend_payload(to_email: str, subject: str, content: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "from": settings.resend_sender,
        "to": [to_email],
        "subject": subject,
        "text": content,
    }
    if settings.resend_reply_to.strip():
        payload["reply_to"] = settings.resend_reply_to.strip()
    return payload


def _send_resend_payload(payload: dict[str, object]) -> EmailSendResult:
    if not settings.resend_api_key.strip():
        return EmailSendResult(sent=False, blocked=True, reason="resend_api_key_missing")
    if _email_provider_block_reason:
        return EmailSendResult(sent=False, blocked=True, reason=_email_provider_block_reason)

    try:
        response = httpx.post(
            RESEND_EMAILS_URL,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.email_timeout_seconds,
        )
        if 200 <= response.status_code < 300:
            return EmailSendResult(sent=True, blocked=False, reason="sent")
        result = _classify_resend_response(response)
        if result.blocked and result.reason:
            _record_blocked_reason(result.reason)
            logger.warning(
                "Resend recusou o envio de email: %s",
                result.reason,
                extra={
                    "status_code": response.status_code,
                    "reason": result.reason,
                    "from_email": settings.resend_sender,
                },
            )
        else:
            logger.error(
                "Falha ao enviar email via Resend: %s",
                result.reason,
                extra={"status_code": response.status_code, "reason": result.reason},
            )
        return result
    except httpx.TimeoutException:
        logger.exception("Timeout ao enviar email via Resend")
        return EmailSendResult(sent=False, blocked=False, reason="resend_timeout")
    except httpx.HTTPError:
        logger.exception("Falha de rede ao enviar email via Resend")
        return EmailSendResult(sent=False, blocked=False, reason="resend_request_failed")
    except Exception:
        logger.exception("Falha inesperada ao enviar email via Resend")
        return EmailSendResult(sent=False, blocked=False, reason="unexpected_error")


def send_email_result(to_email: str, subject: str, content: str) -> EmailSendResult:
    return _send_resend_payload(_resend_payload(to_email, subject, content))


def send_email(to_email: str, subject: str, content: str) -> bool:
    return send_email_result(to_email, subject, content).sent


def send_email_with_attachment_result(
    to_email: str,
    subject: str,
    content: str,
    *,
    filename: str,
    attachment_bytes: bytes,
    mime_type: str = "application/pdf",
) -> EmailSendResult:
    payload = _resend_payload(to_email, subject, content)
    payload["attachments"] = [
        {
            "filename": filename,
            "content": b64encode(attachment_bytes).decode("utf-8"),
        }
    ]
    return _send_resend_payload(payload)


def send_email_with_attachment(
    to_email: str,
    subject: str,
    content: str,
    *,
    filename: str,
    attachment_bytes: bytes,
    mime_type: str = "application/pdf",
) -> bool:
    return send_email_with_attachment_result(
        to_email,
        subject,
        content,
        filename=filename,
        attachment_bytes=attachment_bytes,
        mime_type=mime_type,
    ).sent
