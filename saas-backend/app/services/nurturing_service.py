import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache, make_cache_key
from app.core.config import settings
from app.models import Lead, LeadStage, Member, MessageLog, NurturingSequence
from app.models.gym import Gym
from app.services.audit_service import log_audit_event
from app.services.crm_service import append_lead_note
from app.services.objection_service import generate_objection_response
from app.services.whatsapp_service import format_phone, get_gym_instance, normalize_phone, phones_match, send_whatsapp_sync
from app.utils.email import send_email

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


def pause_sequences_for_lead(db: Session, lead_id: UUID, reason: str) -> int:
    paused = 0
    sequences = list(
        db.scalars(
            select(NurturingSequence).where(
                NurturingSequence.lead_id == lead_id,
                NurturingSequence.completed.is_(False),
                NurturingSequence.paused_at.is_(None),
            )
        ).all()
    )
    now = datetime.now(tz=timezone.utc)
    for sequence in sequences:
        sequence.paused_at = now
        sequence.paused_reason = reason
        db.add(sequence)
        paused += 1
    db.flush()
    return paused


def run_nurturing_followup(db: Session) -> dict[str, int]:
    now = datetime.now(tz=timezone.utc)
    due_sequences = list(
        db.scalars(
            select(NurturingSequence).where(
                NurturingSequence.completed.is_(False),
                NurturingSequence.paused_at.is_(None),
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


def handle_incoming_whatsapp_webhook(
    db: Session,
    payload: dict[str, Any],
    *,
    gym_id: UUID | None = None,
) -> dict[str, Any]:
    event_name = _extract_event_name(payload)
    if not _is_received_message_event(event_name, payload):
        return {"processed": False, "detail": "Evento ignorado"}

    message = _extract_message_data(payload)
    if message["is_group"]:
        return {"processed": False, "detail": "Mensagem de grupo ignorada"}
    if message["from_me"]:
        return {"processed": False, "detail": "Mensagem propria ignorada"}
    if not message["phone"] or not message["text"]:
        return {"processed": False, "detail": "Payload sem telefone ou texto"}

    instance_name = _extract_instance_name(payload)
    resolved_gym_id = gym_id or _resolve_gym_id_from_instance(db, instance_name)
    sequence = find_active_sequence_by_phone(db, message["phone"], gym_id=resolved_gym_id)
    member = _find_member_by_phone(db, resolved_gym_id, message["phone"]) if resolved_gym_id else None
    if resolved_gym_id is None and sequence is not None:
        resolved_gym_id = sequence.gym_id
    if resolved_gym_id is None and member is not None:
        resolved_gym_id = member.gym_id
    if member is None and resolved_gym_id is not None:
        member = _find_member_by_phone(db, resolved_gym_id, message["phone"])

    if not sequence and not member:
        return {"processed": False, "detail": "Sem sequencia ativa ou membro correspondente"}

    inbound_log = MessageLog(
        gym_id=resolved_gym_id,
        member_id=member.id if member else None,
        lead_id=sequence.lead_id if sequence else None,
        channel="whatsapp",
        recipient=message["phone"],
        template_name=None,
        content=message["text"],
        status="received",
        direction="inbound",
        event_type=event_name,
        provider_message_id=message["provider_message_id"],
        extra_data={
            "raw_payload": payload,
            "instance_name": instance_name or None,
            "matched_member_id": str(member.id) if member else None,
        },
    )
    db.add(inbound_log)
    db.flush()

    if member:
        _record_member_inbound_response(
            db,
            member=member,
            message=message,
            event_name=event_name,
            instance_name=instance_name,
        )

    if sequence:
        _invalidate_sales_cache(sequence.lead_id)

    if not sequence:
        db.commit()
        return {"processed": True, "detail": "Resposta do aluno registrada"}

    response = generate_objection_response(
        db,
        message_text=message["text"],
        lead_id=sequence.lead_id,
        context=sequence.diagnosis_data,
        public_gym_id=sequence.gym_id,
    )
    if not response["matched"]:
        db.commit()
        return {"processed": True, "detail": "Mensagem registrada sem objecao"}

    _record_detected_objection(
        db,
        sequence=sequence,
        inbound_message=message["text"],
        response=response,
    )
    send_result = send_whatsapp_sync(
        db,
        phone=message["phone"],
        message=response["response_text"],
        instance=get_gym_instance(db, sequence.gym_id),
        lead_id=sequence.lead_id,
        template_name="custom",
        direction="outbound",
        event_type="objection_auto_reply",
    )
    _invalidate_sales_cache(sequence.lead_id)
    db.commit()
    return {
        "processed": True,
        "detail": "Objecao detectada e respondida" if send_result.status in {"sent", "skipped"} else "Objecao detectada",
    }


def find_active_sequence_by_phone(
    db: Session,
    phone: str,
    *,
    gym_id: UUID | None = None,
) -> NurturingSequence | None:
    target_gym_id = gym_id or _resolve_public_gym_id()
    target_phone = format_phone(phone)
    candidates = list(
        db.scalars(
            select(NurturingSequence)
            .execution_options(include_all_tenants=True)
            .where(
                NurturingSequence.gym_id == target_gym_id,
                NurturingSequence.completed.is_(False),
                NurturingSequence.paused_at.is_(None),
            )
            .order_by(NurturingSequence.created_at.desc())
        ).all()
    )
    for item in candidates:
        candidate_phone = format_phone(item.prospect_whatsapp)
        if phones_match(candidate_phone, target_phone):
            return item
    return None


def _find_member_by_phone(db: Session, gym_id: UUID | None, phone: str) -> Member | None:
    if not gym_id:
        return None

    target_phone = normalize_phone(phone)
    if not target_phone:
        return None

    candidates = list(
        db.scalars(
            select(Member)
            .execution_options(include_all_tenants=True)
            .where(
                Member.gym_id == gym_id,
                Member.deleted_at.is_(None),
            )
        ).all()
    )
    for member in candidates:
        if phones_match(member.phone, target_phone):
            return member
    return None


def _record_member_inbound_response(
    db: Session,
    *,
    member: Member,
    message: dict[str, Any],
    event_name: str,
    instance_name: str,
) -> None:
    log_audit_event(
        db,
        action="member_whatsapp_inbound",
        entity="contact_log",
        gym_id=member.gym_id,
        member_id=member.id,
        details={
            "channel": "whatsapp",
            "outcome": "answered",
            "event_type": event_name,
            "phone": message["phone"],
            "message_preview": message["text"][:280],
            "instance_name": instance_name or None,
        },
    )


def _extract_instance_name(payload: dict[str, Any]) -> str:
    raw_instance = payload.get("instance")
    if isinstance(raw_instance, str):
        return raw_instance.strip()
    if isinstance(raw_instance, dict):
        return str(
            raw_instance.get("instanceName")
            or raw_instance.get("name")
            or raw_instance.get("instance")
            or ""
        ).strip()
    return str(payload.get("instanceName") or "").strip()


def _resolve_gym_id_from_instance(db: Session, instance_name: str) -> UUID | None:
    if not instance_name:
        return None
    gym = db.scalar(
        select(Gym)
        .where(Gym.whatsapp_instance == instance_name)
    )
    return getattr(gym, "id", None)


def list_sent_nurturing_steps(sequence: NurturingSequence | None) -> list[int]:
    if not sequence:
        return []
    if sequence.completed:
        return [step for step in NURTURING_STEP_ORDER if step <= sequence.current_step]
    return [step for step in NURTURING_STEP_ORDER if step < sequence.current_step]


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
        instance = get_gym_instance(db, sequence.gym_id)
        message = _whatsapp_message_for_step(sequence, step)
        result = send_whatsapp_sync(
            db,
            phone=sequence.prospect_whatsapp,
            message=message,
            instance=instance,
            lead_id=sequence.lead_id,
            template_name="custom",
            direction="outbound",
            event_type=f"nurturing_d{step}",
        )
        return result.status in {"sent", "skipped"}

    subject, body = _email_for_step(sequence, step)
    if not subject:
        return False
    sent_ok = send_email(sequence.prospect_email, subject, body)
    _record_email_dispatch(db, sequence, subject, body, sent_ok, f"nurturing_d{step}")
    return sent_ok


def _record_email_dispatch(
    db: Session,
    sequence: NurturingSequence,
    subject: str,
    body: str,
    sent_ok: bool,
    event_type: str,
) -> None:
    db.add(
        MessageLog(
            lead_id=sequence.lead_id,
            channel="email",
            recipient=sequence.prospect_email,
            template_name=event_type,
            content=f"{subject}\n\n{body}",
            status="sent" if sent_ok else "failed",
            direction="outbound",
            event_type=event_type,
            extra_data={"subject": subject},
        )
    )
    db.flush()


def _record_detected_objection(
    db: Session,
    *,
    sequence: NurturingSequence,
    inbound_message: str,
    response: dict[str, Any],
) -> None:
    if not sequence.lead_id:
        return
    lead = db.get(Lead, sequence.lead_id)
    if not lead:
        return
    append_lead_note(
        db,
        lead,
        {
            "type": "objection_detected",
            "message_text": inbound_message,
            "response_text": response["response_text"],
            "objection_id": str(response["objection_id"]) if response.get("objection_id") else None,
            "source": response["source"],
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


def _invalidate_sales_cache(lead_id: UUID | None) -> None:
    if not lead_id:
        return
    dashboard_cache.delete(make_cache_key("sales_brief", lead_id))
    dashboard_cache.delete(make_cache_key("call_script", lead_id))


def _extract_event_name(payload: dict[str, Any]) -> str:
    return str(payload.get("event") or payload.get("type") or payload.get("eventType") or "").strip().lower()


def _is_received_message_event(event_name: str, payload: dict[str, Any]) -> bool:
    if event_name in {"message.received", "messages.upsert", "message_upsert", "message_created"}:
        return True
    data = payload.get("data")
    return isinstance(data, dict) and ("message" in data or "text" in data or "body" in data)


def _extract_message_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if not isinstance(data, dict):
        data = payload

    key = data.get("key") if isinstance(data.get("key"), dict) else {}
    remote_jid = str(key.get("remoteJid") or data.get("from") or data.get("sender") or "").strip()
    phone = remote_jid.split("@", 1)[0] if "@" in remote_jid else remote_jid
    phone = format_phone(phone) if phone else ""

    body = ""
    message = data.get("message")
    if isinstance(message, dict):
        body = (
            str(message.get("conversation") or "").strip()
            or str(message.get("text") or "").strip()
            or str(message.get("extendedTextMessage", {}).get("text") or "").strip()
        )
    body = body or str(data.get("text") or data.get("body") or "").strip()

    return {
        "phone": phone,
        "text": body,
        "from_me": bool(key.get("fromMe") or data.get("fromMe") or False),
        "is_group": bool(str(remote_jid).endswith("@g.us") or data.get("isGroup") or False),
        "provider_message_id": str(key.get("id") or data.get("id") or "").strip() or None,
    }


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


def _resolve_public_gym_id() -> UUID:
    raw = (settings.public_diag_gym_id or "").strip()
    if not raw:
        raise RuntimeError("PUBLIC_DIAG_GYM_ID nao configurado")
    return UUID(raw)
