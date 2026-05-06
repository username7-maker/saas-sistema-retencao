from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.kommo_service import get_kommo_gym, is_kommo_ready

RequestedChannel = Literal["auto", "kommo", "whatsapp", "manual"]
ResolvedChannel = Literal["kommo", "whatsapp", "manual"]


@dataclass(frozen=True)
class CommunicationChannelResolution:
    requested_channel: str
    channel: ResolvedChannel
    primary_channel: str
    fallback_channel: str
    used_fallback: bool
    kommo_ready: bool
    detail: str


def resolve_communication_channel(
    db: Session,
    *,
    gym_id: UUID,
    requested_channel: str | None = "auto",
) -> CommunicationChannelResolution:
    gym = get_kommo_gym(db, gym_id)
    requested = _normalize_requested_channel(requested_channel)
    primary = _normalize_primary_channel(getattr(gym, "primary_message_channel", None))
    fallback = _normalize_fallback_channel(getattr(gym, "kommo_fallback_channel", None))
    kommo_ready = is_kommo_ready(gym)

    target = primary if requested == "auto" else requested
    if target == "kommo":
        if kommo_ready:
            return CommunicationChannelResolution(
                requested_channel=requested,
                channel="kommo",
                primary_channel=primary,
                fallback_channel=fallback,
                used_fallback=False,
                kommo_ready=True,
                detail="Kommo configurada como canal operacional.",
            )
        return CommunicationChannelResolution(
            requested_channel=requested,
            channel=fallback,
            primary_channel=primary,
            fallback_channel=fallback,
            used_fallback=True,
            kommo_ready=False,
            detail="Kommo indisponivel; usando fallback operacional.",
        )

    return CommunicationChannelResolution(
        requested_channel=requested,
        channel=target,  # type: ignore[arg-type]
        primary_channel=primary,
        fallback_channel=fallback,
        used_fallback=False,
        kommo_ready=kommo_ready,
        detail="Canal operacional resolvido.",
    )


def _normalize_requested_channel(value: str | None) -> RequestedChannel:
    normalized = (value or "auto").strip().lower()
    if normalized in {"auto", "kommo", "whatsapp", "manual"}:
        return normalized  # type: ignore[return-value]
    return "auto"


def _normalize_primary_channel(value: str | None) -> ResolvedChannel:
    normalized = (value or "whatsapp").strip().lower()
    if normalized in {"kommo", "whatsapp", "manual"}:
        return normalized  # type: ignore[return-value]
    return "whatsapp"


def _normalize_fallback_channel(value: str | None) -> Literal["whatsapp", "manual"]:
    normalized = (value or "whatsapp").strip().lower()
    if normalized in {"whatsapp", "manual"}:
        return normalized  # type: ignore[return-value]
    return "whatsapp"
