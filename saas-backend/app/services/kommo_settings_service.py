from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import include_all_tenants
from app.models import Gym, KommoDomainRoute
from app.schemas.settings import (
    KommoConnectionTestResult,
    KommoDomainRouteRead,
    KommoSettingsRead,
    KommoSettingsUpdate,
)
from app.services.kommo_service import (
    is_kommo_ready,
    normalize_kommo_base_url,
    test_kommo_connection,
)


def get_kommo_settings(db: Session, *, gym_id: UUID) -> KommoSettingsRead:
    gym = _get_gym_or_404(db, gym_id=gym_id)
    return serialize_kommo_settings(gym)


def update_kommo_settings(
    db: Session,
    *,
    gym_id: UUID,
    payload: KommoSettingsUpdate,
) -> KommoSettingsRead:
    gym = _get_gym_or_404(db, gym_id=gym_id)
    gym.kommo_enabled = payload.kommo_enabled
    gym.kommo_base_url = normalize_kommo_base_url(payload.kommo_base_url)
    gym.kommo_default_pipeline_id = _normalize_text(payload.kommo_default_pipeline_id)
    gym.kommo_default_stage_id = _normalize_text(payload.kommo_default_stage_id)
    gym.kommo_default_responsible_user_id = _normalize_text(payload.kommo_default_responsible_user_id)
    if payload.primary_message_channel is not None:
        gym.primary_message_channel = payload.primary_message_channel
    if payload.kommo_operator_confirmed_send_enabled is not None:
        gym.kommo_operator_confirmed_send_enabled = payload.kommo_operator_confirmed_send_enabled
    if payload.kommo_auto_close_enabled is not None:
        gym.kommo_auto_close_enabled = payload.kommo_auto_close_enabled
    if payload.kommo_fallback_channel is not None:
        gym.kommo_fallback_channel = payload.kommo_fallback_channel

    if payload.clear_access_token:
        gym.kommo_access_token_encrypted = None
    elif payload.kommo_access_token is not None:
        normalized_token = payload.kommo_access_token.strip()
        if normalized_token:
            gym.kommo_access_token_encrypted = normalized_token

    db.add(gym)
    if payload.domain_routes is not None:
        _upsert_domain_routes(db, gym_id=gym.id, payloads=payload.domain_routes)
    db.flush()
    db.expire(gym, ["kommo_domain_routes"])
    return serialize_kommo_settings(gym)


def test_kommo_connection_for_gym(db: Session, *, gym_id: UUID) -> KommoConnectionTestResult:
    payload = test_kommo_connection(db, gym_id=gym_id)
    return KommoConnectionTestResult(
        success=bool(payload.get("success")),
        automatic_handoff_ready=bool(payload.get("success")),
        message=str(payload.get("message") or "Nao foi possivel validar a conexao com a Kommo."),
        detail=payload.get("detail"),
        base_url=payload.get("base_url"),
    )


def serialize_kommo_settings(gym: Gym) -> KommoSettingsRead:
    return KommoSettingsRead(
        kommo_enabled=bool(gym.kommo_enabled),
        kommo_base_url=normalize_kommo_base_url(gym.kommo_base_url),
        kommo_has_access_token=bool(_normalize_text(gym.kommo_access_token_encrypted)),
        kommo_default_pipeline_id=_normalize_text(gym.kommo_default_pipeline_id),
        kommo_default_stage_id=_normalize_text(gym.kommo_default_stage_id),
        kommo_default_responsible_user_id=_normalize_text(gym.kommo_default_responsible_user_id),
        automatic_handoff_ready=is_kommo_ready(gym),
        primary_message_channel=str(getattr(gym, "primary_message_channel", None) or "whatsapp"),
        kommo_operator_confirmed_send_enabled=bool(getattr(gym, "kommo_operator_confirmed_send_enabled", True)),
        kommo_auto_close_enabled=bool(getattr(gym, "kommo_auto_close_enabled", True)),
        kommo_fallback_channel=str(getattr(gym, "kommo_fallback_channel", None) or "whatsapp"),
        domain_routes=_serialize_domain_routes(gym),
    )


def _get_gym_or_404(db: Session, *, gym_id: UUID) -> Gym:
    gym = db.scalar(include_all_tenants(select(Gym).where(Gym.id == gym_id), reason="kommo_settings.fetch_gym"))
    if not gym:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academia nao encontrada")
    return gym


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _serialize_domain_routes(gym: Gym) -> list[KommoDomainRouteRead]:
    routes = sorted(getattr(gym, "kommo_domain_routes", []) or [], key=lambda item: item.domain)
    if not routes:
        return [_default_route_read(domain) for domain in DEFAULT_KOMMO_DOMAINS]
    existing = {route.domain: route for route in routes}
    serialized: list[KommoDomainRouteRead] = []
    for domain in DEFAULT_KOMMO_DOMAINS:
        route = existing.get(domain)
        serialized.append(_route_to_read(route) if route else _default_route_read(domain))
    for route in routes:
        if route.domain not in DEFAULT_KOMMO_DOMAINS:
            serialized.append(_route_to_read(route))
    return serialized


def _route_to_read(route: KommoDomainRoute) -> KommoDomainRouteRead:
    return KommoDomainRouteRead(
        domain=route.domain,
        is_enabled=bool(route.is_enabled),
        pipeline_id=_normalize_text(route.pipeline_id),
        stage_id=_normalize_text(route.stage_id),
        salesbot_id=_normalize_text(route.salesbot_id),
        channel_source_id=_normalize_text(route.channel_source_id),
        responsible_user_id=_normalize_text(route.responsible_user_id),
        message_field_id=_normalize_text(route.message_field_id),
        pdf_url_field_id=_normalize_text(route.pdf_url_field_id),
        pdf_delivery_mode=_normalize_pdf_delivery_mode(getattr(route, "pdf_delivery_mode", None)),
        file_uuid_field_id=_normalize_text(getattr(route, "file_uuid_field_id", None)),
        file_name_field_id=_normalize_text(getattr(route, "file_name_field_id", None)),
        file_attachment_note_field_id=_normalize_text(getattr(route, "file_attachment_note_field_id", None)),
        source_type_field_id=_normalize_text(route.source_type_field_id),
        source_id_field_id=_normalize_text(route.source_id_field_id),
        tags=[str(item).strip() for item in (route.tags or []) if str(item).strip()],
    )


def _default_route_read(domain: str) -> KommoDomainRouteRead:
    return KommoDomainRouteRead(domain=domain)


def _upsert_domain_routes(db: Session, *, gym_id: UUID, payloads) -> None:
    existing_routes = {
        route.domain: route
        for route in db.scalars(
            select(KommoDomainRoute).where(KommoDomainRoute.gym_id == gym_id)
        ).all()
    }
    for payload in payloads:
        domain = _normalize_domain(payload.domain)
        route = existing_routes.get(domain)
        if route is None:
            route = KommoDomainRoute(gym_id=gym_id, domain=domain)
        route.is_enabled = bool(payload.is_enabled)
        route.pipeline_id = _normalize_text(payload.pipeline_id)
        route.stage_id = _normalize_text(payload.stage_id)
        route.salesbot_id = _normalize_text(payload.salesbot_id)
        route.channel_source_id = _normalize_text(payload.channel_source_id)
        route.responsible_user_id = _normalize_text(payload.responsible_user_id)
        route.message_field_id = _normalize_text(payload.message_field_id)
        route.pdf_url_field_id = _normalize_text(payload.pdf_url_field_id)
        route.pdf_delivery_mode = _normalize_pdf_delivery_mode(payload.pdf_delivery_mode)
        route.file_uuid_field_id = _normalize_text(payload.file_uuid_field_id)
        route.file_name_field_id = _normalize_text(payload.file_name_field_id)
        route.file_attachment_note_field_id = _normalize_text(payload.file_attachment_note_field_id)
        route.source_type_field_id = _normalize_text(payload.source_type_field_id)
        route.source_id_field_id = _normalize_text(payload.source_id_field_id)
        route.tags = [str(tag).strip() for tag in (payload.tags or []) if str(tag).strip()]
        db.add(route)


def _normalize_domain(value: str) -> str:
    normalized = (value or "").strip().lower().replace("-", "_")
    if normalized not in DEFAULT_KOMMO_DOMAINS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Dominio Kommo invalido: {value}")
    return normalized


def _normalize_pdf_delivery_mode(value: str | None) -> str:
    normalized = (value or "native_file_required").strip().lower()
    if normalized not in {"native_file_required", "native_file_preferred", "link_only"}:
        return "native_file_required"
    return normalized


DEFAULT_KOMMO_DOMAINS = (
    "retention",
    "onboarding",
    "assessment",
    "body_composition",
    "finance",
    "sales",
    "student_ai",
    "support",
)
