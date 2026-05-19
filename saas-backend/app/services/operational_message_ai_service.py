from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import Lead, LeadStage, Member, MemberStatus, Task
from app.services.ai_prompt_registry_service import generate_specialist_text, prompt_metadata
from app.services.autopilot_safety_service import contains_sensitive_text


PROMPT_BY_DOMAIN = {
    "retention": "retention_copy_agent_v1",
    "onboarding": "onboarding_copy_agent_v1",
    "finance": "finance_copy_agent_v1",
    "commercial": "commercial_copy_agent_v1",
    "sales": "commercial_copy_agent_v1",
}


@dataclass
class OperationalMessageDraft:
    message: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    message_source: str = "template_safe"
    blocked_reasons: list[str] = field(default_factory=list)
    fallback_used: bool = True


def generate_operational_message_draft(
    db: Session | None,
    *,
    domain: str,
    base_message: str | None,
    member: Member | None = None,
    lead: Lead | None = None,
    task: Task | None = None,
    context: dict[str, Any] | None = None,
    max_output_chars: int = 520,
) -> OperationalMessageDraft:
    """Generate a supervised operational message draft, falling back safely."""

    normalized_domain = (domain or "task").strip().lower()
    prompt_key = PROMPT_BY_DOMAIN.get(normalized_domain, "task_copy_agent_v1")
    fallback_text = (base_message or "").strip()
    blocked_reasons = _copy_blockers(
        domain=normalized_domain,
        base_message=fallback_text,
        member=member,
        lead=lead,
        task=task,
        context=context or {},
    )

    if blocked_reasons:
        metadata = prompt_metadata(prompt_key, model="blocked_by_safety", fallback_used=True)
        metadata.update(
            {
                "message_source": "blocked_by_safety",
                "blocked_reasons": blocked_reasons,
            }
        )
        return OperationalMessageDraft(
            message=fallback_text or None,
            metadata=metadata,
            message_source="blocked_by_safety",
            blocked_reasons=blocked_reasons,
            fallback_used=True,
        )

    if not fallback_text:
        metadata = prompt_metadata(prompt_key, model="deterministic_fallback", fallback_used=True)
        metadata.update({"message_source": "template_safe", "blocked_reasons": []})
        return OperationalMessageDraft(message=None, metadata=metadata, message_source="template_safe")

    user_prompt = _build_user_prompt(
        domain=normalized_domain,
        base_message=fallback_text,
        member=member,
        lead=lead,
        task=task,
        context=context or {},
    )
    result = generate_specialist_text(
        prompt_key,
        user_prompt=user_prompt,
        fallback_text=fallback_text,
        max_output_chars=max_output_chars,
    )
    message_source = "template_safe" if result.used_fallback else "ai_specialist"
    metadata = dict(result.metadata)
    metadata.update(
        {
            "message_source": message_source,
            "blocked_reasons": [],
        }
    )
    return OperationalMessageDraft(
        message=result.text.strip() or fallback_text,
        metadata=metadata,
        message_source=message_source,
        blocked_reasons=[],
        fallback_used=result.used_fallback,
    )


def _copy_blockers(
    *,
    domain: str,
    base_message: str,
    member: Member | None,
    lead: Lead | None,
    task: Task | None,
    context: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    text_parts = [
        base_message,
        getattr(task, "title", None),
        getattr(task, "description", None),
        " ".join(str(item) for item in context.get("why_now_details") or []),
        str(context.get("last_message") or ""),
    ]
    if contains_sensitive_text(" ".join(part for part in text_parts if part)):
        reasons.append("sensitive_text")
    if member and getattr(member, "status", None) == MemberStatus.CANCELLED:
        reasons.append("member_cancelled")
    if member and bool(getattr(member, "is_vip", False)):
        reasons.append("vip_member_requires_human")
    if lead and getattr(lead, "stage", None) in {LeadStage.WON, LeadStage.LOST}:
        reasons.append("lead_closed")
    if _explicit_opt_out(member):
        reasons.append("opt_out")
    if domain == "finance" and _finance_dispute_hint(base_message, context):
        reasons.append("finance_dispute")
    return list(dict.fromkeys(reasons))


def _explicit_opt_out(member: Member | None) -> bool:
    if member is None:
        return False
    extra = getattr(member, "extra_data", None) or {}
    if not isinstance(extra, dict):
        return False
    keys = {
        "opt_out",
        "communication_opt_out",
        "whatsapp_opt_out",
        "lgpd_opt_out",
        "do_not_contact",
    }
    return any(bool(extra.get(key)) for key in keys)


def _finance_dispute_hint(base_message: str, context: dict[str, Any]) -> bool:
    text = " ".join(
        [
            base_message,
            str(context.get("finance_status") or ""),
            str(context.get("last_message") or ""),
            str(context.get("reason") or ""),
        ]
    ).lower()
    return any(term in text for term in ("ja paguei", "cobranca indevida", "contestou", "contestacao", "chargeback"))


def _build_user_prompt(
    *,
    domain: str,
    base_message: str,
    member: Member | None,
    lead: Lead | None,
    task: Task | None,
    context: dict[str, Any],
) -> str:
    identity = _subject_identity(member=member, lead=lead)
    lines = [
        "Melhore a mensagem abaixo para uso supervisionado pela equipe.",
        "Regras: ate 3 frases, sem promessas, sem pressao, sem inventar fatos, sem autoenvio.",
        f"Dominio: {domain}.",
        f"Pessoa: {identity}.",
    ]
    if task is not None:
        lines.extend(
            [
                f"Tarefa: {task.title}.",
                f"Descricao da tarefa: {task.description or 'sem descricao'}.",
            ]
        )
    if member is not None:
        lines.extend(
            [
                f"Status do aluno: {getattr(member.status, 'value', member.status)}.",
                f"Plano: {member.plan_name or 'nao informado'}.",
                f"Risco: {getattr(getattr(member, 'risk_level', None), 'value', None) or 'sem risco'} / {int(member.risk_score or 0)}.",
                f"Estagio de retencao: {getattr(member, 'retention_stage', None) or 'nao informado'}.",
                f"Ultimo check-in: {_format_datetime(getattr(member, 'last_checkin_at', None))}.",
            ]
        )
    if lead is not None:
        lines.extend(
            [
                f"Etapa do lead: {getattr(lead.stage, 'value', lead.stage)}.",
                f"Origem do lead: {lead.source}.",
            ]
        )
    for key, value in sorted((context or {}).items()):
        if value is None or value == "":
            continue
        if key in {"metadata", "raw", "payload"}:
            continue
        lines.append(f"{key}: {value}")
    lines.extend(
        [
            "Mensagem base:",
            base_message,
            "Retorne somente a mensagem final, sem titulo e sem explicacao.",
        ]
    )
    return "\n".join(lines)


def _subject_identity(*, member: Member | None, lead: Lead | None) -> str:
    subject = member or lead
    if subject is None:
        return "sem pessoa vinculada"
    return getattr(subject, "full_name", None) or "sem nome"


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "sem registro"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
