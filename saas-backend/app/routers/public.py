from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter, rate_limit_enabled
from app.database import get_db
from app.schemas.public_diagnosis import (
    PublicDiagnosisQueuedResponse,
    PublicDiagnosisStatusRead,
    PublicObjectionRequest,
    PublicObjectionResponse,
    PublicProposalRequest,
)
from app.schemas.acquisition import AcquisitionCaptureInput, AcquisitionCaptureResponse
from app.schemas.sales import (
    PublicBookingConfirmRequest,
    PublicBookingConfirmResponse,
    PublicWhatsappWebhookResponse,
)
from app.services.booking_service import confirm_public_booking
from app.services.acquisition_service import capture_acquisition_lead
from app.services.crm_service import create_public_diagnosis_lead
from app.services.core_async_job_service import enqueue_public_diagnosis_job, get_public_diagnosis_job, serialize_core_async_job
from app.services.diagnosis_service import (
    build_public_diagnosis_payload,
    new_diagnosis_id,
    resolve_public_gym_id,
)
from app.services.nurturing_service import handle_incoming_whatsapp_webhook
from app.services.objection_service import generate_objection_response
from app.services.proposal_service import (
    generate_proposal_pdf,
    hydrate_proposal_from_lead,
    send_proposal_email_if_needed,
)

router = APIRouter(prefix="/public", tags=["public"])

_MAX_DIAG_UPLOAD_SIZE = 10 * 1024 * 1024
_fallback_uploads_by_ip: dict[str, list[datetime]] = defaultdict(list)


def _apply_fallback_rate_limit(request: Request) -> None:
    if rate_limit_enabled:
        return
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(hours=1)
    ip = request.client.host if request.client else "unknown"
    entries = [item for item in _fallback_uploads_by_ip[ip] if item >= cutoff]
    if len(entries) >= 5:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Limite de uploads por hora excedido")
    entries.append(now)
    _fallback_uploads_by_ip[ip] = entries


def _ensure_public_endpoint_enabled(enabled: bool, endpoint_name: str) -> None:
    if enabled:
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Endpoint publico '{endpoint_name}' temporariamente desabilitado para o piloto.",
    )


def _require_public_shared_token(
    *,
    configured_token: str,
    provided_token: str | None,
    endpoint_name: str,
) -> None:
    expected = configured_token.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Endpoint publico '{endpoint_name}' exige token compartilhado configurado.",
        )
    if not provided_token or provided_token.strip() != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token publico invalido")


@router.post("/diagnostico", response_model=PublicDiagnosisQueuedResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.public_diag_rate_limit)
async def public_diagnostico(
    request: Request,
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    email: str = Form(...),
    whatsapp: str = Form(...),
    gym_name: str = Form(...),
    total_members: int = Form(...),
    avg_monthly_fee: str = Form(...),
    csv_file: UploadFile = File(...),
) -> PublicDiagnosisQueuedResponse:
    _ensure_public_endpoint_enabled(settings.public_diagnosis_enabled, "diagnostico")
    _apply_fallback_rate_limit(request)
    try:
        public_gym_id = resolve_public_gym_id()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    filename = (csv_file.filename or "").lower()
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo de diagnostico deve ser CSV")

    content = await csv_file.read(_MAX_DIAG_UPLOAD_SIZE + 1)
    if len(content) > _MAX_DIAG_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Arquivo excede o limite de 10 MB")

    try:
        avg_fee_decimal = Decimal(avg_monthly_fee)
    except InvalidOperation as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="avg_monthly_fee invalido") from exc

    diagnosis_id = new_diagnosis_id()
    payload = build_public_diagnosis_payload(
        full_name=full_name,
        email=email,
        whatsapp=whatsapp,
        gym_name=gym_name,
        total_members=total_members,
        avg_monthly_fee=avg_fee_decimal,
    )

    lead = create_public_diagnosis_lead(
        db,
        gym_id=public_gym_id,
        full_name=payload["full_name"],
        email=payload["email"],
        phone=payload["whatsapp"],
        gym_name=payload["gym_name"],
        total_members=payload["total_members"],
        avg_monthly_fee=Decimal(str(payload["avg_monthly_fee"])),
        diagnosis_id=diagnosis_id,
        commit=False,
    )
    job = enqueue_public_diagnosis_job(
        db,
        gym_id=public_gym_id,
        diagnosis_id=diagnosis_id,
        lead_id=lead.id,
        payload=payload,
        csv_content=content,
        requester_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return PublicDiagnosisQueuedResponse(
        message="Diagnostico recebido e em processamento.",
        diagnosis_id=diagnosis_id,
        job_id=job.id,
        lead_id=lead.id,
        status=job.status,
    )


@router.get("/diagnostico/{diagnosis_id}/status", response_model=PublicDiagnosisStatusRead)
def public_diagnostico_status(
    diagnosis_id: UUID,
    lead_id: UUID,
    db: Session = Depends(get_db),
) -> PublicDiagnosisStatusRead:
    try:
        public_gym_id = resolve_public_gym_id()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    job = get_public_diagnosis_job(
        db,
        diagnosis_id=diagnosis_id,
        lead_id=lead_id,
        gym_id=public_gym_id,
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostico nao encontrado")

    serialized = serialize_core_async_job(job)
    return PublicDiagnosisStatusRead(
        diagnosis_id=diagnosis_id,
        lead_id=lead_id,
        **serialized,
    )


@router.post("/objection-response", response_model=PublicObjectionResponse)
@limiter.limit(settings.public_objection_response_rate_limit)
def public_objection_response(
    request: Request,
    payload: PublicObjectionRequest,
    db: Session = Depends(get_db),
) -> PublicObjectionResponse:
    _ensure_public_endpoint_enabled(settings.public_objection_response_enabled, "objection-response")
    public_gym_id: UUID | None = None
    try:
        public_gym_id = resolve_public_gym_id()
    except Exception:
        public_gym_id = None

    result = generate_objection_response(
        db,
        message_text=payload.message_text,
        lead_id=payload.lead_id,
        context=payload.context,
        public_gym_id=public_gym_id,
    )
    return PublicObjectionResponse(**result)


@router.post("/proposal")
@limiter.limit(settings.public_proposal_rate_limit)
def public_proposal(
    request: Request,
    payload: PublicProposalRequest,
    db: Session = Depends(get_db),
) -> Response:
    _ensure_public_endpoint_enabled(settings.public_proposal_enabled, "proposal")
    hydrated = hydrate_proposal_from_lead(db, payload, allow_lead_lookup=False)
    pdf_bytes, filename = generate_proposal_pdf(hydrated)
    if settings.public_proposal_email_enabled:
        send_proposal_email_if_needed(hydrated, pdf_bytes, filename)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.post("/whatsapp/webhook", response_model=PublicWhatsappWebhookResponse)
@limiter.limit(settings.public_whatsapp_webhook_rate_limit)
def public_whatsapp_webhook(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> PublicWhatsappWebhookResponse:
    provided_token = x_webhook_token or _extract_bearer_token(authorization)
    if not settings.whatsapp_webhook_token or provided_token != settings.whatsapp_webhook_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook token invalido")

    result = handle_incoming_whatsapp_webhook(db, payload)
    return PublicWhatsappWebhookResponse(**result)


@router.post("/booking/confirm", response_model=PublicBookingConfirmResponse)
@limiter.limit(settings.public_booking_rate_limit)
def public_booking_confirm(
    request: Request,
    payload: PublicBookingConfirmRequest,
    db: Session = Depends(get_db),
    x_public_booking_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> PublicBookingConfirmResponse:
    _ensure_public_endpoint_enabled(settings.public_booking_confirm_enabled, "booking/confirm")
    _require_public_shared_token(
        configured_token=settings.public_booking_confirm_token,
        provided_token=x_public_booking_token or _extract_bearer_token(authorization),
        endpoint_name="booking/confirm",
    )
    lead, booking = confirm_public_booking(db, payload)
    return PublicBookingConfirmResponse(
        message="Agendamento confirmado",
        lead_id=lead.id,
        booking_id=booking.id,
    )


@router.post("/acquisition/capture", response_model=AcquisitionCaptureResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.public_booking_rate_limit)
def public_acquisition_capture(
    request: Request,
    payload: AcquisitionCaptureInput,
    db: Session = Depends(get_db),
    x_public_booking_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> AcquisitionCaptureResponse:
    _ensure_public_endpoint_enabled(settings.public_booking_confirm_enabled, "acquisition/capture")
    _require_public_shared_token(
        configured_token=settings.public_booking_confirm_token,
        provided_token=x_public_booking_token or _extract_bearer_token(authorization),
        endpoint_name="acquisition/capture",
    )
    try:
        public_gym_id = resolve_public_gym_id()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return capture_acquisition_lead(db, payload, gym_id=public_gym_id, commit=True)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip() or None
