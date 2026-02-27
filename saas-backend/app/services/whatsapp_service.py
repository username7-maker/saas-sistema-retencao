import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.message_log import MessageLog


logger = logging.getLogger(__name__)
DEFAULT_RATE_LIMIT_PER_HOUR = 6

WHATSAPP_TEMPLATES: dict[str, str] = {
    "reengagement_3d": (
        "Ola {nome}! Sentimos sua falta na academia. "
        "Ja faz {dias} dias desde seu ultimo treino. "
        "Que tal retomar o ritmo esta semana? Estamos te esperando! 💪"
    ),
    "reengagement_7d": (
        "Oi {nome}, tudo bem? Notamos que voce nao aparece ha {dias} dias. "
        "Sabemos que a rotina pesa, mas seu progresso importa! "
        "Vamos conversar sobre como podemos te ajudar a voltar?"
    ),
    "risk_red": (
        "{nome}, queremos muito te ver de volta! "
        "Seu plano {plano} continua ativo e preparamos novidades para voce. "
        "Podemos agendar um horario para conversarmos?"
    ),
    "nps_low": (
        "Oi {nome}, recebemos seu feedback e queremos melhorar sua experiencia. "
        "Podemos conversar sobre como tornar seus treinos mais agradaveis?"
    ),
    "birthday": (
        "Feliz aniversario, {nome}! 🎂 "
        "A equipe da academia te deseja tudo de bom. "
        "Passe aqui para receber uma surpresa especial!"
    ),
    "custom": "{mensagem}",
}


class _SafeFormatDict(dict):
    """Retorna a chave original quando ausente, evitando KeyError em templates."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def render_template(template_name: str, variables: dict) -> str:
    template = WHATSAPP_TEMPLATES.get(template_name, WHATSAPP_TEMPLATES["custom"])
    try:
        return template.format_map(_SafeFormatDict(variables))
    except Exception:
        return template


def _format_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if not digits.startswith("55") and len(digits) <= 11:
        digits = f"55{digits}"
    return digits


def _is_rate_limited(db: Session, recipient: str, limit_per_hour: int = DEFAULT_RATE_LIMIT_PER_HOUR) -> bool:
    window_start = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    total_recent = db.scalar(
        select(func.count())
        .select_from(MessageLog)
        .where(
            MessageLog.channel == "whatsapp",
            MessageLog.recipient == recipient,
            MessageLog.created_at >= window_start,
            MessageLog.status.in_(["pending", "sent"]),
        )
    ) or 0
    return total_recent >= limit_per_hour


async def send_whatsapp_message(
    db: Session,
    *,
    phone: str,
    message: str,
    member_id: UUID | None = None,
    automation_rule_id: UUID | None = None,
    template_name: str | None = None,
) -> MessageLog:
    formatted_phone = _format_phone(phone)

    log_entry = MessageLog(
        member_id=member_id,
        automation_rule_id=automation_rule_id,
        channel="whatsapp",
        recipient=formatted_phone,
        template_name=template_name,
        content=message,
        status="pending",
    )
    db.add(log_entry)
    db.flush()

    if _is_rate_limited(db, formatted_phone, settings.whatsapp_rate_limit_per_hour):
        log_entry.status = "blocked"
        log_entry.error_detail = "Rate limit exceeded for recipient in the last hour"
        db.add(log_entry)
        db.flush()
        logger.warning("WhatsApp bloqueado por rate limit para %s", formatted_phone)
        return log_entry

    if not settings.whatsapp_api_url or not settings.whatsapp_api_token:
        log_entry.status = "skipped"
        log_entry.error_detail = "WhatsApp API not configured"
        db.add(log_entry)
        db.flush()
        logger.warning("WhatsApp API nao configurada, mensagem nao enviada")
        return log_entry

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.whatsapp_api_url}/message/sendText/{settings.whatsapp_instance}",
                headers={"apikey": settings.whatsapp_api_token},
                json={
                    "number": formatted_phone,
                    "text": message,
                },
            )
            response.raise_for_status()
            log_entry.status = "sent"
            log_entry.extra_data = {"response_status": response.status_code}
    except Exception as exc:
        log_entry.status = "failed"
        log_entry.error_detail = str(exc)[:500]
        logger.exception("Falha ao enviar WhatsApp para %s", formatted_phone)

    db.add(log_entry)
    db.flush()
    return log_entry


def send_whatsapp_sync(
    db: Session,
    *,
    phone: str,
    message: str,
    member_id: UUID | None = None,
    automation_rule_id: UUID | None = None,
    template_name: str | None = None,
) -> MessageLog:
    formatted_phone = _format_phone(phone)

    log_entry = MessageLog(
        member_id=member_id,
        automation_rule_id=automation_rule_id,
        channel="whatsapp",
        recipient=formatted_phone,
        template_name=template_name,
        content=message,
        status="pending",
    )
    db.add(log_entry)
    db.flush()

    if _is_rate_limited(db, formatted_phone, settings.whatsapp_rate_limit_per_hour):
        log_entry.status = "blocked"
        log_entry.error_detail = "Rate limit exceeded for recipient in the last hour"
        db.add(log_entry)
        db.flush()
        logger.warning("WhatsApp bloqueado por rate limit para %s", formatted_phone)
        return log_entry

    if not settings.whatsapp_api_url or not settings.whatsapp_api_token:
        log_entry.status = "skipped"
        log_entry.error_detail = "WhatsApp API not configured"
        db.add(log_entry)
        db.flush()
        logger.warning("WhatsApp API nao configurada, mensagem nao enviada")
        return log_entry

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{settings.whatsapp_api_url}/message/sendText/{settings.whatsapp_instance}",
                headers={"apikey": settings.whatsapp_api_token},
                json={
                    "number": formatted_phone,
                    "text": message,
                },
            )
            response.raise_for_status()
            log_entry.status = "sent"
            log_entry.extra_data = {"response_status": response.status_code}
    except Exception as exc:
        log_entry.status = "failed"
        log_entry.error_detail = str(exc)[:500]
        logger.exception("Falha ao enviar WhatsApp para %s", formatted_phone)

    db.add(log_entry)
    db.flush()
    return log_entry
