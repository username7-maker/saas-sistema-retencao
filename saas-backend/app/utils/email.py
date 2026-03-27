import logging
from base64 import b64encode
from dataclasses import dataclass

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Attachment, Disposition, FileContent, FileName, FileType, Mail
from python_http_client.exceptions import HTTPError

from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailSendResult:
    sent: bool
    blocked: bool = False
    reason: str | None = None


_sendgrid_block_reason: str | None = None


def _decode_error_body(error: HTTPError) -> str:
    body = getattr(error, "body", b"")
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return str(body)


def _classify_sendgrid_http_error(error: HTTPError) -> EmailSendResult:
    body_text = _decode_error_body(error)
    normalized = f"{getattr(error, 'reason', '')} {body_text}".lower()
    if "verified sender identity" in normalized:
        return EmailSendResult(sent=False, blocked=True, reason="sender_identity_unverified")
    if "permission" in normalized or getattr(error, "status_code", None) == 401:
        return EmailSendResult(sent=False, blocked=True, reason="sendgrid_permission_denied")
    return EmailSendResult(sent=False, blocked=False, reason="sendgrid_http_error")


def _record_blocked_reason(reason: str) -> None:
    global _sendgrid_block_reason
    if _sendgrid_block_reason == reason:
        return
    _sendgrid_block_reason = reason
    logger.error("Envio de email bloqueado por configuracao do SendGrid.", extra={"reason": reason})


def send_email_result(to_email: str, subject: str, content: str) -> EmailSendResult:
    if not settings.sendgrid_api_key:
        return EmailSendResult(sent=False, blocked=True, reason="sendgrid_api_key_missing")
    if _sendgrid_block_reason:
        return EmailSendResult(sent=False, blocked=True, reason=_sendgrid_block_reason)

    try:
        message = Mail(
            from_email=settings.sendgrid_sender,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content,
        )
        client = SendGridAPIClient(settings.sendgrid_api_key)
        response = client.send(message)
        return EmailSendResult(sent=200 <= response.status_code < 300)
    except HTTPError as exc:
        result = _classify_sendgrid_http_error(exc)
        if result.blocked and result.reason:
            _record_blocked_reason(result.reason)
            logger.warning(
                "SendGrid recusou o envio de email.",
                extra={
                    "status_code": getattr(exc, "status_code", None),
                    "reason": result.reason,
                    "from_email": settings.sendgrid_sender,
                },
            )
        else:
            logger.exception("Falha ao enviar email via SendGrid")
        return result
    except Exception:
        logger.exception("Falha ao enviar email via SendGrid")
        return EmailSendResult(sent=False, blocked=False, reason="unexpected_error")


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
    if not settings.sendgrid_api_key:
        return EmailSendResult(sent=False, blocked=True, reason="sendgrid_api_key_missing")
    if _sendgrid_block_reason:
        return EmailSendResult(sent=False, blocked=True, reason=_sendgrid_block_reason)

    try:
        message = Mail(
            from_email=settings.sendgrid_sender,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content,
        )
        encoded = b64encode(attachment_bytes).decode("utf-8")
        message.attachment = Attachment(
            file_content=FileContent(encoded),
            file_type=FileType(mime_type),
            file_name=FileName(filename),
            disposition=Disposition("attachment"),
        )
        client = SendGridAPIClient(settings.sendgrid_api_key)
        response = client.send(message)
        return EmailSendResult(sent=200 <= response.status_code < 300)
    except HTTPError as exc:
        result = _classify_sendgrid_http_error(exc)
        if result.blocked and result.reason:
            _record_blocked_reason(result.reason)
            logger.warning(
                "SendGrid recusou o envio de email com anexo.",
                extra={
                    "status_code": getattr(exc, "status_code", None),
                    "reason": result.reason,
                    "from_email": settings.sendgrid_sender,
                },
            )
        else:
            logger.exception("Falha ao enviar email com anexo via SendGrid")
        return result
    except Exception:
        logger.exception("Falha ao enviar email com anexo via SendGrid")
        return EmailSendResult(sent=False, blocked=False, reason="unexpected_error")


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
