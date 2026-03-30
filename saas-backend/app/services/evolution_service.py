"""Wrapper para Evolution API - gerencia instancias WhatsApp por gym."""
import logging
from typing import Literal

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)

WhatsAppStatus = Literal["disconnected", "connecting", "connected", "error"]


def _instance_name(gym_id: str) -> str:
    return f"gym_{gym_id.replace('-', '')}"


def _headers() -> dict[str, str]:
    return {
        "apikey": settings.whatsapp_api_token,
        "Content-Type": "application/json",
    }


def _base() -> str:
    return settings.whatsapp_api_url.rstrip("/")


def ensure_instance(gym_id: str) -> str:
    instance = _instance_name(gym_id)
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{_base()}/instance/create",
                headers=_headers(),
                json={
                    "instanceName": instance,
                    "qrcode": True,
                    "integration": "WHATSAPP-BAILEYS",
                },
            )
            if response.status_code not in (200, 201, 409):
                response.raise_for_status()
    except Exception:
        logger.exception("Erro ao criar instancia %s", instance)
        raise
    return instance


def get_qr_code(instance: str) -> dict:
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"{_base()}/instance/connect/{instance}",
                headers=_headers(),
            )
            response.raise_for_status()
            data = response.json()
            base64_img = data.get("base64") or data.get("qrcode", {}).get("base64")
            if base64_img and not str(base64_img).startswith("data:"):
                base64_img = f"data:image/png;base64,{base64_img}"
            return {
                "status": "connecting" if base64_img else "connected",
                "qrcode": base64_img,
            }
    except Exception:
        logger.exception("Erro ao buscar QR de %s", instance)
        return {"status": "error", "qrcode": None}


def get_connection_status(instance: str) -> dict:
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{_base()}/instance/connectionState/{instance}",
                headers=_headers(),
            )
            response.raise_for_status()
            data = response.json()
            inner = data.get("instance", data)
            state = inner.get("state", "close")

            phone = None
            if state == "open":
                try:
                    info = client.get(
                        f"{_base()}/instance/fetchInstances",
                        headers=_headers(),
                        params={"instanceName": instance},
                    )
                    info_data = info.json()
                    if isinstance(info_data, list) and info_data:
                        phone = (info_data[0].get("ownerJid") or "").split("@")[0] or None
                    elif isinstance(info_data, dict):
                        items = info_data.get("instances") or info_data.get("data") or []
                        if isinstance(items, list) and items:
                            phone = (items[0].get("ownerJid") or "").split("@")[0] or None
                except Exception:
                    logger.exception("Erro ao buscar dados adicionais da instancia %s", instance)

            return {"state": state, "phone": phone}
    except Exception:
        logger.exception("Erro ao verificar status de %s", instance)
        return {"state": "close", "phone": None}


def disconnect_instance(instance: str) -> bool:
    try:
        with httpx.Client(timeout=15.0) as client:
            client.delete(f"{_base()}/instance/logout/{instance}", headers=_headers())
            response = client.delete(f"{_base()}/instance/delete/{instance}", headers=_headers())
            return response.status_code in (200, 204, 404)
    except Exception:
        logger.exception("Erro ao desconectar instancia %s", instance)
        return False


def configure_webhook(instance: str, webhook_url: str, webhook_headers: dict[str, str] | None = None) -> bool:
    try:
        payload = {
            "url": webhook_url,
            "webhook_by_events": False,
            "webhook_base64": False,
            "events": [
                "QRCODE_UPDATED",
                "CONNECTION_UPDATE",
                "STATUS_INSTANCE",
                "MESSAGES_UPSERT",
            ],
        }
        if webhook_headers:
            payload["headers"] = webhook_headers
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{_base()}/webhook/set/{instance}",
                headers=_headers(),
                json=payload,
            )
            return response.status_code in (200, 201)
    except Exception:
        logger.exception("Erro ao configurar webhook para %s", instance)
        return False
