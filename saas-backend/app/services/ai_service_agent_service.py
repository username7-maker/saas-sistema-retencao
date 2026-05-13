from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AutopilotAction, AutopilotEvent, Gym, Member, MessageLog
from app.schemas.ai_service_agent import (
    AiServiceAgentDraftOut,
    AiServiceAgentPrepareResultOut,
    AiServiceAgentSettingsOut,
    AiServiceAgentSettingsUpdate,
)
from app.services.autopilot_event_service import record_event
from app.services.autopilot_settings_service import get_or_create_autopilot_settings
from app.services.compliance_service import current_consent_status_map
from app.services.kommo_service import handoff_member_to_kommo, is_kommo_ready

AI_SERVICE_AGENT_EXTRA_KEY = "ai_service_agent"
AI_SERVICE_AGENT_ACTION_TYPE = "kommo_draft_reply"
AI_SERVICE_AGENT_DRAFT_READY = "draft_ready"

DEFAULT_AI_SERVICE_AGENT_SETTINGS = {
    "enabled": False,
    "mode": "draft_only",
    "auto_send_enabled": False,
    "sensitive_escalation_enabled": True,
    "kommo_required": True,
    "max_drafts_per_day": 100,
    "human_recent_activity_cooldown_hours": 24,
    "allowed_intents": ["general", "onboarding", "retention", "assessment", "finance", "sales", "support"],
}

SENSITIVE_INTENTS = {"cancellation", "injury", "finance_dispute", "opt_out", "human_request", "complaint"}
OPT_OUT_TERMS = ("parar", "remover", "sair da lista", "nao autorizo", "não autorizo", "sem mensagem", "opt-out")
HUMAN_TERMS = ("humano", "gerente", "responsavel", "responsável", "atendente", "falar com alguem", "falar com alguém")
COMPLAINT_TERMS = ("reclamacao", "reclamação", "reclamar", "processo", "advogado", "assedio", "assédio", "agressao", "agressão")
CANCELLATION_TERMS = ("cancelar", "cancelamento", "trancar", "trancamento", "encerrar plano", "sair da academia")
INJURY_TERMS = ("lesao", "lesão", "dor forte", "machuquei", "emergencia", "emergência", "lesionado")
FINANCE_DISPUTE_TERMS = ("ja paguei", "já paguei", "cobranca indevida", "cobrança indevida", "chargeback", "nao reconheco", "não reconheço")


@dataclass(frozen=True)
class ServiceAgentClassification:
    intent: str
    sensitivity: str
    summary: str
    next_action: str
    recommended_owner_role: str
    blocked_reasons: list[str]
    evidence: list[str]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def get_ai_service_agent_settings(db: Session, *, gym_id: UUID) -> AiServiceAgentSettingsOut:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    payload = _merge_settings((settings.extra_data or {}).get(AI_SERVICE_AGENT_EXTRA_KEY))
    return AiServiceAgentSettingsOut(**payload)


def update_ai_service_agent_settings(
    db: Session,
    *,
    gym_id: UUID,
    payload: AiServiceAgentSettingsUpdate,
) -> AiServiceAgentSettingsOut:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    current = _merge_settings((settings.extra_data or {}).get(AI_SERVICE_AGENT_EXTRA_KEY))
    updates = payload.model_dump(exclude_unset=True)
    updates["auto_send_enabled"] = False
    if updates.get("mode") and updates["mode"] != "draft_only":
        updates["mode"] = "draft_only"
    current.update(updates)
    current = _merge_settings(current)

    extra = dict(settings.extra_data or {})
    extra[AI_SERVICE_AGENT_EXTRA_KEY] = current
    settings.extra_data = extra
    db.add(settings)
    db.flush()
    return AiServiceAgentSettingsOut(**current)


def process_kommo_inbound_for_ai_agent(
    db: Session,
    *,
    gym_id: UUID,
    member: Member,
    message_text: str,
    event: AutopilotEvent,
    message_log_id: UUID | None = None,
    kommo_contact_id: str | None = None,
    kommo_lead_id: str | None = None,
    flush: bool = True,
) -> AiServiceAgentDraftOut | None:
    settings = get_ai_service_agent_settings(db, gym_id=gym_id)
    if not settings.enabled:
        return None

    gym = db.get(Gym, gym_id)
    classification = classify_kommo_message(message_text)
    blocked_reasons = list(classification.blocked_reasons)

    if settings.kommo_required and (gym is None or getattr(gym, "primary_message_channel", None) != "kommo"):
        blocked_reasons.append("kommo_not_primary_channel")
    if settings.kommo_required and (gym is None or not is_kommo_ready(gym)):
        blocked_reasons.append("kommo_not_ready")
    if not _member_has_communication_consent(db, member):
        blocked_reasons.append("missing_communication_consent")
    if _member_is_vip(member):
        blocked_reasons.append("vip_member_requires_human")
    if _has_recent_human_kommo_activity(db, gym_id=gym_id, member_id=member.id, hours=settings.human_recent_activity_cooldown_hours):
        blocked_reasons.append("recent_human_activity")
    if _drafts_created_today(db, gym_id=gym_id) >= settings.max_drafts_per_day:
        blocked_reasons.append("daily_draft_limit_reached")
    if not message_text.strip():
        blocked_reasons.append("empty_message")

    status_value = "escalated" if classification.intent in SENSITIVE_INTENTS else AI_SERVICE_AGENT_DRAFT_READY
    if blocked_reasons:
        status_value = "blocked" if classification.intent not in SENSITIVE_INTENTS else "escalated"

    draft_reply = None if blocked_reasons or classification.intent in SENSITIVE_INTENTS else _draft_reply_for_member(member, classification.intent)
    metadata = {
        "ai_service_agent_state": status_value,
        "intent": classification.intent,
        "sensitivity": classification.sensitivity,
        "summary": classification.summary,
        "draft_reply": draft_reply,
        "next_action": classification.next_action,
        "recommended_owner_role": classification.recommended_owner_role,
        "blocked_reasons": blocked_reasons,
        "evidence": classification.evidence,
        "received_message": message_text,
        "kommo_contact_id": kommo_contact_id,
        "kommo_lead_id": kommo_lead_id,
        "source_event_id": str(event.id),
        "message_log_id": str(message_log_id) if message_log_id else None,
        "auto_send_enabled": False,
        "mode": "draft_only",
    }
    idempotency_key = f"ai-service-agent:kommo-inbound:{event.id}"
    existing = db.scalar(
        select(AutopilotAction).where(
            AutopilotAction.gym_id == gym_id,
            AutopilotAction.idempotency_key == idempotency_key,
        )
    )
    if existing:
        return serialize_ai_service_agent_draft(existing)

    action = AutopilotAction(
        gym_id=gym_id,
        policy_key=f"ai_service_agent_{classification.intent}",
        domain=_domain_for_intent(classification.intent),
        action_type=AI_SERVICE_AGENT_ACTION_TYPE,
        status=status_value,
        member_id=member.id,
        lead_id=None,
        channel="kommo",
        template_key=f"ai_service_agent_{classification.intent}",
        message_body=draft_reply,
        timeout_at=_now() + timedelta(hours=48),
        max_attempts=1,
        idempotency_key=idempotency_key,
        failure_reason=",".join(blocked_reasons) if blocked_reasons else None,
        escalation_reason=classification.summary if status_value == "escalated" else None,
        metadata_json=metadata,
    )
    db.add(action)
    db.flush()

    record_event(
        db,
        gym_id=gym_id,
        event_type="ai_service_agent_draft_created" if status_value == AI_SERVICE_AGENT_DRAFT_READY else "human_intervention_required",
        source="ai_service_agent",
        member_id=member.id,
        autopilot_action_id=action.id,
        metadata={
            "intent": classification.intent,
            "status": status_value,
            "blocked_reasons": blocked_reasons,
            "source_event_id": str(event.id),
        },
        flush=False,
    )
    if flush:
        db.flush()
    return serialize_ai_service_agent_draft(action)


def list_ai_service_agent_drafts(
    db: Session,
    *,
    gym_id: UUID,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[AiServiceAgentDraftOut]:
    query = select(AutopilotAction).where(
        AutopilotAction.gym_id == gym_id,
        AutopilotAction.action_type == AI_SERVICE_AGENT_ACTION_TYPE,
    )
    if status_filter:
        query = query.where(AutopilotAction.status == status_filter)
    actions = db.scalars(query.order_by(AutopilotAction.created_at.desc()).limit(limit)).all()
    return [serialize_ai_service_agent_draft(action) for action in actions]


def prepare_ai_service_agent_draft_in_kommo(
    db: Session,
    *,
    gym_id: UUID,
    draft_id: UUID,
    flush: bool = True,
) -> AiServiceAgentPrepareResultOut:
    action = db.scalar(
        select(AutopilotAction).where(
            AutopilotAction.gym_id == gym_id,
            AutopilotAction.id == draft_id,
            AutopilotAction.action_type == AI_SERVICE_AGENT_ACTION_TYPE,
        )
    )
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rascunho do agente IA nao encontrado.")
    if action.status != AI_SERVICE_AGENT_DRAFT_READY:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este rascunho nao esta pronto para preparar na Kommo.")
    member = db.get(Member, action.member_id) if action.member_id else None
    if member is None or member.gym_id != gym_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno do rascunho nao encontrado.")

    metadata = dict(action.metadata_json or {})
    summary = "\n".join(
        part
        for part in [
            "Agente IA Kommo V1 - revisar resposta antes de enviar.",
            f"Resumo: {metadata.get('summary') or '-'}",
            f"Mensagem recebida: {metadata.get('received_message') or '-'}",
            f"Resposta sugerida: {action.message_body or '-'}",
            f"Proxima acao: {metadata.get('next_action') or '-'}",
            f"Evidencias: {', '.join(metadata.get('evidence') or []) or '-'}",
        ]
        if part
    )
    result = handoff_member_to_kommo(
        db,
        gym_id=gym_id,
        member=member,
        title=f"Revisar resposta IA - {member.full_name}"[:120],
        summary=summary,
        source="ai_service_agent",
        due_in_hours=4,
    )
    if result.status != "sent":
        action.status = "failed"
        action.failure_reason = result.detail or result.status
        db.add(action)
        record_event(
            db,
            gym_id=gym_id,
            event_type="ai_service_agent_prepare_kommo_failed",
            source="ai_service_agent",
            member_id=member.id,
            autopilot_action_id=action.id,
            metadata={"detail": result.detail, "status": result.status},
            flush=False,
        )
        if flush:
            db.flush()
        return AiServiceAgentPrepareResultOut(draft=serialize_ai_service_agent_draft(action), detail=result.detail or result.status)

    metadata.update(
        {
            "kommo_contact_id": result.contact_id,
            "kommo_lead_id": result.lead_id,
            "kommo_task_id": result.task_id,
            "prepared_at": _now().isoformat(),
            "ai_service_agent_state": "waiting_human_review",
        }
    )
    action.status = "awaiting_outcome"
    action.metadata_json = metadata
    db.add(action)
    _record_ai_service_agent_kommo_handoff_log(db, action=action, member=member, result=result)
    record_event(
        db,
        gym_id=gym_id,
        event_type="ai_service_agent_draft_prepared_kommo",
        source="ai_service_agent",
        member_id=member.id,
        autopilot_action_id=action.id,
        metadata={
            "kommo_contact_id": result.contact_id,
            "kommo_lead_id": result.lead_id,
            "kommo_task_id": result.task_id,
        },
        flush=False,
    )
    if flush:
        db.flush()
    return AiServiceAgentPrepareResultOut(
        draft=serialize_ai_service_agent_draft(action),
        detail="Rascunho preparado na Kommo para revisao humana.",
        kommo_contact_id=result.contact_id,
        kommo_lead_id=result.lead_id,
        kommo_task_id=result.task_id,
    )


def serialize_ai_service_agent_draft(action: AutopilotAction) -> AiServiceAgentDraftOut:
    metadata = dict(action.metadata_json or {})
    return AiServiceAgentDraftOut(
        id=action.id,
        status=action.status,
        gym_id=action.gym_id,
        member_id=action.member_id,
        lead_id=action.lead_id,
        intent=str(metadata.get("intent") or action.domain or "general"),
        sensitivity=str(metadata.get("sensitivity") or "normal"),
        summary=str(metadata.get("summary") or action.policy_key),
        draft_reply=action.message_body or metadata.get("draft_reply"),
        next_action=str(metadata.get("next_action") or "Revisar atendimento na Kommo."),
        recommended_owner_role=str(metadata.get("recommended_owner_role") or "reception"),
        blocked_reasons=list(metadata.get("blocked_reasons") or []),
        evidence=list(metadata.get("evidence") or []),
        received_message=metadata.get("received_message"),
        kommo_contact_id=metadata.get("kommo_contact_id"),
        kommo_lead_id=metadata.get("kommo_lead_id"),
        kommo_task_id=metadata.get("kommo_task_id"),
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


def classify_kommo_message(message_text: str) -> ServiceAgentClassification:
    normalized = _normalize_text(message_text)
    matched_sensitive = _matched_sensitive_intent(normalized)
    if matched_sensitive:
        intent, next_action, owner = matched_sensitive
        return ServiceAgentClassification(
            intent=intent,
            sensitivity="sensitive",
            summary=f"Mensagem sensivel detectada: {intent}.",
            next_action=next_action,
            recommended_owner_role=owner,
            blocked_reasons=[f"sensitive_{intent}"],
            evidence=["kommo_inbound", "sensitive_keyword"],
        )

    intent = "general"
    owner = "reception"
    if any(term in normalized for term in ("avaliacao", "avaliação", "bioimpedancia", "bioimpedância", "treino", "professor")):
        intent = "assessment"
        owner = "coach"
    elif any(term in normalized for term in ("voltar", "treinar", "horario", "horário", "frequencia", "frequência")):
        intent = "retention"
    elif any(term in normalized for term in ("plano", "preco", "preço", "mensalidade", "visita", "experimental")):
        intent = "sales"
        owner = "sales"
    elif any(term in normalized for term in ("pagamento", "boleto", "pix", "cartao", "cartão")):
        intent = "finance"
        owner = "manager"
    elif any(term in normalized for term in ("primeira vez", "comecei", "novo aluno", "app")):
        intent = "onboarding"
    return ServiceAgentClassification(
        intent=intent,
        sensitivity="normal",
        summary=f"Mensagem Kommo classificada como {intent}.",
        next_action="Revisar resposta sugerida e enviar pela Kommo.",
        recommended_owner_role=owner,
        blocked_reasons=[],
        evidence=["kommo_inbound", f"intent:{intent}", "draft_only"],
    )


def _merge_settings(raw: dict | None) -> dict:
    merged = {**DEFAULT_AI_SERVICE_AGENT_SETTINGS, **(raw or {})}
    merged["mode"] = "draft_only"
    merged["auto_send_enabled"] = False
    if not isinstance(merged.get("allowed_intents"), list):
        merged["allowed_intents"] = list(DEFAULT_AI_SERVICE_AGENT_SETTINGS["allowed_intents"])
    return merged


def _matched_sensitive_intent(normalized: str) -> tuple[str, str, str] | None:
    if any(term in normalized for term in OPT_OUT_TERMS):
        return ("opt_out", "Registrar opt-out e pausar comunicacoes automaticas.", "manager")
    if any(term in normalized for term in CANCELLATION_TERMS):
        return ("cancellation", "Assumir conversa e tratar risco de cancelamento.", "manager")
    if any(term in normalized for term in INJURY_TERMS):
        return ("injury", "Encaminhar para professor/gestor antes de responder.", "coach")
    if any(term in normalized for term in FINANCE_DISPUTE_TERMS):
        return ("finance_dispute", "Escalar para gestor/financeiro revisar cobranca.", "manager")
    if any(term in normalized for term in COMPLAINT_TERMS):
        return ("complaint", "Escalar para gestor antes de responder.", "manager")
    if any(term in normalized for term in HUMAN_TERMS):
        return ("human_request", "Humano deve assumir a conversa.", "reception")
    return None


def _draft_reply_for_member(member: Member, intent: str) -> str:
    first_name = ((member.full_name or "").split(" ")[0] or "tudo bem").strip()
    templates = {
        "assessment": f"Oi, {first_name}! Consigo te ajudar com isso. Vou confirmar o melhor encaminhamento com o professor e ja te retorno por aqui.",
        "retention": f"Oi, {first_name}! Que bom te ver por aqui. Me diz qual horario fica mais facil para voce retomar os treinos esta semana?",
        "sales": f"Oi, {first_name}! Posso te ajudar sim. Vou separar a melhor opcao e te mando os detalhes por aqui.",
        "finance": f"Oi, {first_name}! Vou conferir sua situacao e te retorno com as opcoes corretas para regularizar.",
        "onboarding": f"Oi, {first_name}! Bem-vindo(a). Vou te orientar no proximo passo para voce comecar bem.",
        "general": f"Oi, {first_name}! Recebi sua mensagem. Vou verificar o contexto e ja te retorno por aqui.",
    }
    return templates.get(intent, templates["general"])


def _member_has_communication_consent(db: Session, member: Member) -> bool:
    try:
        consent_map = current_consent_status_map(db, member.id, gym_id=member.gym_id)
        return consent_map.get("communication") is True
    except Exception:
        extra = getattr(member, "extra_data", None) or {}
        consents = extra.get("consents") if isinstance(extra.get("consents"), dict) else {}
        return bool(
            consents.get("communication") is True
            or consents.get("whatsapp_consent") is True
            or extra.get("communication_consent") is True
            or extra.get("whatsapp_consent") is True
        )


def _has_recent_human_kommo_activity(db: Session, *, gym_id: UUID, member_id: UUID, hours: int) -> bool:
    if hours <= 0:
        return False
    since = _now() - timedelta(hours=hours)
    recent = db.scalar(
        select(MessageLog.id)
        .where(
            MessageLog.gym_id == gym_id,
            MessageLog.member_id == member_id,
            MessageLog.channel == "kommo",
            MessageLog.direction == "outbound",
            MessageLog.created_at >= since,
            MessageLog.event_type.in_(["kommo_human_reply", "kommo_operator_manual", "kommo_manual_reply"]),
        )
        .limit(1)
    )
    return recent is not None


def _drafts_created_today(db: Session, *, gym_id: UUID) -> int:
    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    value = db.scalar(
        select(func.count(AutopilotAction.id)).where(
            AutopilotAction.gym_id == gym_id,
            AutopilotAction.action_type == AI_SERVICE_AGENT_ACTION_TYPE,
            AutopilotAction.created_at >= today_start,
        )
    )
    return int(value or 0)


def _record_ai_service_agent_kommo_handoff_log(db: Session, *, action: AutopilotAction, member: Member, result) -> None:
    db.add(
        MessageLog(
            gym_id=action.gym_id,
            member_id=member.id,
            lead_id=None,
            channel="kommo",
            recipient=(member.phone or member.email or str(member.id)),
            template_name=action.template_key,
            content=action.message_body or "",
            status="sent",
            direction="outbound",
            event_type="ai_service_agent_kommo_draft",
            provider_message_id=result.task_id,
            extra_data={
                "autopilot_action_id": str(action.id),
                "source": "ai_service_agent",
                "kommo_contact_id": result.contact_id,
                "kommo_lead_id": result.lead_id,
                "kommo_task_id": result.task_id,
                "operator_review_required": True,
            },
        )
    )


def _domain_for_intent(intent: str) -> str:
    if intent in {"cancellation", "complaint", "human_request", "opt_out"}:
        return "support"
    if intent == "injury":
        return "assessment"
    if intent == "finance_dispute":
        return "finance"
    return intent if intent in {"retention", "onboarding", "assessment", "finance", "sales", "support"} else "support"


def _member_is_vip(member: Member) -> bool:
    return bool(getattr(member, "is_vip", False))


def _normalize_text(value: str) -> str:
    return (value or "").strip().lower()
