from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.actuar.browser_client import ActuarPlaywrightProvider
from app.models import Gym
from app.schemas.settings import (
    ActuarConnectionTestResult,
    ActuarSettingsRead,
    ActuarSettingsUpdate,
)


def get_actuar_settings(db: Session, *, gym_id: UUID) -> ActuarSettingsRead:
    gym = _get_gym_or_404(db, gym_id=gym_id)
    return serialize_actuar_settings(gym)


def update_actuar_settings(
    db: Session,
    *,
    gym_id: UUID,
    payload: ActuarSettingsUpdate,
) -> ActuarSettingsRead:
    gym = _get_gym_or_404(db, gym_id=gym_id)
    gym.actuar_enabled = payload.actuar_enabled
    gym.actuar_auto_sync_body_composition = payload.actuar_auto_sync_body_composition
    gym.actuar_base_url = _normalize_text(payload.actuar_base_url)
    gym.actuar_username = _normalize_text(payload.actuar_username)

    if payload.clear_password:
        gym.actuar_password_encrypted = None
    elif payload.actuar_password is not None:
        normalized_password = payload.actuar_password.strip()
        if normalized_password:
            gym.actuar_password_encrypted = normalized_password

    db.add(gym)
    db.flush()
    return serialize_actuar_settings(gym)


def test_actuar_connection(db: Session, *, gym_id: UUID) -> ActuarConnectionTestResult:
    gym = _get_gym_or_404(db, gym_id=gym_id)
    if not settings.actuar_enabled or not settings.actuar_sync_enabled:
        return ActuarConnectionTestResult(
            success=False,
            provider="actuar_assisted_rpa",
            effective_sync_mode=resolve_effective_actuar_sync_mode(gym),
            automatic_sync_ready=False,
            message="Actuar desabilitado neste ambiente.",
            detail="Ative ACTUAR_ENABLED e ACTUAR_SYNC_ENABLED antes de testar a automacao.",
        )

    if not has_actuar_credentials(gym):
        return ActuarConnectionTestResult(
            success=False,
            provider="actuar_assisted_rpa",
            effective_sync_mode=resolve_effective_actuar_sync_mode(gym),
            automatic_sync_ready=False,
            message="Configure URL, usuario e senha do Actuar para ativar o modo automatico.",
            detail="Sem credenciais validas, o piloto continua no fallback de exportacao/manual.",
        )

    provider: ActuarPlaywrightProvider | None = None
    try:
        provider = ActuarPlaywrightProvider(
            base_url=(gym.actuar_base_url or settings.actuar_base_url).strip(),
            username=(gym.actuar_username or settings.actuar_username).strip(),
            password=(gym.actuar_password_encrypted or settings.actuar_password).strip(),
            worker_id="settings:test-connection",
            evidence_dir=Path(settings.actuar_sync_evidence_dir) / str(gym.id) / "connection-test",
        )
        provider.login()
        return ActuarConnectionTestResult(
            success=True,
            provider="actuar_assisted_rpa",
            effective_sync_mode=resolve_effective_actuar_sync_mode(gym),
            automatic_sync_ready=True,
            message="Conexao com o Actuar validada com sucesso.",
            detail="O ambiente esta pronto para tentar o sync automatico da bioimpedancia.",
        )
    except Exception as exc:
        return ActuarConnectionTestResult(
            success=False,
            provider="actuar_assisted_rpa",
            effective_sync_mode=resolve_effective_actuar_sync_mode(gym),
            automatic_sync_ready=False,
            message="Nao foi possivel validar a conexao automatica com o Actuar.",
            detail=_map_connection_error(exc),
        )
    finally:
        if provider:
            provider.close()


def serialize_actuar_settings(gym: Gym) -> ActuarSettingsRead:
    effective_sync_mode = resolve_effective_actuar_sync_mode(gym)
    return ActuarSettingsRead(
        actuar_enabled=bool(gym.actuar_enabled),
        actuar_auto_sync_body_composition=bool(gym.actuar_auto_sync_body_composition),
        actuar_base_url=_normalize_text(gym.actuar_base_url),
        actuar_username=_normalize_text(gym.actuar_username),
        actuar_has_password=bool(_normalize_text(gym.actuar_password_encrypted)),
        environment_enabled=bool(settings.actuar_enabled and settings.actuar_sync_enabled),
        environment_sync_mode=(settings.actuar_sync_mode or "disabled").strip().lower(),
        effective_sync_mode=effective_sync_mode,
        automatic_sync_ready=bool(
            settings.actuar_enabled
            and settings.actuar_sync_enabled
            and effective_sync_mode == "assisted_rpa"
            and has_actuar_credentials(gym)
        ),
    )


def has_actuar_credentials(gym: Gym | None) -> bool:
    if gym is None:
        return False
    return bool(
        (gym.actuar_base_url or settings.actuar_base_url or "").strip()
        and (gym.actuar_username or settings.actuar_username or "").strip()
        and (gym.actuar_password_encrypted or settings.actuar_password or "").strip()
    )


def resolve_effective_actuar_sync_mode(gym: Gym | None) -> str:
    if not settings.actuar_sync_enabled:
        return "disabled"
    if gym is not None and not gym.actuar_enabled:
        return "disabled"

    configured_mode = (settings.actuar_sync_mode or "assisted_rpa").strip().lower()
    if configured_mode == "http_api":
        return "http_api"
    if configured_mode == "assisted_rpa":
        return "assisted_rpa"
    if configured_mode == "csv_export":
        return "assisted_rpa" if has_actuar_credentials(gym) else "csv_export"
    return "assisted_rpa" if has_actuar_credentials(gym) else "csv_export"


def _get_gym_or_404(db: Session, *, gym_id: UUID) -> Gym:
    gym = db.scalar(select(Gym).where(Gym.id == gym_id).execution_options(include_all_tenants=True))
    if not gym:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academia nao encontrada")
    return gym


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _map_connection_error(exc: Exception) -> str:
    raw = str(exc).strip() or type(exc).__name__
    if raw == "playwright_unavailable":
        return "Playwright indisponivel no ambiente. Confirme a instalacao do runtime automatico."
    if raw == "actuar_form_changed":
        return "A tela do Actuar mudou e os seletores atuais precisam ser ajustados."
    if "Timeout" in raw or "timeout" in raw:
        return "Tempo esgotado ao abrir o Actuar. Verifique URL, disponibilidade e latencia."
    return raw
