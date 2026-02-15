import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
