from __future__ import annotations

import hashlib
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_request_context, require_roles
from app.database import get_db, set_current_gym_id
from app.models import Lead, Member, MessageLog, RoleEnum, User
from app.schemas.kommo import KommoNativeFileUploadTestRequest, KommoNativeFileUploadTestResponse, KommoSendMessageRequest, KommoSendMessageResponse
from app.services.audit_service import log_audit_event
from app.services.ai_service_agent_service import process_kommo_inbound_for_ai_agent
from app.services.autopilot_event_service import record_event
from app.services.autopilot_resolver_service import resolve_event
from app.services.body_composition_actuar_sync_service import get_body_composition_evaluation_or_404
from app.services.body_composition_delivery_service import (
    generate_body_composition_pdf,
    generate_body_composition_technical_pdf,
    get_previous_body_composition_evaluation,
)
from app.services.kommo_service import (
    KommoSalesbotDispatchError,
    KommoServiceError,
    find_member_link_by_kommo_ids,
    get_kommo_gym,
    send_lead_message_via_kommo_salesbot,
    send_member_message_via_kommo_salesbot,
)
from app.services.kommo_file_service import attach_file_to_lead, create_upload_session, get_kommo_drive_url, upload_file_bytes
from app.services.member_service import get_member_or_404
from app.services.public_report_link_service import create_body_composition_report_public_url
from app.services.student_personal_ai_service import process_kommo_inbound_for_student_personal_ai

router = APIRouter(prefix="/kommo", tags=["kommo"])


@router.post("/test-native-file-upload", response_model=KommoNativeFileUploadTestResponse)
def test_native_file_upload_endpoint(
    payload: KommoNativeFileUploadTestRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> KommoNativeFileUploadTestResponse:
    gym = get_kommo_gym(db, current_user.gym_id)
    file_bytes = b"%PDF-1.4\n% Cordex Kommo upload test\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    try:
        drive_url = get_kommo_drive_url(gym)
        session = create_upload_session(
            gym=gym,
            drive_url=drive_url,
            file_name="cordex-kommo-upload-test.pdf",
            file_size=len(file_bytes),
            content_type="application/pdf",
        )
        file_uuid = upload_file_bytes(
            gym=gym,
            drive_url=drive_url,
            session=session,
            file_bytes=file_bytes,
            content_type="application/pdf",
        )
        attach_status = "skipped_no_lead"
        if payload.lead_id:
            attach_file_to_lead(gym=gym, lead_id=payload.lead_id, file_uuid=file_uuid)
            attach_status = "attached"
    except KommoServiceError as exc:
        return KommoNativeFileUploadTestResponse(
            success=False,
            message="Nao foi possivel validar upload nativo na Kommo.",
            upload_status="failed",
            attach_status="failed" if payload.lead_id else None,
            detail=str(exc),
        )

    return KommoNativeFileUploadTestResponse(
        success=True,
        message="Upload nativo de arquivo validado na Kommo.",
        file_uuid=file_uuid,
        upload_status="uploaded",
        attach_status=attach_status,
    )


@router.post("/send-message", response_model=KommoSendMessageResponse)
def send_kommo_message_endpoint(
    request: Request,
    payload: KommoSendMessageRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> KommoSendMessageResponse:
    if bool(payload.member_id) == bool(payload.lead_id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe member_id ou lead_id, mas nao ambos.")

    member = get_member_or_404(db, payload.member_id, gym_id=current_user.gym_id) if payload.member_id else None
    lead = None
    if payload.lead_id:
        lead = db.get(Lead, payload.lead_id)
        if lead is None or lead.gym_id != current_user.gym_id or lead.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead nao encontrado")

    pdf_url = None
    pdf_bytes = None
    pdf_filename = None
    source_id_text = str(payload.source_id)
    pdf_delivery_mode = payload.pdf_delivery_mode or ("native_file_required" if payload.pdf_kind else None)
    if payload.pdf_kind and not member:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Envio de PDF pela Kommo exige member_id.")
    if payload.pdf_kind and payload.source_type == "body_composition":
        try:
            evaluation_id = payload.source_id if isinstance(payload.source_id, UUID) else UUID(str(payload.source_id))
            evaluation = get_body_composition_evaluation_or_404(
                db,
                gym_id=current_user.gym_id,
                member_id=member.id,
                evaluation_id=evaluation_id,
            )
            previous_evaluation = get_previous_body_composition_evaluation(
                db,
                gym_id=current_user.gym_id,
                member_id=member.id,
                evaluation_id=evaluation_id,
            )
            pdf_bytes, pdf_filename = (
                generate_body_composition_technical_pdf(member, evaluation, previous_evaluation)
                if payload.pdf_kind == "technical"
                else generate_body_composition_pdf(member, evaluation, previous_evaluation)
            )
            if pdf_delivery_mode in {"native_file_preferred", "link_only"}:
                pdf_url = create_body_composition_report_public_url(
                    gym_id=current_user.gym_id,
                    member_id=member.id,
                    evaluation_id=evaluation_id,
                    pdf_kind=payload.pdf_kind,
                )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    try:
        if member:
            result = send_member_message_via_kommo_salesbot(
                db,
                gym_id=current_user.gym_id,
                member=member,
                domain=payload.domain,
                message_text=payload.message_text,
                source_type=payload.source_type,
                source_id=source_id_text,
                pdf_url=pdf_url,
                pdf_bytes=pdf_bytes,
                pdf_filename=pdf_filename,
                pdf_delivery_mode=pdf_delivery_mode,
                title=f"{payload.domain.replace('_', ' ').title()} - {member.full_name}",
            )
        else:
            result = send_lead_message_via_kommo_salesbot(
                db,
                gym_id=current_user.gym_id,
                lead=lead,
                domain=payload.domain,
                message_text=payload.message_text,
                source_type=payload.source_type,
                source_id=source_id_text,
                title=f"{payload.domain.replace('_', ' ').title()} - {lead.full_name}",
            )
    except KommoSalesbotDispatchError as exc:
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (KommoServiceError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    context = get_request_context(request)
    log_audit_event(
        db,
        action="kommo_salesbot_message_queued",
        entity="kommo",
        user=current_user,
        member_id=member.id if member else None,
        entity_id=member.id if member else lead.id,
        details={
            "local_lead_id": str(lead.id) if lead else None,
            "domain": payload.domain,
            "source_type": payload.source_type,
            "source_id": source_id_text,
            "status": result.status,
            "lead_id": result.lead_id,
            "contact_id": result.contact_id,
            "salesbot_id": result.salesbot_id,
            "pdf_url": result.pdf_url,
            "kommo_file_uuid": result.kommo_file_uuid,
            "pdf_delivery_mode": result.pdf_delivery_mode,
            "route_kind": getattr(result, "route_kind", None),
            "trainer_user_id": str(result.trainer_user_id) if getattr(result, "trainer_user_id", None) else None,
            "route_fallback_reason": getattr(result, "route_fallback_reason", None),
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return KommoSendMessageResponse(
        status=result.status,
        delivery_mode=result.delivery_mode,
        detail=result.detail,
        member_id=member.id if member else None,
        local_lead_id=lead.id if lead else None,
        source_type=payload.source_type,
        source_id=source_id_text,
        domain=payload.domain,
        lead_id=result.lead_id,
        contact_id=result.contact_id,
        message_log_id=result.message_log_id,
        salesbot_id=result.salesbot_id,
        pdf_url=result.pdf_url,
        kommo_file_uuid=result.kommo_file_uuid,
        file_upload_status=result.file_upload_status,
        file_attach_status=result.file_attach_status,
        pdf_delivery_mode=result.pdf_delivery_mode,
        fallback_available=result.fallback_available,
        route_kind=getattr(result, "route_kind", None),
        trainer_user_id=getattr(result, "trainer_user_id", None),
        route_fallback_reason=getattr(result, "route_fallback_reason", None),
    )


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
    student_personal_draft = process_kommo_inbound_for_student_personal_ai(
        db,
        gym_id=link.gym_id,
        member=member,
        message_text=content,
        event=event,
        payload=payload,
        message_log_id=log.id,
        kommo_contact_id=link.kommo_contact_id,
        kommo_lead_id=link.kommo_lead_id,
        flush=False,
    )
    agent_draft = None
    if student_personal_draft is None:
        agent_draft = process_kommo_inbound_for_ai_agent(
            db,
            gym_id=link.gym_id,
            member=member,
            message_text=content,
            event=event,
            message_log_id=log.id,
            kommo_contact_id=link.kommo_contact_id,
            kommo_lead_id=link.kommo_lead_id,
            flush=False,
        )
    db.commit()
    return {
        "processed": True,
        "event_id": str(event.id),
        "resolver": result,
        "ai_service_agent": {"draft_id": str(agent_draft.id), "status": agent_draft.status} if agent_draft else None,
        "student_personal_ai": {"draft_id": str(student_personal_draft.id), "status": student_personal_draft.status}
        if student_personal_draft
        else None,
    }


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
