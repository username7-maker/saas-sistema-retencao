"""
Endpoints de gerenciamento da conexao WhatsApp por academia.
"""
import logging
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.models.gym import Gym
from app.services.evolution_service import (
    configure_webhook,
    disconnect_instance,
    ensure_instance,
    get_connection_status,
    get_qr_code,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


class WhatsAppStatusOut(BaseModel):
    status: str
    phone: str | None
    connected_at: datetime | None
    instance: str | None


class QRCodeOut(BaseModel):
    status: str
    qrcode: str | None


def _ensure_evolution_config() -> None:
    if not settings.whatsapp_api_url or not settings.whatsapp_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evolution API nao configurada",
        )


def _get_gym(db: Session, gym_id) -> Gym:
    gym = db.scalar(select(Gym).where(Gym.id == gym_id))
    if not gym:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academia nao encontrada")
    return gym


def _map_state(evo_state: str) -> str:
    return {
        "open": "connected",
        "connecting": "connecting",
        "close": "disconnected",
    }.get((evo_state or "").lower(), "disconnected")


def _extract_instance_name(body: dict) -> str:
    raw_instance = body.get("instance")
    if isinstance(raw_instance, str):
        return raw_instance
    if isinstance(raw_instance, dict):
        return (
            raw_instance.get("instanceName")
            or raw_instance.get("name")
            or raw_instance.get("instance")
            or ""
        )
    return body.get("instanceName", "") or ""


@router.post("/connect", response_model=QRCodeOut)
def connect_whatsapp(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER)),
    background_tasks: BackgroundTasks = None,
) -> QRCodeOut:
    _ensure_evolution_config()

    gym = _get_gym(db, current_user.gym_id)
    instance = ensure_instance(str(current_user.gym_id))
    gym.whatsapp_instance = instance
    gym.whatsapp_status = "connecting"
    db.add(gym)
    db.commit()

    if settings.public_backend_url and settings.whatsapp_webhook_token and background_tasks is not None:
        webhook_url = (
            f"{settings.public_backend_url.rstrip('/')}/api/v1/whatsapp/webhook"
            f"?token={quote(settings.whatsapp_webhook_token, safe='')}"
        )
        background_tasks.add_task(configure_webhook, instance, webhook_url)
    else:
        logger.warning("Webhook da Evolution nao configurado: PUBLIC_BACKEND_URL ou WHATSAPP_WEBHOOK_TOKEN ausente")

    qr_data = get_qr_code(instance)
    return QRCodeOut(**qr_data)


@router.get("/qr", response_model=QRCodeOut)
def get_qr(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER)),
) -> QRCodeOut:
    _ensure_evolution_config()

    gym = _get_gym(db, current_user.gym_id)
    if not gym.whatsapp_instance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma conexao iniciada. Chame POST /whatsapp/connect primeiro.",
        )

    conn = get_connection_status(gym.whatsapp_instance)
    if conn["state"] == "open":
        if gym.whatsapp_status != "connected":
            gym.whatsapp_status = "connected"
            gym.whatsapp_phone = conn.get("phone")
            gym.whatsapp_connected_at = datetime.now(tz=timezone.utc)
            db.add(gym)
            db.commit()
        return QRCodeOut(status="connected", qrcode=None)

    return QRCodeOut(**get_qr_code(gym.whatsapp_instance))


@router.get("/status", response_model=WhatsAppStatusOut)
def get_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER)),
) -> WhatsAppStatusOut:
    gym = _get_gym(db, current_user.gym_id)
    return WhatsAppStatusOut(
        status=gym.whatsapp_status,
        phone=gym.whatsapp_phone,
        connected_at=gym.whatsapp_connected_at,
        instance=gym.whatsapp_instance,
    )


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_whatsapp(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.OWNER)),
) -> None:
    gym = _get_gym(db, current_user.gym_id)
    if gym.whatsapp_instance:
        disconnect_instance(gym.whatsapp_instance)
    gym.whatsapp_instance = None
    gym.whatsapp_status = "disconnected"
    gym.whatsapp_phone = None
    gym.whatsapp_connected_at = None
    db.add(gym)
    db.commit()


@router.post("/webhook", status_code=status.HTTP_200_OK, include_in_schema=False)
async def whatsapp_webhook(
    request: Request,
    token: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    configured_token = (settings.whatsapp_webhook_token or "").strip()
    if not configured_token or token != configured_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook token")

    body = await request.json()
    event = str(body.get("event", ""))
    instance_name = _extract_instance_name(body)
    data = body.get("data", {}) if isinstance(body.get("data"), dict) else {}

    if not instance_name:
        return {"ok": True}

    gym = db.scalar(select(Gym).where(Gym.whatsapp_instance == instance_name))
    if not gym:
        logger.warning("Webhook para instancia desconhecida: %s", instance_name)
        return {"ok": True}

    if event in ("CONNECTION_UPDATE", "STATUS_INSTANCE"):
        state = data.get("state") or data.get("status", "")
        mapped = _map_state(state)
        gym.whatsapp_status = mapped

        if mapped == "connected":
            phone = (
                data.get("instance", {}).get("owner", "")
                or data.get("ownerJid", "")
                or data.get("wuid", "")
            ).split("@")[0] or None
            gym.whatsapp_phone = phone
            gym.whatsapp_connected_at = datetime.now(tz=timezone.utc)
        elif mapped == "disconnected":
            gym.whatsapp_phone = None
            gym.whatsapp_connected_at = None

        db.add(gym)
        db.commit()
        logger.info("Gym %s: WhatsApp status -> %s", gym.id, mapped)

    return {"ok": True}
