from __future__ import annotations

import hashlib
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db, set_current_gym_id
from app.models import Member, MessageLog
from app.services.autopilot_event_service import record_event
from app.services.autopilot_resolver_service import resolve_event
from app.services.kommo_service import find_member_link_by_kommo_ids, get_kommo_gym

router = APIRouter(prefix="/kommo", tags=["kommo"])


@router.post("/webhook")
async def kommo_webhook_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_kommo_webhook_token: Annotated[str | None, Header(alias="X-Kommo-Webhook-Token")] = None,
    token: str | None = Query(default=None),
) -> dict[str, Any]:
    expected = (settings.kommo_webhook_token or "").strip()
    received = (x_kommo_webhook_token or token or "").strip()
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kommo webhook token nao configurado.")
    if received != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token Kommo invalido.")

    payload = await _read_payload(request)
    lead_id = _first_string(payload, {"lead_id", "kommo_lead_id", "entity_id", "lead[id]", "leads[id]"})
    contact_id = _first_string(payload, {"contact_id", "kommo_contact_id", "contact[id]", "contacts[id]"})
    message_text = _first_string(payload, {"message", "text", "body", "note", "comment", "message[text]"})
    event_id = _first_string(payload, {"event_id", "message_id", "id", "note_id"}) or _payload_hash(payload)

    link = find_member_link_by_kommo_ids(db, kommo_lead_id=lead_id, kommo_contact_id=contact_id)
    if link is None:
        return {"processed": False, "detail": "Vinculo Kommo nao encontrado para o evento."}

    set_current_gym_id(link.gym_id)
    gym = get_kommo_gym(db, link.gym_id)
    member = db.get(Member, link.member_id)
    if member is None:
        return {"processed": False, "detail": "Aluno vinculado a Kommo nao encontrado."}

    content = (message_text or "").strip()
    log = MessageLog(
        gym_id=link.gym_id,
        member_id=member.id,
        lead_id=None,
        channel="kommo",
        recipient=(member.phone or member.email or str(member.id)),
        template_name=None,
        content=content,
        status="received",
        direction="inbound",
        event_type="kommo_inbound",
        provider_message_id=event_id,
        extra_data={
            "kommo_contact_id": link.kommo_contact_id,
            "kommo_lead_id": link.kommo_lead_id,
            "raw_event_keys": sorted(str(key) for key in payload.keys()) if isinstance(payload, dict) else [],
        },
    )
    db.add(log)
    db.flush()
    event = record_event(
        db,
        gym_id=link.gym_id,
        event_type="kommo_inbound_received",
        source="kommo_webhook",
        member_id=member.id,
        metadata={
            "message_text": content,
            "kommo_contact_id": link.kommo_contact_id,
            "kommo_lead_id": link.kommo_lead_id,
            "message_log_id": str(log.id),
        },
        deduplication_key=f"kommo:inbound:{link.kommo_lead_id or lead_id}:{link.kommo_contact_id or contact_id}:{event_id}",
        raw_payload=payload if isinstance(payload, dict) else {"payload": payload},
        flush=False,
    )
    result = None
    if bool(getattr(gym, "kommo_auto_close_enabled", True)):
        result = resolve_event(db, event, flush=False)
    db.commit()
    return {"processed": True, "event_id": str(event.id), "resolver": result}


async def _read_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        return payload if isinstance(payload, dict) else {"data": payload}
    form = await request.form()
    if form:
        return {key: value for key, value in form.items()}
    raw = await request.body()
    return {"raw": raw.decode("utf-8", errors="ignore")}


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()[:32]


def _first_string(payload: dict[str, Any], keys: set[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    found = _find_nested_value(payload, keys)
    if found is None:
        return None
    normalized = str(found).strip()
    return normalized or None


def _find_nested_value(value: Any, keys: set[str]) -> Any | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in keys and child is not None:
                return child
            found = _find_nested_value(child, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_nested_value(child, keys)
            if found is not None:
                return found
    return None
