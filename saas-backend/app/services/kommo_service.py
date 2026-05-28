from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.branding import PRODUCT_NAME
from app.database import include_all_tenants
from app.models import Gym, KommoDomainRoute, KommoMemberDomainLink, KommoMemberLink, KommoTrainerRoute, Lead, Member, MessageLog
from app.services.autopilot_event_service import record_event

KommoRoute = KommoDomainRoute | KommoTrainerRoute
TECHNICAL_MEMBER_DOMAINS = {"assessment", "body_composition", "student_ai"}


@dataclass
class KommoHandoffResult:
    status: str
    contact_id: str | None
    lead_id: str | None
    task_id: str | None
    detail: str | None = None


@dataclass
class KommoSalesbotOutboundResult:
    status: str
    contact_id: str | None
    lead_id: str | None
    message_log_id: UUID | None = None
    salesbot_id: str | None = None
    pdf_url: str | None = None
    kommo_file_uuid: str | None = None
    file_upload_status: str | None = None
    file_attach_status: str | None = None
    pdf_delivery_mode: str | None = None
    detail: str | None = None
    delivery_mode: str = "salesbot_outbound"
    fallback_available: bool = True
    route_kind: str | None = None
    trainer_user_id: UUID | None = None
    route_fallback_reason: str | None = None


@dataclass
class ResolvedKommoRoute:
    route: KommoRoute | None
    route_kind: str
    trainer_user_id: UUID | None = None
    fallback_reason: str | None = None


class KommoServiceError(RuntimeError):
    pass


class KommoSalesbotDispatchError(KommoServiceError):
    def __init__(self, message: str, *, result: KommoSalesbotOutboundResult):
        super().__init__(message)
        self.result = result


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
            "detail": f"Sem credenciais validas, o {PRODUCT_NAME} nao consegue entregar handoffs para a Kommo.",
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


def send_member_message_via_kommo_salesbot(
    db: Session,
    *,
    gym_id: UUID,
    member: Member,
    domain: str,
    message_text: str,
    source_type: str,
    source_id: str | UUID,
    pdf_url: str | None = None,
    pdf_bytes: bytes | None = None,
    pdf_filename: str | None = None,
    pdf_content_type: str = "application/pdf",
    pdf_delivery_mode: str | None = None,
    title: str | None = None,
) -> KommoSalesbotOutboundResult:
    gym = get_kommo_gym(db, gym_id)
    normalized_domain = _normalize_member_salesbot_domain(domain)
    if not is_kommo_ready(gym):
        raise KommoServiceError("Kommo nao configurada para esta academia.")
    if not member.phone:
        raise KommoServiceError("Aluno sem telefone cadastrado para envio pela Kommo.")

    resolved_route = _resolve_member_salesbot_route(
        db,
        gym_id=gym.id,
        member=member,
        domain=normalized_domain,
        pdf_url=pdf_url,
    )
    route = resolved_route.route
    selected_pdf_mode = _resolve_pdf_delivery_mode(route, override=pdf_delivery_mode, has_pdf=bool(pdf_bytes or pdf_url))
    _validate_salesbot_route(route, requires_pdf=bool(pdf_url and selected_pdf_mode == "link_only"))

    link = _get_member_domain_link(db, gym_id=gym.id, member_id=member.id, domain=normalized_domain)
    lead_id = link.kommo_lead_id if link else None
    contact_id = link.kommo_contact_id if link else None
    lead_title = title or f"{normalized_domain.replace('_', ' ').title()} - {member.full_name}"
    source_id_text = str(source_id)

    if not lead_id:
        payload = [
            _build_salesbot_lead_payload(
                route=route,
                member=member,
                title=lead_title,
                message_text=message_text,
                pdf_url=pdf_url,
                source_type=source_type,
                source_id=source_id_text,
            )
        ]
        created = _kommo_request(gym=gym, method="POST", path="/api/v4/leads/complex", json=payload)
        lead_id, contact_id = _extract_complex_lead_ids(created)
    else:
        _kommo_request(
            gym=gym,
            method="PATCH",
            path=f"/api/v4/leads/{lead_id}",
            json=_build_salesbot_lead_update_payload(
                route=route,
                title=lead_title,
                message_text=message_text,
                pdf_url=pdf_url,
                source_type=source_type,
                source_id=source_id_text,
            ),
        )

    now = datetime.now(tz=timezone.utc)
    if link is None:
        link = KommoMemberDomainLink(gym_id=gym.id, member_id=member.id, domain=normalized_domain)
    link.kommo_contact_id = contact_id
    link.kommo_lead_id = lead_id
    link.last_salesbot_at = now
    link.last_action_type = source_type
    db.add(link)

    # Keep the legacy one-lead link fresh so existing inbound webhook resolution keeps working.
    legacy_link = _get_member_link(db, gym_id=gym.id, member_id=member.id)
    if legacy_link is None:
        legacy_link = KommoMemberLink(gym_id=gym.id, member_id=member.id)
    legacy_link.kommo_contact_id = contact_id
    legacy_link.kommo_lead_id = lead_id
    legacy_link.last_handoff_at = now
    legacy_link.last_action_type = source_type
    db.add(legacy_link)

    native_file_uuid: str | None = None
    file_upload_status: str | None = None
    file_attach_status: str | None = None
    effective_delivery_mode = "salesbot_outbound"
    if pdf_bytes and selected_pdf_mode != "link_only":
        try:
            from app.services.kommo_file_service import upload_and_attach_pdf_to_lead

            native_file = upload_and_attach_pdf_to_lead(
                db,
                gym=gym,
                member=member,
                domain=normalized_domain,
                source_type=source_type,
                source_id=source_id_text,
                lead_id=str(lead_id),
                contact_id=contact_id,
                file_bytes=pdf_bytes,
                file_name=pdf_filename or f"{source_type}-{source_id_text}.pdf",
                content_type=pdf_content_type,
            )
            native_file_uuid = native_file.file_uuid
            file_upload_status = native_file.upload_status
            file_attach_status = native_file.attach_status
            effective_delivery_mode = "kommo_salesbot_native_file"
            _patch_salesbot_file_fields(
                gym=gym,
                route=route,
                lead_id=str(lead_id),
                file_uuid=native_file_uuid,
                file_name=native_file.file_name,
                note="PDF anexado nativamente pelo Cordex.",
            )
        except KommoServiceError as exc:
            if selected_pdf_mode == "native_file_preferred" and pdf_url:
                effective_delivery_mode = "kommo_salesbot_link_fallback"
                file_upload_status = "failed"
                file_attach_status = "fallback_link"
            else:
                failed_result = _record_salesbot_failure(
                    db,
                    gym=gym,
                    member=member,
                    route=route,
                    normalized_domain=normalized_domain,
                    route_kind=resolved_route.route_kind,
                    trainer_user_id=resolved_route.trainer_user_id,
                    route_fallback_reason=resolved_route.fallback_reason,
                    source_type=source_type,
                    source_id_text=source_id_text,
                    message_text=message_text,
                    contact_id=contact_id,
                    lead_id=lead_id,
                    pdf_url=pdf_url,
                    salesbot_error=str(exc),
                    delivery_mode="kommo_salesbot_native_file",
                    kommo_file_uuid=native_file_uuid,
                    file_upload_status=file_upload_status or "failed",
                    file_attach_status=file_attach_status or "failed",
                    pdf_delivery_mode=selected_pdf_mode,
                )
                raise KommoSalesbotDispatchError(str(exc), result=failed_result) from exc

    try:
        _run_salesbot(gym=gym, route=route, lead_id=lead_id)
    except KommoServiceError as exc:
        failed_result = _record_salesbot_failure(
            db,
            gym=gym,
            member=member,
            route=route,
            normalized_domain=normalized_domain,
            route_kind=resolved_route.route_kind,
            trainer_user_id=resolved_route.trainer_user_id,
            route_fallback_reason=resolved_route.fallback_reason,
            source_type=source_type,
            source_id_text=source_id_text,
            message_text=message_text,
            contact_id=contact_id,
            lead_id=lead_id,
            pdf_url=pdf_url,
            salesbot_error=str(exc),
            delivery_mode=effective_delivery_mode,
            kommo_file_uuid=native_file_uuid,
            file_upload_status=file_upload_status,
            file_attach_status=file_attach_status,
            pdf_delivery_mode=selected_pdf_mode,
        )
        raise KommoSalesbotDispatchError(str(exc), result=failed_result) from exc

    log = MessageLog(
        gym_id=gym.id,
        member_id=member.id,
        lead_id=None,
        channel="kommo",
        recipient=member.phone,
        template_name=f"kommo_{normalized_domain}",
        content=message_text,
        status="queued",
        direction="outbound",
        event_type="kommo_salesbot_outbound",
        provider_message_id=str(route.salesbot_id),
        extra_data={
            "delivery_mode": effective_delivery_mode,
            "domain": normalized_domain,
            "source_type": source_type,
            "source_id": source_id_text,
            "pdf_url": pdf_url,
            "kommo_file_uuid": native_file_uuid,
            "file_upload_status": file_upload_status,
            "file_attach_status": file_attach_status,
            "pdf_delivery_mode": selected_pdf_mode,
            "kommo_contact_id": contact_id,
            "kommo_lead_id": lead_id,
            "salesbot_id": route.salesbot_id,
            "pipeline_id": route.pipeline_id,
            "stage_id": route.stage_id,
            "channel_source_id": route.channel_source_id,
            "kommo_route_kind": resolved_route.route_kind,
            "kommo_trainer_user_id": str(resolved_route.trainer_user_id) if resolved_route.trainer_user_id else None,
            "kommo_route_fallback_reason": resolved_route.fallback_reason,
        },
    )
    db.add(log)
    db.flush()

    record_event(
        db,
        gym_id=gym.id,
        event_type="kommo_salesbot_outbound_queued",
        source="kommo_salesbot",
        member_id=member.id,
        metadata={
            "domain": normalized_domain,
            "source_type": source_type,
            "source_id": source_id_text,
            "message_log_id": str(log.id),
            "kommo_contact_id": contact_id,
            "kommo_lead_id": lead_id,
            "salesbot_id": route.salesbot_id,
            "pdf_url": pdf_url,
            "kommo_file_uuid": native_file_uuid,
            "file_upload_status": file_upload_status,
            "file_attach_status": file_attach_status,
            "pdf_delivery_mode": selected_pdf_mode,
            "kommo_route_kind": resolved_route.route_kind,
            "kommo_trainer_user_id": str(resolved_route.trainer_user_id) if resolved_route.trainer_user_id else None,
            "kommo_route_fallback_reason": resolved_route.fallback_reason,
        },
        deduplication_key=f"kommo:salesbot:{log.id}",
        flush=False,
    )

    return KommoSalesbotOutboundResult(
        status="queued",
        contact_id=contact_id,
        lead_id=lead_id,
        message_log_id=log.id,
        salesbot_id=route.salesbot_id,
        pdf_url=pdf_url,
        kommo_file_uuid=native_file_uuid,
        file_upload_status=file_upload_status,
        file_attach_status=file_attach_status,
        pdf_delivery_mode=selected_pdf_mode,
        detail=_salesbot_success_detail(effective_delivery_mode),
        delivery_mode=effective_delivery_mode,
        route_kind=resolved_route.route_kind,
        trainer_user_id=resolved_route.trainer_user_id,
        route_fallback_reason=resolved_route.fallback_reason,
    )


def send_lead_message_via_kommo_salesbot(
    db: Session,
    *,
    gym_id: UUID,
    lead: Lead,
    domain: str,
    message_text: str,
    source_type: str,
    source_id: str | UUID,
    title: str | None = None,
) -> KommoSalesbotOutboundResult:
    gym = get_kommo_gym(db, gym_id)
    normalized_domain = _normalize_domain(domain)
    if not is_kommo_ready(gym):
        raise KommoServiceError("Kommo nao configurada para esta academia.")
    if not lead.phone:
        raise KommoServiceError("Lead sem telefone cadastrado para envio pela Kommo.")

    route = _get_domain_route(db, gym_id=gym.id, domain=normalized_domain)
    _validate_salesbot_route(route, requires_pdf=False)
    lead_title = title or f"{normalized_domain.replace('_', ' ').title()} - {lead.full_name}"
    source_id_text = str(source_id)
    payload = [
        _build_salesbot_lead_payload_for_lead(
            route=route,
            lead=lead,
            title=lead_title,
            message_text=message_text,
            source_type=source_type,
            source_id=source_id_text,
        )
    ]
    created = _kommo_request(gym=gym, method="POST", path="/api/v4/leads/complex", json=payload)
    kommo_lead_id, kommo_contact_id = _extract_complex_lead_ids(created)

    try:
        _run_salesbot(gym=gym, route=route, lead_id=kommo_lead_id)
    except KommoServiceError as exc:
        failed_log = MessageLog(
            gym_id=gym.id,
            member_id=None,
            lead_id=lead.id,
            channel="kommo",
            recipient=lead.phone,
            template_name=f"kommo_{normalized_domain}",
            content=message_text,
            status="failed",
            direction="outbound",
            event_type="kommo_salesbot_outbound_failed",
            provider_message_id=str(route.salesbot_id) if route else None,
            error_detail=str(exc),
            extra_data={
                "delivery_mode": "salesbot_outbound",
                "domain": normalized_domain,
                "source_type": source_type,
                "source_id": source_id_text,
                "kommo_contact_id": kommo_contact_id,
                "kommo_lead_id": kommo_lead_id,
                "salesbot_id": route.salesbot_id if route else None,
                "pipeline_id": route.pipeline_id if route else None,
                "stage_id": route.stage_id if route else None,
                "kommo_route_kind": "domain_route",
            },
        )
        db.add(failed_log)
        db.flush()
        failed_result = KommoSalesbotOutboundResult(
            status="failed",
            contact_id=kommo_contact_id,
            lead_id=kommo_lead_id,
            message_log_id=failed_log.id,
            salesbot_id=route.salesbot_id if route else None,
            detail=str(exc),
            delivery_mode="salesbot_outbound",
            route_kind="domain_route",
        )
        record_event(
            db,
            gym_id=gym.id,
            event_type="kommo_salesbot_outbound_failed",
            source="kommo_salesbot",
            lead_id=lead.id,
            metadata={
                "domain": normalized_domain,
                "source_type": source_type,
                "source_id": source_id_text,
                "message_log_id": str(failed_log.id),
                "kommo_contact_id": kommo_contact_id,
                "kommo_lead_id": kommo_lead_id,
                "salesbot_id": route.salesbot_id if route else None,
                "error": str(exc),
                "kommo_route_kind": "domain_route",
            },
            deduplication_key=f"kommo:salesbot:lead:failed:{failed_log.id}",
            flush=False,
        )
        raise KommoSalesbotDispatchError(str(exc), result=failed_result) from exc

    log = MessageLog(
        gym_id=gym.id,
        member_id=None,
        lead_id=lead.id,
        channel="kommo",
        recipient=lead.phone,
        template_name=f"kommo_{normalized_domain}",
        content=message_text,
        status="queued",
        direction="outbound",
        event_type="kommo_salesbot_outbound",
        provider_message_id=str(route.salesbot_id),
        extra_data={
            "delivery_mode": "salesbot_outbound",
            "domain": normalized_domain,
            "source_type": source_type,
            "source_id": source_id_text,
            "kommo_contact_id": kommo_contact_id,
            "kommo_lead_id": kommo_lead_id,
            "salesbot_id": route.salesbot_id,
            "pipeline_id": route.pipeline_id,
            "stage_id": route.stage_id,
            "channel_source_id": route.channel_source_id,
            "kommo_route_kind": "domain_route",
        },
    )
    db.add(log)
    db.flush()
    record_event(
        db,
        gym_id=gym.id,
        event_type="kommo_salesbot_outbound_queued",
        source="kommo_salesbot",
        lead_id=lead.id,
        metadata={
            "domain": normalized_domain,
            "source_type": source_type,
            "source_id": source_id_text,
            "message_log_id": str(log.id),
            "kommo_contact_id": kommo_contact_id,
            "kommo_lead_id": kommo_lead_id,
            "salesbot_id": route.salesbot_id,
            "kommo_route_kind": "domain_route",
        },
        deduplication_key=f"kommo:salesbot:lead:{log.id}",
        flush=False,
    )
    return KommoSalesbotOutboundResult(
        status="queued",
        contact_id=kommo_contact_id,
        lead_id=kommo_lead_id,
        message_log_id=log.id,
        salesbot_id=route.salesbot_id,
        detail=_salesbot_success_detail("salesbot_outbound"),
        delivery_mode="salesbot_outbound",
        route_kind="domain_route",
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


def find_member_link_by_kommo_ids(
    db: Session,
    *,
    kommo_lead_id: str | None = None,
    kommo_contact_id: str | None = None,
) -> KommoMemberLink | KommoMemberDomainLink | None:
    filters = []
    domain_filters = []
    if kommo_lead_id:
        filters.append(KommoMemberLink.kommo_lead_id == str(kommo_lead_id))
        domain_filters.append(KommoMemberDomainLink.kommo_lead_id == str(kommo_lead_id))
    if kommo_contact_id:
        filters.append(KommoMemberLink.kommo_contact_id == str(kommo_contact_id))
        domain_filters.append(KommoMemberDomainLink.kommo_contact_id == str(kommo_contact_id))
    if not filters:
        return None
    domain_link = db.scalar(
        include_all_tenants(
            select(KommoMemberDomainLink).where(or_(*domain_filters)).order_by(KommoMemberDomainLink.updated_at.desc()).limit(1),
            reason="kommo.find_member_domain_link_by_external_id",
        )
    )
    if domain_link is not None:
        return domain_link
    return db.scalar(
        include_all_tenants(
            select(KommoMemberLink).where(or_(*filters)).order_by(KommoMemberLink.updated_at.desc()).limit(1),
            reason="kommo.find_member_link_by_external_id",
        )
    )


def _get_domain_route(db: Session, *, gym_id: UUID, domain: str) -> KommoDomainRoute | None:
    return db.scalar(
        select(KommoDomainRoute).where(
            KommoDomainRoute.gym_id == gym_id,
            KommoDomainRoute.domain == domain,
        )
    )


def _get_trainer_route(db: Session, *, gym_id: UUID, trainer_user_id: UUID) -> KommoTrainerRoute | None:
    return db.scalar(
        select(KommoTrainerRoute).where(
            KommoTrainerRoute.gym_id == gym_id,
            KommoTrainerRoute.trainer_user_id == trainer_user_id,
        )
    )


def _resolve_member_salesbot_route(
    db: Session,
    *,
    gym_id: UUID,
    member: Member,
    domain: str,
    pdf_url: str | None,
) -> ResolvedKommoRoute:
    domain_route = _get_domain_route(db, gym_id=gym_id, domain=domain)
    if domain not in TECHNICAL_MEMBER_DOMAINS:
        return ResolvedKommoRoute(route=domain_route, route_kind="domain_route")

    trainer_user_id = getattr(member, "assigned_user_id", None)
    if trainer_user_id:
        trainer_route = _get_trainer_route(db, gym_id=gym_id, trainer_user_id=trainer_user_id)
        if _is_salesbot_route_ready(trainer_route, requires_pdf=_route_requires_link_pdf(trainer_route, pdf_url=pdf_url)):
            return ResolvedKommoRoute(
                route=trainer_route,
                route_kind="trainer_route",
                trainer_user_id=trainer_user_id,
            )
        fallback_reason = _trainer_route_fallback_reason(trainer_route, pdf_url=pdf_url)
    else:
        fallback_reason = "no_assigned_trainer"

    return ResolvedKommoRoute(
        route=domain_route,
        route_kind="coordination_fallback",
        trainer_user_id=trainer_user_id,
        fallback_reason=fallback_reason,
    )


def _get_member_domain_link(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    domain: str,
) -> KommoMemberDomainLink | None:
    return db.scalar(
        select(KommoMemberDomainLink).where(
            KommoMemberDomainLink.gym_id == gym_id,
            KommoMemberDomainLink.member_id == member_id,
            KommoMemberDomainLink.domain == domain,
        )
    )


def _validate_salesbot_route(route: KommoRoute | None, *, requires_pdf: bool) -> None:
    if route is None or not route.is_enabled:
        raise KommoServiceError("Rota Kommo deste dominio nao configurada ou desativada.")
    if not _safe_int(route.pipeline_id):
        raise KommoServiceError("Rota Kommo sem pipeline_id valido.")
    if not _safe_int(route.stage_id):
        raise KommoServiceError("Rota Kommo sem stage_id valido.")
    if not _safe_int(route.salesbot_id):
        raise KommoServiceError("Rota Kommo sem salesbot_id valido.")
    if not _safe_int(route.message_field_id):
        raise KommoServiceError("Rota Kommo sem campo customizado de mensagem.")
    if requires_pdf and not _safe_int(route.pdf_url_field_id):
        raise KommoServiceError("Rota Kommo sem campo customizado de PDF.")


def _is_salesbot_route_ready(route: KommoRoute | None, *, requires_pdf: bool = False) -> bool:
    if route is None or not route.is_enabled:
        return False
    return bool(
        _safe_int(route.pipeline_id)
        and _safe_int(route.stage_id)
        and _safe_int(route.salesbot_id)
        and _safe_int(route.message_field_id)
        and (not requires_pdf or _safe_int(route.pdf_url_field_id))
    )


def _route_requires_link_pdf(route: KommoRoute | None, *, pdf_url: str | None) -> bool:
    if not pdf_url:
        return False
    mode = str(getattr(route, "pdf_delivery_mode", None) or "native_file_required").strip().lower()
    return mode == "link_only"


def _trainer_route_fallback_reason(route: KommoRoute | None, *, pdf_url: str | None) -> str:
    if route is None:
        return "trainer_route_missing"
    if not route.is_enabled:
        return "trainer_route_disabled"
    if not _is_salesbot_route_ready(route, requires_pdf=_route_requires_link_pdf(route, pdf_url=pdf_url)):
        return "trainer_route_incomplete"
    return "trainer_route_unavailable"


def _resolve_pdf_delivery_mode(
    route: KommoRoute | None,
    *,
    override: str | None,
    has_pdf: bool,
) -> str | None:
    if not has_pdf:
        return None
    raw = override or getattr(route, "pdf_delivery_mode", None) or "native_file_required"
    normalized = str(raw).strip().lower()
    if normalized not in {"native_file_required", "native_file_preferred", "link_only"}:
        return "native_file_required"
    return normalized


def _build_salesbot_lead_payload(
    *,
    route: KommoRoute,
    member: Member,
    title: str,
    message_text: str,
    pdf_url: str | None,
    source_type: str,
    source_id: str,
) -> dict[str, Any]:
    contact_payload: dict[str, Any] = {"name": member.full_name}
    contact_fields: list[dict[str, Any]] = []
    if member.phone:
        contact_fields.append({"field_code": "PHONE", "values": [{"value": member.phone, "enum_code": "WORK"}]})
    if member.email:
        contact_fields.append({"field_code": "EMAIL", "values": [{"value": member.email, "enum_code": "WORK"}]})
    if contact_fields:
        contact_payload["custom_fields_values"] = contact_fields

    payload = _build_salesbot_lead_update_payload(
        route=route,
        title=title,
        message_text=message_text,
        pdf_url=pdf_url,
        source_type=source_type,
        source_id=source_id,
    )
    embedded = payload.setdefault("_embedded", {})
    embedded["contacts"] = [contact_payload]
    return payload


def _build_salesbot_lead_payload_for_lead(
    *,
    route: KommoRoute,
    lead: Lead,
    title: str,
    message_text: str,
    source_type: str,
    source_id: str,
) -> dict[str, Any]:
    contact_payload: dict[str, Any] = {"name": lead.full_name}
    contact_fields: list[dict[str, Any]] = []
    if lead.phone:
        contact_fields.append({"field_code": "PHONE", "values": [{"value": lead.phone, "enum_code": "WORK"}]})
    if lead.email:
        contact_fields.append({"field_code": "EMAIL", "values": [{"value": lead.email, "enum_code": "WORK"}]})
    if contact_fields:
        contact_payload["custom_fields_values"] = contact_fields

    payload = _build_salesbot_lead_update_payload(
        route=route,
        title=title,
        message_text=message_text,
        pdf_url=None,
        source_type=source_type,
        source_id=source_id,
    )
    embedded = payload.setdefault("_embedded", {})
    embedded["contacts"] = [contact_payload]
    return payload


def _build_salesbot_lead_update_payload(
    *,
    route: KommoRoute,
    title: str,
    message_text: str,
    pdf_url: str | None,
    source_type: str,
    source_id: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": title[:255],
        "pipeline_id": int(route.pipeline_id),
        "status_id": int(route.stage_id),
    }
    responsible_user_id = _safe_int(route.responsible_user_id)
    if responsible_user_id is not None:
        payload["responsible_user_id"] = responsible_user_id

    custom_fields = [
        _custom_field_by_id(route.message_field_id, message_text),
        _custom_field_by_id(route.pdf_url_field_id, pdf_url) if pdf_url else None,
        _custom_field_by_id(route.source_type_field_id, source_type) if source_type else None,
        _custom_field_by_id(route.source_id_field_id, source_id) if source_id else None,
    ]
    payload["custom_fields_values"] = [field for field in custom_fields if field is not None]
    tags = [str(tag).strip() for tag in (route.tags or []) if str(tag).strip()]
    if tags:
        payload.setdefault("_embedded", {})["tags"] = [{"name": tag[:255]} for tag in tags]
    return payload


def _patch_salesbot_file_fields(
    *,
    gym: Gym,
    route: KommoRoute | None,
    lead_id: str,
    file_uuid: str,
    file_name: str,
    note: str,
) -> None:
    if route is None:
        return
    custom_fields = [
        _custom_field_by_id(getattr(route, "file_uuid_field_id", None), file_uuid),
        _custom_field_by_id(getattr(route, "file_name_field_id", None), file_name),
        _custom_field_by_id(getattr(route, "file_attachment_note_field_id", None), note),
    ]
    fields = [field for field in custom_fields if field is not None]
    if not fields:
        return
    _kommo_request(
        gym=gym,
        method="PATCH",
        path=f"/api/v4/leads/{lead_id}",
        json={"custom_fields_values": fields},
    )


def _custom_field_by_id(field_id: str | None, value: str | None) -> dict[str, Any] | None:
    normalized_field_id = _safe_int(field_id)
    if normalized_field_id is None or value is None:
        return None
    return {"field_id": normalized_field_id, "values": [{"value": str(value)}]}


def _run_salesbot(*, gym: Gym, route: KommoRoute, lead_id: str) -> None:
    salesbot_id = _safe_int(route.salesbot_id)
    if salesbot_id is None:
        raise KommoServiceError("Salesbot invalido para esta rota Kommo.")
    _kommo_request(
        gym=gym,
        method="POST",
        path=f"/api/v4/bots/{salesbot_id}/run",
        json=[{"entity_id": int(lead_id), "entity_type": "leads"}],
    )


def _record_salesbot_failure(
    db: Session,
    *,
    gym: Gym,
    member: Member,
    route: KommoRoute | None,
    normalized_domain: str,
    route_kind: str | None,
    trainer_user_id: UUID | None,
    route_fallback_reason: str | None,
    source_type: str,
    source_id_text: str,
    message_text: str,
    contact_id: str | None,
    lead_id: str | None,
    pdf_url: str | None,
    salesbot_error: str,
    delivery_mode: str,
    kommo_file_uuid: str | None,
    file_upload_status: str | None,
    file_attach_status: str | None,
    pdf_delivery_mode: str | None,
) -> KommoSalesbotOutboundResult:
    failed_log = MessageLog(
        gym_id=gym.id,
        member_id=member.id,
        lead_id=None,
        channel="kommo",
        recipient=member.phone,
        template_name=f"kommo_{normalized_domain}",
        content=message_text,
        status="failed",
        direction="outbound",
        event_type="kommo_salesbot_outbound_failed",
        provider_message_id=str(route.salesbot_id) if route else None,
        error_detail=salesbot_error,
        extra_data={
            "delivery_mode": delivery_mode,
            "domain": normalized_domain,
            "source_type": source_type,
            "source_id": source_id_text,
            "pdf_url": pdf_url,
            "kommo_file_uuid": kommo_file_uuid,
            "file_upload_status": file_upload_status,
            "file_attach_status": file_attach_status,
            "pdf_delivery_mode": pdf_delivery_mode,
            "kommo_contact_id": contact_id,
            "kommo_lead_id": lead_id,
            "salesbot_id": route.salesbot_id if route else None,
            "pipeline_id": route.pipeline_id if route else None,
            "stage_id": route.stage_id if route else None,
            "channel_source_id": route.channel_source_id if route else None,
            "kommo_route_kind": route_kind,
            "kommo_trainer_user_id": str(trainer_user_id) if trainer_user_id else None,
            "kommo_route_fallback_reason": route_fallback_reason,
        },
    )
    db.add(failed_log)
    db.flush()
    record_event(
        db,
        gym_id=gym.id,
        event_type="kommo_salesbot_outbound_failed",
        source="kommo_salesbot",
        member_id=member.id,
        metadata={
            "domain": normalized_domain,
            "source_type": source_type,
            "source_id": source_id_text,
            "message_log_id": str(failed_log.id),
            "kommo_contact_id": contact_id,
            "kommo_lead_id": lead_id,
            "salesbot_id": route.salesbot_id if route else None,
            "pdf_url": pdf_url,
            "kommo_file_uuid": kommo_file_uuid,
            "file_upload_status": file_upload_status,
            "file_attach_status": file_attach_status,
            "pdf_delivery_mode": pdf_delivery_mode,
            "error": salesbot_error,
            "kommo_route_kind": route_kind,
            "kommo_trainer_user_id": str(trainer_user_id) if trainer_user_id else None,
            "kommo_route_fallback_reason": route_fallback_reason,
        },
        deduplication_key=f"kommo:salesbot_failed:{failed_log.id}",
        flush=False,
    )
    return KommoSalesbotOutboundResult(
        status="failed",
        contact_id=contact_id,
        lead_id=lead_id,
        message_log_id=failed_log.id,
        salesbot_id=route.salesbot_id if route else None,
        pdf_url=pdf_url,
        kommo_file_uuid=kommo_file_uuid,
        file_upload_status=file_upload_status,
        file_attach_status=file_attach_status,
        pdf_delivery_mode=pdf_delivery_mode,
        detail=salesbot_error,
        delivery_mode=delivery_mode,
        route_kind=route_kind,
        trainer_user_id=trainer_user_id,
        route_fallback_reason=route_fallback_reason,
    )


def _salesbot_success_detail(delivery_mode: str) -> str:
    if delivery_mode == "kommo_salesbot_native_file":
        return "PDF anexado nativamente na Kommo e Salesbot acionado. Aguardando resposta pelo webhook."
    if delivery_mode == "kommo_salesbot_link_fallback":
        return "Upload nativo falhou; Salesbot acionado com link temporario de PDF. Aguardando resposta pelo webhook."
    return "Salesbot da Kommo acionado. Aguardando resposta pelo webhook."


def _normalize_domain(value: str) -> str:
    normalized = (value or "").strip().lower().replace("-", "_")
    allowed = {"retention", "onboarding", "assessment", "body_composition", "finance", "sales", "student_ai", "support"}
    if normalized not in allowed:
        raise KommoServiceError(f"Dominio Kommo invalido: {value}")
    return normalized


def _normalize_member_salesbot_domain(value: str) -> str:
    normalized = (value or "").strip().lower().replace("-", "_")
    if normalized in {"trainer", "coach", "training"}:
        return "assessment"
    return _normalize_domain(normalized)


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
        text_lines.extend(["", f"{PRODUCT_NAME}: {ai_gym_profile_url}"])
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
