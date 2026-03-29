import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_current_gym_id
from app.models import Lead, Member, MemberStatus, RiskLevel
from app.models.message_log import MessageLog
from app.services.operational_outcome_service import record_operational_outcome


logger = logging.getLogger(__name__)
DEFAULT_RATE_LIMIT_PER_HOUR = 6

WHATSAPP_TEMPLATES: dict[str, str] = {
    "reengagement_3d": (
        "Ola {nome}! Sentimos sua falta na academia. "
        "Ja faz {dias} dias desde seu ultimo treino. "
        "Que tal retomar o ritmo esta semana? Estamos te esperando! ðŸ’ª"
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
        "Feliz aniversario, {nome}! ðŸŽ‚ "
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


def format_phone(phone: str) -> str:
    return _format_phone(phone)


def normalize_phone(phone: str | None) -> str:
    if not phone:
        return ""
    return _format_phone(phone)


def format_phone_display(phone: str | None) -> str | None:
    normalized = normalize_phone(phone)
    if not normalized:
        return None

    local = normalized[2:] if normalized.startswith("55") else normalized
    if len(local) == 11:
        return f"+55 ({local[:2]}) {local[2:7]}-{local[7:]}"
    if len(local) == 10:
        return f"+55 ({local[:2]}) {local[2:6]}-{local[6:]}"
    return f"+{normalized}"


def build_whatsapp_url(phone: str | None, message: str | None = None) -> str | None:
    normalized = normalize_phone(phone)
    if not normalized:
        return None
    if not message:
        return f"https://wa.me/{normalized}"
    from urllib.parse import quote
    return f"https://wa.me/{normalized}?text={quote(message)}"


def phones_match(left: str | None, right: str | None) -> bool:
    normalized_left = normalize_phone(left)
    normalized_right = normalize_phone(right)
    if not normalized_left or not normalized_right:
        return False
    return (
        normalized_left == normalized_right
        or normalized_left.endswith(normalized_right)
        or normalized_right.endswith(normalized_left)
    )


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


def get_gym_instance(db: Session, gym_id: UUID | str | None) -> str | None:
    """
    Retorna a instancia WhatsApp do gym somente se estiver conectada.
    """
    from app.models.gym import Gym

    if not gym_id:
        return None

    gym = db.get(Gym, gym_id)
    instance_name = getattr(gym, "whatsapp_instance", None)
    status = getattr(gym, "whatsapp_status", None)

    if not gym or not instance_name:
        return None
    if status != "connected":
        logger.warning(
            "gym %s tem instancia %s mas status e '%s' - envio bloqueado",
            gym_id,
            instance_name,
            status,
        )
        return None
    return instance_name


def resolve_instance(instance: str | None) -> str | None:
    """
    Resolve qual instancia usar:
    1. instancia explicita passada -> usa
    2. None + fallback habilitado -> usa settings.whatsapp_instance
    3. None + fallback desabilitado -> None
    """
    if instance:
        return instance
    if settings.whatsapp_allow_global_fallback and settings.whatsapp_instance:
        return settings.whatsapp_instance
    return None


def _instance_source(explicit: str | None) -> str:
    return "gym" if explicit else "global_fallback"


def _build_message_log(
    *,
    db: Session,
    phone: str,
    message: str,
    member_id: UUID | None,
    lead_id: UUID | None,
    automation_rule_id: UUID | None,
    template_name: str | None,
    direction: str | None,
    event_type: str | None,
    provider_message_id: str | None,
) -> tuple[str, MessageLog]:
    formatted_phone = _format_phone(phone)
    log_entry = MessageLog(
        member_id=member_id,
        lead_id=lead_id,
        automation_rule_id=automation_rule_id,
        channel="whatsapp",
        recipient=formatted_phone,
        template_name=template_name,
        content=message,
        status="pending",
        direction=direction,
        event_type=event_type,
        provider_message_id=provider_message_id,
        extra_data={},
    )
    db.add(log_entry)
    db.flush()
    return formatted_phone, log_entry


def _mark_log(log_entry: MessageLog, *, status: str, error: str | None = None, extra_data: dict | None = None) -> None:
    log_entry.status = status
    log_entry.error_detail = error
    log_entry.extra_data = extra_data or {}


def _resolve_outcome_gym_id(db: Session, *, member_id: UUID | None, lead_id: UUID | None):
    if member_id:
        gym_id = db.scalar(select(Member.gym_id).where(Member.id == member_id))
        if gym_id:
            return gym_id
    if lead_id:
        gym_id = db.scalar(select(Lead.gym_id).where(Lead.id == lead_id))
        if gym_id:
            return gym_id
    return get_current_gym_id()


def _message_status_to_outcome_status(status: str) -> str:
    if status == "sent":
        return "sent"
    if status == "failed":
        return "failed"
    if status in {"blocked", "skipped"}:
        return "ignored"
    return "attempted"


def _record_whatsapp_outcome(
    db: Session,
    *,
    log_entry: MessageLog,
    member_id: UUID | None,
    lead_id: UUID | None,
    automation_rule_id: UUID | None,
    template_name: str | None,
    event_type: str | None,
) -> None:
    gym_id = _resolve_outcome_gym_id(db, member_id=member_id, lead_id=lead_id)
    if not gym_id:
        return

    source = "automation" if automation_rule_id else ("crm" if lead_id else "retention")
    record_operational_outcome(
        db,
        gym_id=gym_id,
        source=source,
        action_type=event_type or "whatsapp_send",
        actor="automation" if automation_rule_id else "user",
        status=_message_status_to_outcome_status(log_entry.status),
        member_id=member_id,
        lead_id=lead_id,
        message_log_id=log_entry.id,
        channel="whatsapp",
        related_entity_type="message_log",
        related_entity_id=log_entry.id,
        playbook_key=template_name,
        metadata_json={
            "template_name": template_name,
            "message_status": log_entry.status,
            "event_type": event_type,
            "instance_used": (log_entry.extra_data or {}).get("instance_used"),
            "instance_source": (log_entry.extra_data or {}).get("instance_source"),
        },
        flush=False,
    )


async def send_whatsapp_message(
    db: Session,
    *,
    phone: str,
    message: str,
    instance: str | None = None,
    member_id: UUID | None = None,
    lead_id: UUID | None = None,
    automation_rule_id: UUID | None = None,
    template_name: str | None = None,
    direction: str | None = "outbound",
    event_type: str | None = None,
    provider_message_id: str | None = None,
) -> MessageLog:
    formatted_phone, log_entry = _build_message_log(
        db=db,
        phone=phone,
        message=message,
        member_id=member_id,
        lead_id=lead_id,
        automation_rule_id=automation_rule_id,
        template_name=template_name,
        direction=direction,
        event_type=event_type,
        provider_message_id=provider_message_id,
    )
    resolved = resolve_instance(instance)

    if not resolved:
        _mark_log(
            log_entry,
            status="skipped",
            error=(
                "WhatsApp instance not configured or not connected for this gym. "
                "Go to Settings -> WhatsApp to connect."
            ),
            extra_data={"instance_used": None, "instance_source": "none"},
        )
        db.flush()
        _record_whatsapp_outcome(
            db,
            log_entry=log_entry,
            member_id=member_id,
            lead_id=lead_id,
            automation_rule_id=automation_rule_id,
            template_name=template_name,
            event_type=event_type,
        )
        logger.warning(
            "WhatsApp skipped: sem instancia conectada phone=%s instance_arg=%s",
            formatted_phone,
            instance,
        )
        return log_entry

    if not settings.whatsapp_api_url or not settings.whatsapp_api_token:
        _mark_log(
            log_entry,
            status="skipped",
            error="WhatsApp API URL/token not configured",
            extra_data={"instance_used": resolved, "instance_source": _instance_source(instance)},
        )
        db.flush()
        _record_whatsapp_outcome(
            db,
            log_entry=log_entry,
            member_id=member_id,
            lead_id=lead_id,
            automation_rule_id=automation_rule_id,
            template_name=template_name,
            event_type=event_type,
        )
        return log_entry

    if _is_rate_limited(db, formatted_phone, settings.whatsapp_rate_limit_per_hour):
        _mark_log(
            log_entry,
            status="blocked",
            error="Rate limit exceeded for recipient",
            extra_data={"instance_used": resolved, "instance_source": _instance_source(instance)},
        )
        db.flush()
        _record_whatsapp_outcome(
            db,
            log_entry=log_entry,
            member_id=member_id,
            lead_id=lead_id,
            automation_rule_id=automation_rule_id,
            template_name=template_name,
            event_type=event_type,
        )
        return log_entry

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.whatsapp_api_url}/message/sendText/{resolved}",
                headers={"apikey": settings.whatsapp_api_token},
                json={"number": formatted_phone, "text": message},
            )
            response.raise_for_status()
            _mark_log(
                log_entry,
                status="sent",
                extra_data={
                    "instance_used": resolved,
                    "instance_source": _instance_source(instance),
                    "response_status": response.status_code,
                },
            )
    except Exception as exc:
        _mark_log(
            log_entry,
            status="failed",
            error=str(exc)[:500],
            extra_data={"instance_used": resolved, "instance_source": _instance_source(instance)},
        )
        logger.exception("Falha ao enviar WhatsApp para %s via %s", formatted_phone, resolved)

    db.flush()
    _record_whatsapp_outcome(
        db,
        log_entry=log_entry,
        member_id=member_id,
        lead_id=lead_id,
        automation_rule_id=automation_rule_id,
        template_name=template_name,
        event_type=event_type,
    )
    return log_entry


def suggest_whatsapp_template(db: Session, member_id: UUID) -> dict:
    """Generate a suggested WhatsApp message for a member based on their state."""
    member = db.get(Member, member_id)
    if not member:
        from fastapi import HTTPException, status as http_status

        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")

    now = datetime.now(tz=timezone.utc)
    days_inactive = (
        (now - member.last_checkin_at).days
        if member.last_checkin_at
        else None
    )
    variables = {
        "nome": member.full_name.split()[0],
        "plano": member.plan_name,
        "dias": str(days_inactive) if days_inactive else "alguns",
    }

    if member.status == MemberStatus.CANCELLED:
        template_name = "risk_red"
    elif member.risk_level == RiskLevel.RED:
        if days_inactive is not None and days_inactive >= 7:
            template_name = "reengagement_7d"
        else:
            template_name = "risk_red"
    elif member.risk_level == RiskLevel.YELLOW:
        if member.nps_last_score > 0 and member.nps_last_score < 7:
            template_name = "nps_low"
        else:
            template_name = "reengagement_3d"
    else:
        template_name = "reengagement_3d"

    message = render_template(template_name, variables)

    if settings.claude_api_key:
        try:
            message = _personalize_template_with_ai(member, message, days_inactive)
        except Exception:
            logger.exception("Falha ao personalizar template com IA")

    return {
        "member_id": str(member.id),
        "member_name": member.full_name,
        "phone": member.phone,
        "template_name": template_name,
        "suggested_message": message,
        "source": "ai" if settings.claude_api_key else "rule",
    }


def _personalize_template_with_ai(member: Member, base_message: str, days_inactive: int | None) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.claude_api_key)
    prompt = (
        "Voce e um assistente de retencao de uma academia. "
        "Personalize a mensagem de WhatsApp abaixo mantendo o mesmo tom e objetivo. "
        "Maximo 200 caracteres. Tom profissional e amigavel. Nao use emoji em excesso.\n\n"
        f"Aluno: {member.full_name}\n"
        f"Plano: {member.plan_name}\n"
        f"Risco: {member.risk_level.value}\n"
        f"Dias inativo: {days_inactive or 'desconhecido'}\n"
        f"NPS: {member.nps_last_score}\n\n"
        f"Mensagem base: {base_message}\n"
    )
    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=200,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    result = response.content[0].text.strip()
    return result[:500] if result else base_message


def send_whatsapp_sync(
    db: Session,
    *,
    phone: str,
    message: str,
    instance: str | None = None,
    member_id: UUID | None = None,
    lead_id: UUID | None = None,
    automation_rule_id: UUID | None = None,
    template_name: str | None = None,
    direction: str | None = "outbound",
    event_type: str | None = None,
    provider_message_id: str | None = None,
) -> MessageLog:
    formatted_phone, log_entry = _build_message_log(
        db=db,
        phone=phone,
        message=message,
        member_id=member_id,
        lead_id=lead_id,
        automation_rule_id=automation_rule_id,
        template_name=template_name,
        direction=direction,
        event_type=event_type,
        provider_message_id=provider_message_id,
    )
    resolved = resolve_instance(instance)

    if not resolved:
        _mark_log(
            log_entry,
            status="skipped",
            error=(
                "WhatsApp instance not configured or not connected for this gym. "
                "Go to Settings -> WhatsApp to connect."
            ),
            extra_data={"instance_used": None, "instance_source": "none"},
        )
        db.flush()
        _record_whatsapp_outcome(
            db,
            log_entry=log_entry,
            member_id=member_id,
            lead_id=lead_id,
            automation_rule_id=automation_rule_id,
            template_name=template_name,
            event_type=event_type,
        )
        logger.warning(
            "WhatsApp skipped: sem instancia conectada phone=%s instance_arg=%s",
            formatted_phone,
            instance,
        )
        return log_entry

    if not settings.whatsapp_api_url or not settings.whatsapp_api_token:
        _mark_log(
            log_entry,
            status="skipped",
            error="WhatsApp API URL/token not configured",
            extra_data={"instance_used": resolved, "instance_source": _instance_source(instance)},
        )
        db.flush()
        _record_whatsapp_outcome(
            db,
            log_entry=log_entry,
            member_id=member_id,
            lead_id=lead_id,
            automation_rule_id=automation_rule_id,
            template_name=template_name,
            event_type=event_type,
        )
        return log_entry

    if _is_rate_limited(db, formatted_phone, settings.whatsapp_rate_limit_per_hour):
        _mark_log(
            log_entry,
            status="blocked",
            error="Rate limit exceeded for recipient",
            extra_data={"instance_used": resolved, "instance_source": _instance_source(instance)},
        )
        db.flush()
        _record_whatsapp_outcome(
            db,
            log_entry=log_entry,
            member_id=member_id,
            lead_id=lead_id,
            automation_rule_id=automation_rule_id,
            template_name=template_name,
            event_type=event_type,
        )
        return log_entry

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{settings.whatsapp_api_url}/message/sendText/{resolved}",
                headers={"apikey": settings.whatsapp_api_token},
                json={"number": formatted_phone, "text": message},
            )
            response.raise_for_status()
            _mark_log(
                log_entry,
                status="sent",
                extra_data={
                    "instance_used": resolved,
                    "instance_source": _instance_source(instance),
                    "response_status": response.status_code,
                },
            )
    except Exception as exc:
        _mark_log(
            log_entry,
            status="failed",
            error=str(exc)[:500],
            extra_data={"instance_used": resolved, "instance_source": _instance_source(instance)},
        )
        logger.exception("Falha ao enviar WhatsApp para %s via %s", formatted_phone, resolved)

    db.flush()
    _record_whatsapp_outcome(
        db,
        log_entry=log_entry,
        member_id=member_id,
        lead_id=lead_id,
        automation_rule_id=automation_rule_id,
        template_name=template_name,
        event_type=event_type,
    )
    return log_entry
