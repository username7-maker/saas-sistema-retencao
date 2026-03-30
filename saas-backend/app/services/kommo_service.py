from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import include_all_tenants
from app.models import Gym, KommoMemberLink, Member


@dataclass
class KommoHandoffResult:
    status: str
    contact_id: str | None
    lead_id: str | None
    task_id: str | None
    detail: str | None = None


class KommoServiceError(RuntimeError):
    pass


def get_kommo_gym(db: Session, gym_id: UUID) -> Gym:
    gym = db.scalar(include_all_tenants(select(Gym).where(Gym.id == gym_id), reason="kommo.fetch_gym"))
    if not gym:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academia nao encontrada")
    return gym


def is_kommo_ready(gym: Gym | None) -> bool:
    if gym is None:
        return False
    return bool(gym.kommo_enabled and (gym.kommo_base_url or "").strip() and (gym.kommo_access_token_encrypted or "").strip())


def test_kommo_connection(db: Session, *, gym_id: UUID) -> dict[str, Any]:
    gym = get_kommo_gym(db, gym_id)
    if not is_kommo_ready(gym):
        return {
            "success": False,
            "message": "Configure URL e token da Kommo antes de testar a conexao.",
            "detail": "Sem credenciais validas, o AI GYM OS nao consegue entregar handoffs para a Kommo.",
            "base_url": normalize_kommo_base_url(gym.kommo_base_url),
        }

    try:
        response = _kommo_request(
            gym=gym,
            method="GET",
            path="/api/v4/account",
        )
        account_name = str(response.get("name") or "").strip() or "conta Kommo"
        return {
            "success": True,
            "message": "Conexao com a Kommo validada com sucesso.",
            "detail": f"Conta identificada: {account_name}.",
            "base_url": normalize_kommo_base_url(gym.kommo_base_url),
        }
    except KommoServiceError as exc:
        return {
            "success": False,
            "message": "Nao foi possivel validar a conexao com a Kommo.",
            "detail": str(exc),
            "base_url": normalize_kommo_base_url(gym.kommo_base_url),
        }


def handoff_member_to_kommo(
    db: Session,
    *,
    gym_id: UUID,
    member: Member,
    title: str,
    summary: str,
    source: str,
    ai_gym_profile_url: str | None = None,
    due_in_hours: int = 24,
) -> KommoHandoffResult:
    gym = get_kommo_gym(db, gym_id)
    if not is_kommo_ready(gym):
        return KommoHandoffResult(
            status="skipped",
            contact_id=None,
            lead_id=None,
            task_id=None,
            detail="Kommo nao configurada para esta academia.",
        )

    if not (member.phone or member.email):
        return KommoHandoffResult(
            status="skipped",
            contact_id=None,
            lead_id=None,
            task_id=None,
            detail="Membro sem telefone e sem email para handoff.",
        )

    link = _get_member_link(db, gym_id=gym.id, member_id=member.id)
    lead_id = link.kommo_lead_id if link else None
    contact_id = link.kommo_contact_id if link else None

    if not lead_id:
        payload = [_build_complex_lead_payload(gym=gym, member=member, title=title, summary=summary)]
        created = _kommo_request(gym=gym, method="POST", path="/api/v4/leads/complex", json=payload)
        lead_id, contact_id = _extract_complex_lead_ids(created)

    task_id = _create_kommo_task(
        gym=gym,
        lead_id=lead_id,
        title=title,
        summary=summary,
        source=source,
        ai_gym_profile_url=ai_gym_profile_url,
        due_in_hours=due_in_hours,
    )

    if link is None:
        link = KommoMemberLink(gym_id=gym.id, member_id=member.id)
    link.kommo_contact_id = contact_id
    link.kommo_lead_id = lead_id
    link.last_handoff_at = datetime.now(tz=timezone.utc)
    link.last_action_type = source
    db.add(link)
    db.flush()

    return KommoHandoffResult(
        status="sent",
        contact_id=contact_id,
        lead_id=lead_id,
        task_id=task_id,
        detail="Handoff entregue para a Kommo.",
    )


def normalize_kommo_base_url(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().rstrip("/")
    if not normalized:
        return None
    if not normalized.startswith("http://") and not normalized.startswith("https://"):
        normalized = f"https://{normalized}"
    return normalized


def _kommo_request(
    *,
    gym: Gym,
    method: str,
    path: str,
    json: Any | None = None,
) -> dict[str, Any]:
    base_url = normalize_kommo_base_url(gym.kommo_base_url)
    token = (gym.kommo_access_token_encrypted or "").strip()
    if not base_url or not token:
        raise KommoServiceError("Kommo nao configurada para esta academia.")

    url = f"{base_url}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.request(method=method, url=url, headers=headers, json=json)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or f"HTTP {exc.response.status_code}"
        raise KommoServiceError(detail[:500]) from exc
    except httpx.HTTPError as exc:
        raise KommoServiceError(f"Falha de rede com a Kommo: {type(exc).__name__}.") from exc

    if not response.content:
        return {}
    payload = response.json()
    return payload if isinstance(payload, dict) else {"data": payload}


def _get_member_link(db: Session, *, gym_id: UUID, member_id: UUID) -> KommoMemberLink | None:
    return db.scalar(
        include_all_tenants(
            select(KommoMemberLink).where(
                KommoMemberLink.gym_id == gym_id,
                KommoMemberLink.member_id == member_id,
            ),
            reason="kommo.fetch_member_link",
        )
    )


def _build_complex_lead_payload(*, gym: Gym, member: Member, title: str, summary: str) -> dict[str, Any]:
    contact_payload: dict[str, Any] = {"name": member.full_name}
    custom_fields: list[dict[str, Any]] = []
    if member.phone:
        custom_fields.append(
            {
                "field_code": "PHONE",
                "values": [{"value": member.phone, "enum_code": "WORK"}],
            }
        )
    if member.email:
        custom_fields.append(
            {
                "field_code": "EMAIL",
                "values": [{"value": member.email, "enum_code": "WORK"}],
            }
        )
    if custom_fields:
        contact_payload["custom_fields_values"] = custom_fields

    payload: dict[str, Any] = {
        "name": title,
        "_embedded": {"contacts": [contact_payload]},
    }

    pipeline_id = _safe_int(gym.kommo_default_pipeline_id)
    if pipeline_id is not None:
        payload["pipeline_id"] = pipeline_id

    stage_id = _safe_int(gym.kommo_default_stage_id)
    if stage_id is not None:
        payload["status_id"] = stage_id

    responsible_user_id = _safe_int(gym.kommo_default_responsible_user_id)
    if responsible_user_id is not None:
        payload["responsible_user_id"] = responsible_user_id

    return payload


def _extract_complex_lead_ids(response: dict[str, Any]) -> tuple[str | None, str | None]:
    lead_id = None
    contact_id = None
    embedded = response.get("_embedded")
    if isinstance(embedded, dict):
        leads = embedded.get("leads")
        if isinstance(leads, list) and leads:
            lead = leads[0] if isinstance(leads[0], dict) else {}
            if isinstance(lead, dict):
                raw_lead_id = lead.get("id")
                if raw_lead_id is not None:
                    lead_id = str(raw_lead_id)
                lead_contacts = lead.get("_embedded", {}).get("contacts") if isinstance(lead.get("_embedded"), dict) else None
                if isinstance(lead_contacts, list) and lead_contacts:
                    first_contact = lead_contacts[0] if isinstance(lead_contacts[0], dict) else {}
                    if isinstance(first_contact, dict) and first_contact.get("id") is not None:
                        contact_id = str(first_contact["id"])

        contacts = embedded.get("contacts")
        if not contact_id and isinstance(contacts, list) and contacts:
            first_contact = contacts[0] if isinstance(contacts[0], dict) else {}
            if isinstance(first_contact, dict) and first_contact.get("id") is not None:
                contact_id = str(first_contact["id"])

    if not lead_id:
        raw_data = response.get("data")
        if isinstance(raw_data, list) and raw_data and isinstance(raw_data[0], dict):
            if raw_data[0].get("id") is not None:
                lead_id = str(raw_data[0]["id"])

    if not lead_id:
        raise KommoServiceError("Kommo nao retornou o lead criado no handoff.")
    return lead_id, contact_id


def _create_kommo_task(
    *,
    gym: Gym,
    lead_id: str,
    title: str,
    summary: str,
    source: str,
    ai_gym_profile_url: str | None,
    due_in_hours: int,
) -> str | None:
    due_at = datetime.now(tz=timezone.utc) + timedelta(hours=max(due_in_hours, 1))
    text_lines = [
        title.strip(),
        "",
        summary.strip(),
        "",
        f"Origem: {source}",
    ]
    if ai_gym_profile_url:
        text_lines.extend(["", f"AI GYM OS: {ai_gym_profile_url}"])
    task_payload: dict[str, Any] = {
        "text": "\n".join(line for line in text_lines if line is not None).strip()[:650],
        "complete_till": int(due_at.timestamp()),
        "entity_id": int(lead_id),
        "entity_type": "leads",
    }
    responsible_user_id = _safe_int(gym.kommo_default_responsible_user_id)
    if responsible_user_id is not None:
        task_payload["responsible_user_id"] = responsible_user_id

    created = _kommo_request(gym=gym, method="POST", path="/api/v4/tasks", json=[task_payload])
    embedded = created.get("_embedded")
    if isinstance(embedded, dict):
        tasks = embedded.get("tasks")
        if isinstance(tasks, list) and tasks and isinstance(tasks[0], dict) and tasks[0].get("id") is not None:
            return str(tasks[0]["id"])
    data = created.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get("id") is not None:
        return str(data[0]["id"])
    return None


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized.isdigit():
        return None
    return int(normalized)
