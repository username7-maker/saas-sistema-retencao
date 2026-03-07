from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_current_gym_id
from app.models import Lead, LeadBooking, LeadStage, NurturingSequence
from app.schemas.sales import PublicBookingConfirmRequest
from app.services.crm_service import append_lead_note, create_public_booking_lead
from app.services.nurturing_service import pause_sequences_for_lead
from app.services.whatsapp_service import send_whatsapp_sync


def confirm_public_booking(db: Session, payload: PublicBookingConfirmRequest) -> tuple[Lead, LeadBooking]:
    public_gym_id = _resolve_public_gym_id()
    lead = _resolve_or_create_public_lead(db, public_gym_id, payload)
    booking = _upsert_booking(db, lead, payload)

    lead.stage = LeadStage.MEETING_SCHEDULED
    lead.last_contact_at = datetime.now(tz=timezone.utc)
    append_lead_note(
        db,
        lead,
        {
            "type": "booking_confirmed",
            "booking_id": str(booking.id),
            "scheduled_for": booking.scheduled_for.isoformat(),
            "provider_name": booking.provider_name,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        },
    )
    pause_sequences_for_lead(db, lead.id, "meeting_scheduled")
    _send_booking_confirmation_whatsapp(db, lead, booking)
    db.add(lead)
    db.add(booking)
    db.commit()
    db.refresh(lead)
    db.refresh(booking)
    return lead, booking


def get_booking_status(db: Session, lead_id: UUID) -> dict[str, Any]:
    gym_id = get_current_gym_id()
    stmt = (
        select(LeadBooking)
        .where(
            LeadBooking.lead_id == lead_id,
            LeadBooking.status == "confirmed",
            LeadBooking.scheduled_for >= datetime.now(tz=timezone.utc),
        )
        .order_by(LeadBooking.scheduled_for.asc())
        .limit(1)
    )
    if gym_id:
        stmt = stmt.where(LeadBooking.gym_id == gym_id)
    booking = db.scalar(stmt)
    if not booking:
        return {"has_booking": False, "booking_id": None, "scheduled_for": None, "status": None, "provider_name": None}
    return {
        "has_booking": True,
        "booking_id": booking.id,
        "scheduled_for": booking.scheduled_for,
        "status": booking.status,
        "provider_name": booking.provider_name,
    }


def process_booking_reminders(db: Session) -> dict[str, int]:
    now = datetime.now(tz=timezone.utc)
    window_end = now + timedelta(minutes=settings.booking_reminder_minutes_before)
    window_start = window_end - timedelta(minutes=10)
    bookings = list(
        db.scalars(
            select(LeadBooking).where(
                LeadBooking.status == "confirmed",
                LeadBooking.reminder_sent_at.is_(None),
                LeadBooking.scheduled_for >= window_start,
                LeadBooking.scheduled_for <= window_end,
            )
        ).all()
    )

    processed = 0
    sent = 0
    for booking in bookings:
        processed += 1
        lead = db.get(Lead, booking.lead_id) if booking.lead_id else None
        phone = booking.prospect_whatsapp or (lead.phone if lead else None)
        if not phone:
            continue
        reminder_text = (
            f"Lembrete AI GYM OS: sua call esta agendada para "
            f"{booking.scheduled_for.astimezone(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}. "
            "Vamos te mostrar o diagnostico, a automacao de retencao e o plano recomendado."
        )
        result = send_whatsapp_sync(
            db,
            phone=phone,
            message=reminder_text,
            lead_id=booking.lead_id,
            template_name="custom",
            direction="outbound",
            event_type="booking_reminder",
        )
        if result.status in {"sent", "skipped"}:
            booking.reminder_sent_at = now
            db.add(booking)
            sent += 1

    db.commit()
    return {"processed": processed, "sent": sent}


def _resolve_or_create_public_lead(db: Session, gym_id: UUID, payload: PublicBookingConfirmRequest) -> Lead:
    lead = None
    if payload.lead_id:
        candidate = db.get(Lead, payload.lead_id)
        if candidate and candidate.gym_id == gym_id and candidate.deleted_at is None:
            lead = candidate

    if lead is None and payload.email:
        lead = db.scalar(
            select(Lead)
            .where(
                Lead.gym_id == gym_id,
                Lead.email == str(payload.email),
                Lead.deleted_at.is_(None),
            )
            .order_by(Lead.updated_at.desc())
            .limit(1)
        )

    if lead is not None:
        if payload.whatsapp and not lead.phone:
            lead.phone = payload.whatsapp
        return lead

    return create_public_booking_lead(
        db,
        gym_id=gym_id,
        full_name=payload.prospect_name,
        email=str(payload.email) if payload.email else None,
        phone=payload.whatsapp,
        scheduled_for=payload.scheduled_for,
        provider_name=payload.provider_name,
    )


def _upsert_booking(db: Session, lead: Lead, payload: PublicBookingConfirmRequest) -> LeadBooking:
    booking = None
    if payload.provider_booking_id:
        booking = db.scalar(
            select(LeadBooking).where(
                LeadBooking.gym_id == lead.gym_id,
                LeadBooking.provider_booking_id == payload.provider_booking_id,
            )
        )

    if booking is None:
        booking = db.scalar(
            select(LeadBooking)
            .where(
                LeadBooking.gym_id == lead.gym_id,
                LeadBooking.lead_id == lead.id,
                LeadBooking.scheduled_for == payload.scheduled_for,
            )
            .limit(1)
        )

    if booking is None:
        booking = LeadBooking(
            gym_id=lead.gym_id,
            lead_id=lead.id,
            provider_name=payload.provider_name,
            provider_booking_id=payload.provider_booking_id,
            prospect_name=payload.prospect_name,
            prospect_email=str(payload.email) if payload.email else lead.email,
            prospect_whatsapp=payload.whatsapp or lead.phone,
            scheduled_for=payload.scheduled_for,
            status="confirmed",
            extra_data=payload.metadata,
        )
        db.add(booking)
        db.flush()
        return booking

    booking.provider_name = payload.provider_name or booking.provider_name
    booking.provider_booking_id = payload.provider_booking_id or booking.provider_booking_id
    booking.prospect_name = payload.prospect_name
    booking.prospect_email = str(payload.email) if payload.email else booking.prospect_email
    booking.prospect_whatsapp = payload.whatsapp or booking.prospect_whatsapp
    booking.scheduled_for = payload.scheduled_for
    booking.status = "confirmed"
    booking.extra_data = {**dict(booking.extra_data or {}), **payload.metadata}
    db.add(booking)
    db.flush()
    return booking


def _send_booking_confirmation_whatsapp(db: Session, lead: Lead, booking: LeadBooking) -> None:
    phone = booking.prospect_whatsapp or lead.phone or _phone_from_sequence(db, lead.id)
    if not phone:
        return

    message = (
        f"Call confirmada para {booking.scheduled_for.astimezone(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}. "
        "Na conversa vamos apresentar seu diagnostico, o plano de recuperacao e a proposta recomendada."
    )
    send_whatsapp_sync(
        db,
        phone=phone,
        message=message,
        lead_id=lead.id,
        template_name="custom",
        direction="outbound",
        event_type="booking_confirmation",
    )


def _phone_from_sequence(db: Session, lead_id: UUID) -> str | None:
    sequence = db.scalar(
        select(NurturingSequence)
        .where(NurturingSequence.lead_id == lead_id)
        .order_by(NurturingSequence.created_at.desc())
        .limit(1)
    )
    return sequence.prospect_whatsapp if sequence else None


def _resolve_public_gym_id() -> UUID:
    raw = (settings.public_diag_gym_id or "").strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PUBLIC_DIAG_GYM_ID nao configurado",
        )
    return UUID(raw)
