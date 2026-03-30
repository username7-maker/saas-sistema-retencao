from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import include_all_tenants
from app.models import Gym
from app.schemas.settings import (
    KommoConnectionTestResult,
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

    if payload.clear_access_token:
        gym.kommo_access_token_encrypted = None
    elif payload.kommo_access_token is not None:
        normalized_token = payload.kommo_access_token.strip()
        if normalized_token:
            gym.kommo_access_token_encrypted = normalized_token

    db.add(gym)
    db.flush()
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
