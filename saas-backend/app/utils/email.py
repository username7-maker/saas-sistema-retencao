import logging
from base64 import b64encode

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Attachment, Disposition, FileContent, FileName, FileType, Mail

from app.core.config import settings


logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, content: str) -> bool:
    if not settings.sendgrid_api_key:
        return False

    try:
        message = Mail(
            from_email=settings.sendgrid_sender,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content,
        )
        client = SendGridAPIClient(settings.sendgrid_api_key)
        response = client.send(message)
        return 200 <= response.status_code < 300
    except Exception:
        logger.exception("Falha ao enviar email via SendGrid")
        return False


def send_email_with_attachment(
    to_email: str,
    subject: str,
    content: str,
    *,
    filename: str,
    attachment_bytes: bytes,
    mime_type: str = "application/pdf",
) -> bool:
    if not settings.sendgrid_api_key:
        return False

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
        return 200 <= response.status_code < 300
    except Exception:
        logger.exception("Falha ao enviar email com anexo via SendGrid")
        return False
