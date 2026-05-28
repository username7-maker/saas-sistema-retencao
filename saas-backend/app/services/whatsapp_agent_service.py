import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import MessageLog
from app.services.whatsapp_service import normalize_phone, send_whatsapp_sync


logger = logging.getLogger(__name__)

WhatsAppAgentAudience = Literal["internal", "external"]


@dataclass(frozen=True)
class WhatsAppAgentOutcome:
    processed: bool
    fallback_allowed: bool
    detail: str
    response: dict[str, Any] | None = None


def whatsapp_agent_enabled() -> bool:
    return _agent_mode() in {"sandbox", "active"}


def classify_whatsapp_agent_audience(phone: str | None) -> WhatsAppAgentAudience:
    normalized = normalize_phone(phone)
    if normalized and normalized in _internal_allowed_phones():
        return "internal"
    return "external"


def build_whatsapp_agent_payload(
    *,
    event_id: str,
    provider_message_id: str | None,
    gym_id: UUID | str | None,
    instance: str,
    sender_phone: str,
    sender_name: str | None,
    audience: WhatsAppAgentAudience,
    message: str,
    member_id: UUID | str | None = None,
    lead_id: UUID | str | None = None,
    sequence_id: UUID | str | None = None,
    role: str | None = None,
    source: str = "evolution",
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "provider_message_id": provider_message_id,
        "gym_id": str(gym_id) if gym_id else None,
        "instance": instance,
        "sender_phone": normalize_phone(sender_phone),
        "sender_name": sender_name,
        "audience": audience,
        "message": message,
        "attachments": [],
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "source": source,
        "context": {
            "member_id": str(member_id) if member_id else None,
            "lead_id": str(lead_id) if lead_id else None,
            "sequence_id": str(sequence_id) if sequence_id else None,
            "role": role,
        },
    }


def call_whatsapp_agent(payload: dict[str, Any]) -> WhatsAppAgentOutcome:
    mode = _agent_mode()
    if mode == "off":
        return WhatsAppAgentOutcome(False, True, "WhatsApp agent disabled")
    if payload.get("audience") == "external" and not settings.whatsapp_external_auto_reply_enabled:
        return WhatsAppAgentOutcome(False, True, "External WhatsApp auto-reply disabled")

    webhook_url = settings.n8n_whatsapp_agent_webhook_url.strip()
    token = settings.cordex_agent_service_token.strip()
    if not webhook_url or not token:
        return WhatsAppAgentOutcome(
            False,
            settings.whatsapp_agent_fallback_to_legacy_nurturing,
            "WhatsApp agent webhook not configured",
        )

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                webhook_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Cordex-Agent-Source": "backend-whatsapp-webhook",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        logger.exception("Falha ao chamar WhatsApp AI Agent no n8n")
        return WhatsAppAgentOutcome(
            False,
            settings.whatsapp_agent_fallback_to_legacy_nurturing,
            "WhatsApp agent unavailable",
        )

    return WhatsAppAgentOutcome(True, False, "WhatsApp agent handled message", data)


def dispatch_whatsapp_agent_response(
    db: Session,
    *,
    agent_response: dict[str, Any] | None,
    inbound_phone: str,
    instance: str | None,
    member_id: UUID | None = None,
    lead_id: UUID | None = None,
) -> WhatsAppAgentOutcome:
    if not agent_response:
        return WhatsAppAgentOutcome(False, True, "No agent response")

    status = str(agent_response.get("status") or "").strip()
    action = str(agent_response.get("action") or "").strip()
    message = str(agent_response.get("message") or "").strip()
    recipient = normalize_phone(agent_response.get("recipient_phone") or inbound_phone)
    inbound = normalize_phone(inbound_phone)

    if status in {"pending_approval", "needs_clarification", "no_reply"}:
        return WhatsAppAgentOutcome(True, False, f"Agent returned {status}", agent_response)
    if status != "success":
        return WhatsAppAgentOutcome(False, settings.whatsapp_agent_fallback_to_legacy_nurturing, "Agent returned error", agent_response)
    if action not in {"send_reply", "handoff"} or not message:
        return WhatsAppAgentOutcome(True, False, "Agent handled without outbound reply", agent_response)
    if recipient != inbound:
        logger.warning("WhatsApp agent tried to reply to a different recipient; blocked")
        return WhatsAppAgentOutcome(True, False, "Blocked cross-recipient WhatsApp reply", agent_response)
    if _agent_mode() != "active":
        return WhatsAppAgentOutcome(True, False, "Agent reply suppressed in sandbox mode", agent_response)

    result = send_whatsapp_sync(
        db,
        phone=recipient,
        message=message,
        instance=instance,
        member_id=member_id,
        lead_id=lead_id,
        template_name="cordex_whatsapp_agent",
        direction="outbound",
        event_type="whatsapp_agent_reply",
    )
    response = {**agent_response, "backend_send_status": result.status}
    return WhatsAppAgentOutcome(True, False, "Agent reply sent through backend", response)


def send_agent_reply_from_service_token(
    db: Session,
    *,
    recipient_phone: str,
    message: str,
    instance: str | None = None,
    member_id: UUID | None = None,
    lead_id: UUID | None = None,
) -> MessageLog:
    return send_whatsapp_sync(
        db,
        phone=recipient_phone,
        message=message,
        instance=instance,
        member_id=member_id,
        lead_id=lead_id,
        template_name="cordex_whatsapp_agent",
        direction="outbound",
        event_type="whatsapp_agent_reply",
    )


def _agent_mode() -> str:
    normalized = (settings.whatsapp_agent_mode or "off").strip().lower()
    return normalized if normalized in {"off", "sandbox", "active"} else "off"


def _internal_allowed_phones() -> set[str]:
    raw = settings.whatsapp_internal_allowed_phones or ""
    return {phone for item in raw.split(",") if (phone := normalize_phone(item.strip()))}
