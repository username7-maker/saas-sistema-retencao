import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Lead, LeadStage, NurturingSequence
from app.utils.email import send_email
from app.services.whatsapp_service import send_whatsapp_sync

logger = logging.getLogger(__name__)

NURTURING_STEP_ORDER = [0, 1, 3, 5, 7]


def next_nurturing_step(current_step: int) -> int | None:
    try:
        index = NURTURING_STEP_ORDER.index(current_step)
    except ValueError:
        return None
    if index == len(NURTURING_STEP_ORDER) - 1:
        return None
    return NURTURING_STEP_ORDER[index + 1]


def calculate_next_send_at(created_at: datetime, next_step: int | None) -> datetime | None:
    if next_step is None:
        return None
    return created_at + timedelta(days=next_step)


def create_nurturing_sequence(
    db: Session,
    *,
    gym_id: UUID | None,
    lead_id: UUID | None,
    prospect_email: str,
    prospect_whatsapp: str,
    prospect_name: str,
    diagnosis_data: dict[str, Any],
) -> NurturingSequence:
    now = datetime.now(tz=timezone.utc)
    sequence = NurturingSequence(
        gym_id=gym_id,
        lead_id=lead_id,
        prospect_email=prospect_email,
        prospect_whatsapp=prospect_whatsapp,
        prospect_name=prospect_name,
        diagnosis_data=diagnosis_data,
        current_step=0,
        next_send_at=now,
        completed=False,
    )
    db.add(sequence)
    db.commit()
    db.refresh(sequence)
    return sequence


def run_nurturing_followup(db: Session) -> dict[str, int]:
    now = datetime.now(tz=timezone.utc)
    due_sequences = list(
        db.scalars(
            select(NurturingSequence).where(
                NurturingSequence.completed.is_(False),
                NurturingSequence.next_send_at <= now,
            )
        ).all()
    )

    processed = 0
    sent = 0
    skipped_won = 0
    completed_count = 0

    for sequence in due_sequences:
        processed += 1
        if _stop_if_lead_won(db, sequence):
            skipped_won += 1
            completed_count += 1
            continue

        sent_ok = _dispatch_step(db, sequence)
        if sent_ok:
            sent += 1

        next_step = next_nurturing_step(sequence.current_step)
        if next_step is None:
            sequence.completed = True
            completed_count += 1
        else:
            sequence.current_step = next_step
            next_send = calculate_next_send_at(sequence.created_at, next_step)
            if next_send:
                sequence.next_send_at = next_send
        db.add(sequence)

    db.commit()
    return {
        "processed": processed,
        "sent": sent,
        "skipped_won": skipped_won,
        "completed": completed_count,
    }


def _stop_if_lead_won(db: Session, sequence: NurturingSequence) -> bool:
    if not sequence.lead_id:
        return False
    lead = db.get(Lead, sequence.lead_id)
    if not lead or lead.stage != LeadStage.WON:
        return False

    sequence.completed = True
    details = dict(sequence.diagnosis_data or {})
    details["stop_reason"] = "lead_won"
    sequence.diagnosis_data = details
    db.add(sequence)
    return True


def _dispatch_step(db: Session, sequence: NurturingSequence) -> bool:
    step = sequence.current_step
    if step in {0, 3, 7}:
        message = _whatsapp_message_for_step(sequence, step)
        result = send_whatsapp_sync(
            db,
            phone=sequence.prospect_whatsapp,
            message=message,
            template_name="custom",
        )
        return result.status in {"sent", "skipped"}

    subject, body = _email_for_step(sequence, step)
    if not subject:
        return False
    return send_email(sequence.prospect_email, subject, body)


def _diagnosis_numbers(sequence: NurturingSequence) -> tuple[int, int, float]:
    data = sequence.diagnosis_data or {}
    at_risk = int(data.get("at_risk_total") or 0)
    total_members = int(data.get("total_members") or 0)
    mrr_at_risk = float(data.get("mrr_at_risk") or 0.0)
    return at_risk, total_members, mrr_at_risk


def _whatsapp_message_for_step(sequence: NurturingSequence, step: int) -> str:
    at_risk, total_members, mrr_at_risk = _diagnosis_numbers(sequence)
    weekly_lost_estimate = round(total_members * 0.015)

    fallback: dict[int, str] = {
        0: (
            f"Ola {sequence.prospect_name}! Seu diagnostico AI GYM OS ficou pronto. "
            f"Hoje voce tem {at_risk} alunos em risco e R$ {mrr_at_risk:,.2f} de MRR em risco. "
            f"Agende uma conversa: {settings.public_booking_url}"
        ),
        3: (
            f"{sequence.prospect_name}, analisando seu diagnostico: {at_risk} alunos em risco "
            f"e impacto mensal de R$ {mrr_at_risk:,.2f}. Em 15 min mostramos como recuperar isso."
        ),
        7: (
            f"Ultima mensagem, {sequence.prospect_name}: mantendo o cenario atual, a estimativa e perder "
            f"{weekly_lost_estimate} alunos por semana. Quer ver o plano de recuperacao? {settings.public_booking_url}"
        ),
    }
    return _claude_or_fallback(
        prompt=(
            "Escreva uma mensagem curta de WhatsApp para um prospect de academia. "
            f"Passo D{step}. Nome: {sequence.prospect_name}. "
            f"Alunos em risco: {at_risk}. Total de alunos: {total_members}. MRR em risco: {mrr_at_risk}. "
            f"Link de agenda: {settings.public_booking_url}."
        ),
        fallback=fallback.get(step, fallback[0]),
    )


def _email_for_step(sequence: NurturingSequence, step: int) -> tuple[str, str]:
    at_risk, total_members, mrr_at_risk = _diagnosis_numbers(sequence)
    gym_size = "pequena" if total_members < 300 else ("media" if total_members <= 800 else "grande")

    if step == 1:
        subject = f"Case real para academia {gym_size}: retencao previsivel"
        body = (
            f"Ola {sequence.prospect_name},\n\n"
            f"Em academias de porte {gym_size}, vimos reducao de churn quando o acompanhamento "
            "vira processo diario automatizado.\n"
            f"No seu caso, existem {at_risk} alunos em risco e R$ {mrr_at_risk:,.2f} em risco mensal.\n\n"
            f"Se quiser, te mostramos em 15 min: {settings.public_booking_url}\n"
        )
        return subject, _claude_or_fallback(
            prompt=(
                "Escreva email comercial curto para academia, com tom consultivo e CTA para demo de 15 min. "
                f"Porte: {gym_size}; Nome: {sequence.prospect_name}; Alunos em risco: {at_risk}; "
                f"MRR em risco: {mrr_at_risk}; Link: {settings.public_booking_url}."
            ),
            fallback=body,
        )

    if step == 5:
        subject = "Convite: demonstracao de 15 minutos com os dados da sua academia"
        body = (
            f"Ola {sequence.prospect_name},\n\n"
            "Reservamos uma demonstracao rapida para te mostrar o AI GYM OS usando seus numeros reais.\n"
            f"Agenda: {settings.public_booking_url}\n\n"
            "A apresentacao leva 15 minutos."
        )
        return subject, _claude_or_fallback(
            prompt=(
                "Escreva email de convite para demo de 15 minutos, objetivo e direto. "
                f"Nome: {sequence.prospect_name}. Link de agenda: {settings.public_booking_url}."
            ),
            fallback=body,
        )

    return "", ""


def _claude_or_fallback(*, prompt: str, fallback: str) -> str:
    if not settings.claude_api_key:
        return fallback
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        return text[:1200] or fallback
    except Exception:
        logger.exception("Falha no Claude, usando fallback da regua")
        return fallback
