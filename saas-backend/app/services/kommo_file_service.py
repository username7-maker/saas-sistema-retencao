from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import include_all_tenants
from app.models import Gym, KommoFileAttachment, Member
from app.services.kommo_service import KommoServiceError, _kommo_request, normalize_kommo_base_url


DEFAULT_FILE_CHUNK_SIZE = 4 * 1024 * 1024


@dataclass
class KommoNativeFileResult:
    attachment: KommoFileAttachment
    file_uuid: str
    file_name: str
    upload_status: str
    attach_status: str


def upload_and_attach_pdf_to_lead(
    db: Session,
    *,
    gym: Gym,
    member: Member,
    domain: str,
    source_type: str,
    source_id: str,
    lead_id: str,
    contact_id: str | None,
    file_bytes: bytes,
    file_name: str,
    content_type: str = "application/pdf",
) -> KommoNativeFileResult:
    if not file_bytes:
        raise KommoServiceError("PDF vazio; nao foi possivel anexar arquivo na Kommo.")

    attachment = _get_existing_attachment(
        db,
        gym_id=gym.id,
        domain=domain,
        source_type=source_type,
        source_id=source_id,
    )
    if attachment and attachment.file_uuid and attachment.upload_status == "uploaded" and attachment.attach_status == "attached":
        return KommoNativeFileResult(
            attachment=attachment,
            file_uuid=attachment.file_uuid,
            file_name=attachment.file_name or file_name,
            upload_status=attachment.upload_status,
            attach_status=attachment.attach_status,
        )

    if attachment is None:
        attachment = KommoFileAttachment(
            gym_id=gym.id,
            member_id=member.id,
            domain=domain,
            source_type=source_type,
            source_id=source_id,
        )

    attachment.member_id = member.id
    attachment.kommo_lead_id = str(lead_id)
    attachment.kommo_contact_id = contact_id
    attachment.file_name = file_name[:255]
    attachment.content_type = content_type
    attachment.file_size = len(file_bytes)
    attachment.upload_status = "pending"
    attachment.attach_status = "pending"
    attachment.delivery_status = "pending"
    attachment.error_detail = None
    db.add(attachment)
    db.flush()

    try:
        drive_url = get_kommo_drive_url(gym)
        session = create_upload_session(
            gym=gym,
            drive_url=drive_url,
            file_name=file_name,
            file_size=len(file_bytes),
            content_type=content_type,
        )
        file_uuid = upload_file_bytes(
            gym=gym,
            drive_url=drive_url,
            session=session,
            file_bytes=file_bytes,
            content_type=content_type,
        )
        attach_file_to_lead(gym=gym, lead_id=str(lead_id), file_uuid=file_uuid)
    except KommoServiceError as exc:
        attachment.error_detail = str(exc)
        if attachment.upload_status == "pending":
            attachment.upload_status = "failed"
        if attachment.attach_status == "pending":
            attachment.attach_status = "failed"
        db.add(attachment)
        db.flush()
        raise

    attachment.file_uuid = file_uuid
    attachment.upload_status = "uploaded"
    attachment.attach_status = "attached"
    attachment.delivery_status = "attached"
    attachment.metadata_json = {
        **(attachment.metadata_json or {}),
        "drive_url": drive_url,
        "kommo_lead_id": str(lead_id),
        "content_type": content_type,
    }
    db.add(attachment)
    db.flush()

    return KommoNativeFileResult(
        attachment=attachment,
        file_uuid=file_uuid,
        file_name=attachment.file_name or file_name,
        upload_status=attachment.upload_status,
        attach_status=attachment.attach_status,
    )


def get_kommo_drive_url(gym: Gym) -> str:
    payload = _kommo_request(gym=gym, method="GET", path="/api/v4/account?with=drive_url")
    drive_url = _first_string(payload, "drive_url")
    if not drive_url:
        embedded = payload.get("_embedded") if isinstance(payload, dict) else None
        if isinstance(embedded, dict):
            drive_url = _first_string(embedded, "drive_url")
    if not drive_url:
        raise KommoServiceError("A Kommo nao retornou drive_url. Verifique permissoes de arquivos do token.")
    return str(drive_url).strip().rstrip("/")


def create_upload_session(
    *,
    gym: Gym,
    drive_url: str,
    file_name: str,
    file_size: int,
    content_type: str,
) -> dict[str, Any]:
    payload = {
        "file_name": file_name,
        "file_size": file_size,
        "content_type": content_type,
    }
    response = _kommo_drive_request(gym=gym, method="POST", url=f"{drive_url}/v1.0/sessions", json=payload)
    session_token = _first_string(response, "session_token", "token", "upload_token")
    upload_url = _first_string(response, "upload_url", "url")
    if not session_token and not upload_url:
        raise KommoServiceError("A Kommo nao retornou sessao de upload de arquivo.")
    return {"raw": response, "session_token": session_token, "upload_url": upload_url}


def upload_file_bytes(
    *,
    gym: Gym,
    drive_url: str,
    session: dict[str, Any],
    file_bytes: bytes,
    content_type: str,
) -> str:
    upload_urls: list[str] = []
    if session.get("upload_url"):
        upload_urls.append(str(session["upload_url"]))
    if session.get("session_token"):
        token = str(session["session_token"])
        upload_urls.extend(
            [
                f"{drive_url}/v1.0/upload/{token}",
                f"{drive_url}/v1.0/sessions/{token}/upload",
            ]
        )
    if not upload_urls:
        raise KommoServiceError("Sessao de upload da Kommo sem URL ou token.")

    headers = _kommo_auth_headers(gym)
    headers["Content-Type"] = content_type
    headers["Content-Range"] = f"bytes 0-{len(file_bytes) - 1}/{len(file_bytes)}"
    last_error: str | None = None
    payload: dict[str, Any] = {}
    for upload_url in upload_urls:
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(str(upload_url), headers=headers, content=file_bytes)
            response.raise_for_status()
            payload = response.json() if response.content else {}
            break
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip() or f"HTTP {exc.response.status_code}"
            if exc.response.status_code in {401, 403}:
                detail = "kommo_files_scope_missing: token sem permissao para upload de arquivos."
            last_error = detail[:500]
        except httpx.HTTPError as exc:
            last_error = f"Falha de rede ao subir arquivo na Kommo: {type(exc).__name__}."
    else:
        raise KommoServiceError(last_error or "Falha ao subir arquivo na Kommo.")

    file_uuid = _first_string(payload, "file_uuid", "uuid", "id")
    if not file_uuid:
        file_uuid = _search_nested_string(payload, {"file_uuid", "uuid"})
    if not file_uuid:
        raise KommoServiceError("A Kommo concluiu upload, mas nao retornou file_uuid.")
    return str(file_uuid)


def attach_file_to_lead(*, gym: Gym, lead_id: str, file_uuid: str) -> None:
    _kommo_request(
        gym=gym,
        method="PUT",
        path=f"/api/v4/leads/{lead_id}/files",
        json=[{"file_uuid": file_uuid}],
    )


def _get_existing_attachment(
    db: Session,
    *,
    gym_id: UUID,
    domain: str,
    source_type: str,
    source_id: str,
) -> KommoFileAttachment | None:
    return db.scalar(
        include_all_tenants(
            select(KommoFileAttachment).where(
                KommoFileAttachment.gym_id == gym_id,
                KommoFileAttachment.domain == domain,
                KommoFileAttachment.source_type == source_type,
                KommoFileAttachment.source_id == source_id,
            ),
            reason="kommo.files.fetch_attachment",
        )
    )


def _kommo_drive_request(
    *,
    gym: Gym,
    method: str,
    url: str,
    json: Any | None = None,
) -> dict[str, Any]:
    base_url = normalize_kommo_base_url(url)
    if not base_url:
        raise KommoServiceError("URL da Files API da Kommo invalida.")
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.request(method, base_url, headers=_kommo_auth_headers(gym), json=json)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or f"HTTP {exc.response.status_code}"
        if exc.response.status_code in {401, 403}:
            detail = "kommo_files_scope_missing: token sem permissao para Files API."
        raise KommoServiceError(detail[:500]) from exc
    except httpx.HTTPError as exc:
        raise KommoServiceError(f"Falha de rede com Files API da Kommo: {type(exc).__name__}.") from exc
    return response.json() if response.content else {}


def _kommo_auth_headers(gym: Gym) -> dict[str, str]:
    token = (gym.kommo_access_token_encrypted or "").strip()
    if not token:
        raise KommoServiceError("Kommo nao configurada para upload de arquivos.")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def _first_string(payload: Any, *keys: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return str(value)
    data = payload.get("data")
    if isinstance(data, dict):
        return _first_string(data, *keys)
    embedded = payload.get("_embedded")
    if isinstance(embedded, dict):
        return _first_string(embedded, *keys)
    return None


def _search_nested_string(payload: Any, keys: set[str]) -> str | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and value is not None:
                return str(value)
            found = _search_nested_string(value, keys)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _search_nested_string(item, keys)
            if found:
                return found
    return None
