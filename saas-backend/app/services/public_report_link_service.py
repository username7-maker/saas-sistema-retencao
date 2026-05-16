from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings


PUBLIC_REPORT_TOKEN_AUDIENCE = "cordex-public-report"
PUBLIC_REPORT_TOKEN_TYPE = "body_composition_pdf"


def create_body_composition_report_public_url(
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
    pdf_kind: str = "summary",
    expires_in_hours: int = 72,
) -> str:
    base_url = (settings.public_backend_url or "").strip().rstrip("/")
    if not base_url:
        raise ValueError("PUBLIC_BACKEND_URL precisa estar configurada para envio de PDF pela Kommo.")

    expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=max(expires_in_hours, 1))
    payload: dict[str, Any] = {
        "aud": PUBLIC_REPORT_TOKEN_AUDIENCE,
        "typ": PUBLIC_REPORT_TOKEN_TYPE,
        "gym_id": str(gym_id),
        "member_id": str(member_id),
        "evaluation_id": str(evaluation_id),
        "pdf_kind": pdf_kind,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return f"{base_url}/api/v1/public/reports/body-composition/{token}.pdf"


def decode_body_composition_report_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=PUBLIC_REPORT_TOKEN_AUDIENCE,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Link publico de relatorio invalido ou expirado.") from exc
    if payload.get("typ") != PUBLIC_REPORT_TOKEN_TYPE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tipo de relatorio publico invalido.")
    return payload
