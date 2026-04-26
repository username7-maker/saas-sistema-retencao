from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Lead, LeadBooking, LeadStage
from app.schemas.acquisition import (
    AcquisitionCaptureInput,
    AcquisitionCaptureResponse,
    AcquisitionLeadSummaryOut,
    AcquisitionQualificationOut,
)
from app.services.tenant_guard import ensure_optional_user_in_gym

ACQUISITION_CAPTURE_NOTE_TYPE = "acquisition_capture"
ACQUISITION_QUALIFICATION_NOTE_TYPE = "acquisition_qualification"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _compact_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _latest_note(notes: list[Any] | None, note_type: str) -> dict[str, Any] | None:
    if not isinstance(notes, list):
        return None
    for note in reversed(notes):
        if isinstance(note, dict) and note.get("type") == note_type:
            return note
    return None


def _has_answer(payload: AcquisitionCaptureInput, key: str) -> bool:
    value = payload.qualification_answers.get(key)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | tuple | set | dict):
        return bool(value)
    return True


def generate_acquisition_qualification(payload: AcquisitionCaptureInput) -> AcquisitionQualificationOut:
    score = 0
    reasons: list[str] = []
    missing_fields: list[str] = []

    if _compact_text(payload.phone):
        score += 20
        reasons.append("Telefone disponivel para contato rapido.")
    else:
        missing_fields.append("telefone")

    if payload.email:
        score += 10
        reasons.append("E-mail disponivel para continuidade comercial.")
    else:
        missing_fields.append("email")

    if payload.scheduled_for:
        score += 25
        reasons.append("Aula experimental ja agendada.")
    elif payload.trial_interest:
        score += 15
        reasons.append("Lead demonstrou interesse em aula experimental.")
    else:
        missing_fields.append("aula_experimental")

    if _compact_text(payload.desired_goal):
        score += 15
        reasons.append("Objetivo declarado facilita abordagem consultiva.")
    else:
        missing_fields.append("objetivo")

    if _compact_text(payload.preferred_shift):
        score += 10
        reasons.append("Turno preferido informado para direcionamento.")
    else:
        missing_fields.append("turno_preferido")

    if _compact_text(payload.channel) or _compact_text(payload.campaign):
        score += 10
        reasons.append("Origem/campanha rastreavel para analise comercial.")
    else:
        missing_fields.append("canal_ou_campanha")

    if payload.consent_communication is True:
        score += 5
        reasons.append("Autorizou comunicacao operacional/comercial.")
    elif payload.consent_communication is False:
        missing_fields.append("consentimento_comunicacao")

    if _has_answer(payload, "urgency") or _has_answer(payload, "timeline"):
        score += 5
        reasons.append("Sinal de urgencia ou prazo informado.")

    score = max(0, min(100, score))

    if score >= 70:
        label = "hot"
        next_action = "Priorizar contato e preparar aula experimental."
    elif score >= 45:
        label = "warm"
        next_action = "Completar qualificacao e chamar no WhatsApp."
    else:
        label = "cold"
        next_action = "Qualificar interesse antes de mover no funil."

    if payload.scheduled_for:
        recommended_stage = LeadStage.TRIAL.value
        next_action = "Preparar aula experimental e confirmar presenca."
    elif payload.trial_interest:
        recommended_stage = LeadStage.VISIT.value
    elif _compact_text(payload.phone):
        recommended_stage = LeadStage.CONTACT.value
    else:
        recommended_stage = LeadStage.NEW.value

    return AcquisitionQualificationOut(
        score=score,
        label=label,
        next_action=next_action,
        recommended_stage=recommended_stage,
        reasons=reasons,
        missing_fields=missing_fields,
    )


def _build_capture_note(payload: AcquisitionCaptureInput) -> dict[str, Any]:
    return {
        "type": ACQUISITION_CAPTURE_NOTE_TYPE,
        "text": "Captura registrada pelo Acquisition OS.",
        "source": payload.source,
        "channel": _compact_text(payload.channel),
        "campaign": _compact_text(payload.campaign),
        "desired_goal": _compact_text(payload.desired_goal),
        "preferred_shift": _compact_text(payload.preferred_shift),
        "trial_interest": payload.trial_interest,
        "scheduled_for": payload.scheduled_for.isoformat() if payload.scheduled_for else None,
        "consent_lgpd": payload.consent_lgpd,
        "consent_communication": payload.consent_communication,
        "qualification_answers": payload.qualification_answers,
        "created_at": _now_iso(),
    }


def _build_qualification_note(qualification: AcquisitionQualificationOut) -> dict[str, Any]:
    return {
        "type": ACQUISITION_QUALIFICATION_NOTE_TYPE,
        "text": qualification.next_action,
        "score": qualification.score,
        "label": qualification.label,
        "next_action": qualification.next_action,
        "recommended_stage": qualification.recommended_stage,
        "reasons": qualification.reasons,
        "missing_fields": qualification.missing_fields,
        "created_at": _now_iso(),
    }


def summarize_acquisition_lead(lead: Lead, booking: LeadBooking | None = None) -> AcquisitionLeadSummaryOut:
    capture_note = _latest_note(lead.notes, ACQUISITION_CAPTURE_NOTE_TYPE) or {}
    qualification_note = _latest_note(lead.notes, ACQUISITION_QUALIFICATION_NOTE_TYPE) or {}

    next_booking_at = booking.scheduled_for if booking else None
    if next_booking_at is None and isinstance(capture_note.get("scheduled_for"), str):
        try:
            next_booking_at = datetime.fromisoformat(capture_note["scheduled_for"])
        except ValueError:
            next_booking_at = None

    return AcquisitionLeadSummaryOut(
        lead_id=lead.id,
        full_name=lead.full_name,
        source=capture_note.get("source") or lead.source,
        channel=capture_note.get("channel"),
        campaign=capture_note.get("campaign"),
        desired_goal=capture_note.get("desired_goal"),
        preferred_shift=capture_note.get("preferred_shift"),
        qualification_score=qualification_note.get("score"),
        qualification_label=qualification_note.get("label"),
        next_action=qualification_note.get("next_action"),
        has_trial_booking=booking is not None or bool(capture_note.get("scheduled_for")),
        next_booking_at=next_booking_at,
        consent_lgpd=capture_note.get("consent_lgpd"),
        consent_communication=capture_note.get("consent_communication"),
        reasons=list(qualification_note.get("reasons") or []),
        missing_fields=list(qualification_note.get("missing_fields") or []),
    )


def _latest_trial_booking(db: Session, lead_id: UUID) -> LeadBooking | None:
    return db.scalar(
        select(LeadBooking)
        .where(
            and_(
                LeadBooking.lead_id == lead_id,
                LeadBooking.status.in_(["confirmed", "scheduled", "pending"]),
            )
        )
        .order_by(LeadBooking.scheduled_for.desc())
    )


def capture_acquisition_lead(
    db: Session,
    payload: AcquisitionCaptureInput,
    *,
    gym_id: UUID,
    commit: bool = True,
) -> AcquisitionCaptureResponse:
    ensure_optional_user_in_gym(db, payload.owner_id, gym_id)
    qualification = generate_acquisition_qualification(payload)
    stage = LeadStage(qualification.recommended_stage)
    now = datetime.now(tz=timezone.utc)

    notes = [_build_capture_note(payload), _build_qualification_note(qualification)]
    operator_note = _compact_text(payload.operator_note)
    if operator_note:
        notes.append({"type": "note", "text": operator_note, "created_at": _now_iso()})
    lead = Lead(
        gym_id=gym_id,
        owner_id=payload.owner_id,
        full_name=payload.full_name.strip(),
        email=str(payload.email) if payload.email else None,
        phone=_compact_text(payload.phone),
        source=payload.source,
        stage=stage,
        estimated_value=payload.estimated_value,
        acquisition_cost=payload.acquisition_cost,
        last_contact_at=now if payload.phone or payload.email else None,
        notes=notes,
    )
    db.add(lead)
    db.flush()

    booking: LeadBooking | None = None
    if payload.scheduled_for:
        booking = LeadBooking(
            gym_id=gym_id,
            lead_id=lead.id,
            provider_name="trial_class",
            provider_booking_id=None,
            prospect_name=lead.full_name,
            prospect_email=lead.email,
            prospect_whatsapp=lead.phone,
            scheduled_for=payload.scheduled_for,
            status="confirmed",
            extra_data={
                "source": payload.source,
                "channel": _compact_text(payload.channel),
                "campaign": _compact_text(payload.campaign),
                "desired_goal": _compact_text(payload.desired_goal),
                "preferred_shift": _compact_text(payload.preferred_shift),
                "qualification_score": qualification.score,
                "qualification_label": qualification.label,
                "created_by": "acquisition_os",
            },
            confirmed_at=now,
        )
        db.add(booking)
        db.flush()

    if commit:
        db.commit()
        db.refresh(lead)
        if booking:
            db.refresh(booking)
    else:
        db.flush()
        db.refresh(lead)
        if booking:
            db.refresh(booking)

    invalidate_dashboard_cache("leads")
    summary = summarize_acquisition_lead(lead, booking)
    return AcquisitionCaptureResponse(lead=lead, booking=booking, qualification=qualification, summary=summary)


def get_acquisition_lead_summary(db: Session, lead_id: UUID, *, gym_id: UUID) -> AcquisitionLeadSummaryOut:
    lead = db.get(Lead, lead_id)
    if not lead or lead.deleted_at is not None or lead.gym_id != gym_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead nao encontrado")
    return summarize_acquisition_lead(lead, _latest_trial_booking(db, lead_id))


def list_acquisition_lead_summaries(db: Session, *, gym_id: UUID) -> list[AcquisitionLeadSummaryOut]:
    leads = db.scalars(
        select(Lead)
        .where(Lead.gym_id == gym_id, Lead.deleted_at.is_(None))
        .order_by(Lead.updated_at.desc())
        .limit(500)
    ).all()
    return [summarize_acquisition_lead(lead, _latest_trial_booking(db, lead.id)) for lead in leads]
