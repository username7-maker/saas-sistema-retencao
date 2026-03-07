import json
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache, make_cache_key
from app.core.config import settings
from app.models import AuditLog, Lead, LeadBooking, LeadStage, MessageLog, NurturingSequence
from app.services.nurturing_service import list_sent_nurturing_steps

logger = logging.getLogger(__name__)
SALES_BRIEF_CACHE_TTL_SECONDS = 4 * 60 * 60

SYSTEM_KEYWORDS = {
    "tecnofit": "Tecnofit",
    "evo": "Evo",
    "nextfit": "NextFit",
    "nexusfit": "NexusFit",
    "pacto": "Pacto",
}


def get_sales_brief(db: Session, lead_id: UUID) -> dict[str, Any]:
    lead = db.scalar(select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None)))
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead nao encontrado")

    sequence = _latest_sequence(db, lead_id)
    diagnosis = _build_diagnosis_summary(sequence)
    history = _build_history(db, lead, sequence)
    ai_payload = _generate_cached_sales_ai(lead, diagnosis, history)

    return {
        "profile": {
            "lead_id": lead.id,
            "full_name": lead.full_name,
            "email": lead.email,
            "phone": lead.phone,
            "source": lead.source,
            "stage": lead.stage.value,
            "gym_name": _infer_gym_name(lead, sequence),
            "city": _infer_city(lead),
            "estimated_members": _infer_estimated_members(sequence),
            "avg_monthly_fee": _infer_avg_monthly_fee(sequence),
            "current_management_system": _detect_management_system(lead, history),
        },
        "diagnosis": diagnosis,
        "history": history,
        "ai_arguments": ai_payload["arguments"],
        "next_step_recommended": ai_payload["next_step"],
    }


def _latest_sequence(db: Session, lead_id: UUID) -> NurturingSequence | None:
    return db.scalar(
        select(NurturingSequence)
        .where(NurturingSequence.lead_id == lead_id)
        .order_by(NurturingSequence.created_at.desc())
        .limit(1)
    )


def _build_diagnosis_summary(sequence: NurturingSequence | None) -> dict[str, Any]:
    if not sequence or not isinstance(sequence.diagnosis_data, dict):
        return {
            "has_diagnosis": False,
            "message": "Prospect sem diagnostico - considere oferecer durante a call.",
            "red_total": 0,
            "yellow_total": 0,
            "mrr_at_risk": 0.0,
            "annual_loss_projection": 0.0,
            "estimated_recovered_members": 0,
            "estimated_preserved_annual_revenue": 0.0,
        }

    data = sequence.diagnosis_data
    return {
        "has_diagnosis": True,
        "message": None,
        "red_total": int(data.get("red_total") or 0),
        "yellow_total": int(data.get("yellow_total") or 0),
        "mrr_at_risk": float(data.get("mrr_at_risk") or 0.0),
        "annual_loss_projection": float(data.get("annual_loss_projection") or 0.0),
        "estimated_recovered_members": int(data.get("estimated_recovered_members") or 0),
        "estimated_preserved_annual_revenue": float(data.get("estimated_preserved_annual_revenue") or 0.0),
    }


def _build_history(db: Session, lead: Lead, sequence: NurturingSequence | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for note in lead.notes or []:
        if not isinstance(note, dict):
            continue
        history_item = _history_from_note(note)
        if history_item:
            items.append(history_item)

    if sequence:
        for step in list_sent_nurturing_steps(sequence):
            items.append(
                {
                    "kind": "nurturing_step",
                    "channel": "mixed",
                    "title": f"Regua D{step} enviada",
                    "detail": _nurturing_step_detail(step),
                    "occurred_at": sequence.created_at + timedelta(days=step),
                    "metadata": {"step": step},
                }
            )

    message_logs = list(
        db.scalars(
            select(MessageLog)
            .where(MessageLog.lead_id == lead.id)
            .order_by(MessageLog.created_at.asc())
        ).all()
    )
    for log in message_logs:
        items.append(
            {
                "kind": "message",
                "channel": log.channel,
                "title": _message_log_title(log),
                "detail": log.content[:240],
                "occurred_at": log.created_at,
                "metadata": {
                    "status": log.status,
                    "direction": log.direction,
                    "event_type": log.event_type,
                },
            }
        )

    bookings = list(
        db.scalars(
            select(LeadBooking)
            .where(LeadBooking.lead_id == lead.id)
            .order_by(LeadBooking.scheduled_for.asc())
        ).all()
    )
    for booking in bookings:
        items.append(
            {
                "kind": "booking",
                "channel": "calendar",
                "title": "Call agendada",
                "detail": f"{booking.scheduled_for.strftime('%d/%m/%Y %H:%M UTC')} via {booking.provider_name or 'agenda publica'}",
                "occurred_at": booking.confirmed_at,
                "metadata": {"booking_id": str(booking.id), "status": booking.status},
            }
        )

    call_audits = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity == "lead",
                AuditLog.entity_id == lead.id,
                AuditLog.action.in_(
                    [
                        "call_event_logged",
                        "proposal_auto_followup_created",
                        "lead_booking_confirmed",
                    ]
                ),
            )
            .order_by(AuditLog.created_at.asc())
        ).all()
    )
    for audit in call_audits:
        items.append(
            {
                "kind": "audit",
                "channel": "system",
                "title": audit.action.replace("_", " ").title(),
                "detail": json.dumps(audit.details, ensure_ascii=True)[:240] if audit.details else None,
                "occurred_at": audit.created_at,
                "metadata": audit.details or {},
            }
        )

    items.sort(key=lambda item: item["occurred_at"])
    return items


def _generate_cached_sales_ai(lead: Lead, diagnosis: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    cache_key = make_cache_key("sales_brief", lead.id)
    cached = dashboard_cache.get(cache_key)
    if isinstance(cached, dict) and "arguments" in cached and "next_step" in cached:
        return cached

    objections = _extract_known_objections(lead)
    fallback = _fallback_sales_ai(lead, diagnosis, objections)
    if not settings.claude_api_key:
        dashboard_cache.set(cache_key, fallback, ttl=SALES_BRIEF_CACHE_TTL_SECONDS)
        return fallback

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        prompt = (
            "Voce e um closer de SaaS B2B para academias. "
            "Retorne JSON com campos arguments e next_step. "
            "arguments deve ser uma lista com exatamente 3 itens, cada um com title, body, usage. "
            "O title deve ter no maximo 8 palavras. "
            "Use dados reais do prospect.\n"
            f"Lead: nome={lead.full_name}, origem={lead.source}, stage={lead.stage.value}\n"
            f"Diagnostico: {diagnosis}\n"
            f"Historico recente: {history[-8:]}\n"
            f"Objecoes conhecidas: {objections}\n"
        )
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = _parse_ai_json(response.content[0].text.strip())
        result = {
            "arguments": parsed.get("arguments") or fallback["arguments"],
            "next_step": parsed.get("next_step") or fallback["next_step"],
        }
        dashboard_cache.set(cache_key, result, ttl=SALES_BRIEF_CACHE_TTL_SECONDS)
        return result
    except Exception:
        logger.exception("Falha ao gerar sales brief com Claude")
        dashboard_cache.set(cache_key, fallback, ttl=SALES_BRIEF_CACHE_TTL_SECONDS)
        return fallback


def _fallback_sales_ai(lead: Lead, diagnosis: dict[str, Any], objections: list[str]) -> dict[str, Any]:
    arguments = [
        {
            "title": "Risco financeiro concreto",
            "body": (
                f"O diagnostico aponta R$ {diagnosis['mrr_at_risk']:,.2f} de MRR em risco e "
                f"{diagnosis['red_total']} alunos em vermelho. O foco da call deve ser custo da inacao."
            )
            if diagnosis["has_diagnosis"]
            else "Sem diagnostico formal, conduza a conversa para quantificar churn, inatividade e receita em risco.",
            "usage": "Use na abertura ou quando o decisor minimizar o problema atual.",
        },
        {
            "title": "Automacao reduz carga",
            "body": "Mostre que a equipe nao precisa operar planilhas ou perseguir dados manualmente; o fluxo vira rotina automatizada.",
            "usage": "Use quando surgir objecao de tempo ou operacao.",
        },
        {
            "title": "Plano orientado a recuperacao",
            "body": "Posicione o AI GYM OS como uma camada de recuperacao de receita e nao apenas mais um dashboard.",
            "usage": "Use no fechamento para conectar retorno financeiro com proximo passo.",
        },
    ]
    next_step = "enviar_proposta_apos_call" if lead.stage in {LeadStage.MEETING_SCHEDULED, LeadStage.PROPOSAL} else "agendar_call"
    if objections:
        next_step = "tratar_objecoes_e_validar_decisor"
    return {"arguments": arguments, "next_step": next_step}


def _extract_known_objections(lead: Lead) -> list[str]:
    objections: list[str] = []
    for note in getattr(lead, "notes", None) or []:
        if not isinstance(note, dict):
            continue
        if note.get("type") == "objection_detected":
            text = str(note.get("message_text") or "").strip()
            if text:
                objections.append(text)
    return objections


def _history_from_note(note: dict[str, Any]) -> dict[str, Any] | None:
    note_type = str(note.get("type") or "").strip()
    created_at = _parse_note_datetime(note.get("created_at"))
    if not created_at:
        return None

    if note_type == "public_diagnosis_requested":
        return {
            "kind": "diagnosis",
            "channel": "public_form",
            "title": "Diagnostico solicitado",
            "detail": f"Academia: {note.get('gym_name') or 'nao informada'}",
            "occurred_at": created_at,
            "metadata": note,
        }
    if note_type == "public_diagnosis_completed":
        return {
            "kind": "diagnosis",
            "channel": "system",
            "title": "Diagnostico concluido",
            "detail": f"MRR em risco: R$ {float(note.get('kpis', {}).get('mrr_at_risk') or 0):,.2f}",
            "occurred_at": created_at,
            "metadata": note,
        }
    if note_type == "booking_confirmed":
        return {
            "kind": "booking",
            "channel": "calendar",
            "title": "Agendamento confirmado",
            "detail": str(note.get("scheduled_for") or ""),
            "occurred_at": created_at,
            "metadata": note,
        }
    if note_type == "objection_detected":
        return {
            "kind": "objection",
            "channel": "whatsapp",
            "title": "Objecao detectada",
            "detail": str(note.get("message_text") or "")[:240],
            "occurred_at": created_at,
            "metadata": note,
        }
    return None


def _message_log_title(log: MessageLog) -> str:
    direction = (log.direction or "").strip().lower()
    if direction == "inbound":
        return "Mensagem recebida"
    if log.channel == "email":
        return "Email enviado"
    return "WhatsApp enviado"


def _nurturing_step_detail(step: int) -> str:
    details = {
        0: "WhatsApp de entrega do diagnostico",
        1: "Email com case adaptado ao porte da academia",
        3: "WhatsApp reforcando a dor com numeros reais",
        5: "Email convite para demo de 15 minutos",
        7: "WhatsApp final com senso de urgencia",
    }
    return details.get(step, "Contato da regua automatica")


def _infer_gym_name(lead: Lead, sequence: NurturingSequence | None) -> str | None:
    if sequence and isinstance(sequence.diagnosis_data, dict):
        gym_name = str(sequence.diagnosis_data.get("gym_name") or "").strip()
        if gym_name:
            return gym_name
    for note in getattr(lead, "notes", None) or []:
        if isinstance(note, dict):
            candidate = str(note.get("gym_name") or "").strip()
            if candidate:
                return candidate
    return None


def _infer_city(lead: Lead) -> str | None:
    for note in getattr(lead, "notes", None) or []:
        if isinstance(note, dict):
            candidate = str(note.get("city") or "").strip()
            if candidate:
                return candidate
    return None


def _infer_estimated_members(sequence: NurturingSequence | None) -> int | None:
    if sequence and isinstance(sequence.diagnosis_data, dict):
        total = sequence.diagnosis_data.get("total_members")
        return int(total) if total is not None else None
    return None


def _infer_avg_monthly_fee(sequence: NurturingSequence | None) -> float | None:
    if sequence and isinstance(sequence.diagnosis_data, dict):
        avg_fee = sequence.diagnosis_data.get("avg_monthly_fee")
        return float(avg_fee) if avg_fee is not None else None
    return None


def _detect_management_system(lead: Lead, history: list[dict[str, Any]]) -> str | None:
    haystacks = [lead.source or ""]
    for note in getattr(lead, "notes", None) or []:
        if isinstance(note, dict):
            haystacks.append(str(note.get("message_text") or ""))
            haystacks.append(str(note.get("response_text") or ""))
    for item in history:
        haystacks.append(str(item.get("detail") or ""))

    normalized = _normalize_text(" ".join(haystacks))
    for keyword, label in SYSTEM_KEYWORDS.items():
        if keyword in normalized:
            return label
    return None


def _parse_note_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _normalize_text(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def _parse_ai_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        return json.loads(fenced.group(1))

    inline = re.search(r"(\{.*\})", text, flags=re.S)
    if inline:
        return json.loads(inline.group(1))

    raise ValueError("Resposta AI invalida para sales brief")
