from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Lead, LeadStage, Member, MemberStatus, NPSResponse, RiskLevel, Task, TaskPriority, TaskStatus
from app.schemas.growth import (
    GrowthAudienceOut,
    GrowthChannel,
    GrowthOpportunityOut,
    GrowthOpportunityPrepareInput,
    GrowthOpportunityPreparedOut,
)
from app.services.compliance_service import current_consent_status_map
from app.services.crm_service import append_lead_note


OPEN_LEAD_STAGES = {
    LeadStage.NEW,
    LeadStage.CONTACT,
    LeadStage.VISIT,
    LeadStage.TRIAL,
    LeadStage.PROPOSAL,
    LeadStage.MEETING_SCHEDULED,
    LeadStage.PROPOSAL_SENT,
}

AUDIENCE_META: dict[str, dict[str, str]] = {
    "conversion_hot_leads": {
        "label": "Conversao de leads quentes",
        "objective": "Priorizar leads com maior chance de virar matricula.",
        "cta": "Preparar abordagem",
        "summary": "Leads com score alto, aula experimental ou sinais claros de intencao.",
        "experiment": "Teste abordagem curta por WhatsApp contra ligacao consultiva para leads com aula agendada.",
    },
    "conversion_stale_leads": {
        "label": "Leads parados",
        "objective": "Recuperar oportunidades abertas antes que esfriem.",
        "cta": "Retomar contato",
        "summary": "Leads abertos sem contato recente ou nunca contatados.",
        "experiment": "Teste mensagem direta com pergunta de horario contra oferta de remarcacao de visita.",
    },
    "reactivation_inactive_members": {
        "label": "Reativacao de alunos inativos",
        "objective": "Trazer de volta alunos ativos que reduziram presenca.",
        "cta": "Preparar reativacao",
        "summary": "Alunos ativos com muitos dias sem check-in.",
        "experiment": "Teste convite para treino guiado contra check-in por WhatsApp com professor.",
    },
    "renewal_attention": {
        "label": "Renovacao com atencao",
        "objective": "Antecipar risco em planos longos com queda de engajamento.",
        "cta": "Preparar conversa",
        "summary": "Alunos em planos semestral/anual com sinais de esfriamento.",
        "experiment": "Teste conversa de meta/resultado contra oferta de reavaliacao.",
    },
    "upsell_promoters": {
        "label": "Promotores para upsell/indicacao",
        "objective": "Aproveitar alunos satisfeitos para upgrade ou indicacao.",
        "cta": "Preparar convite",
        "summary": "Alunos com bom NPS, risco baixo e relacao estavel com a academia.",
        "experiment": "Teste convite de indicacao contra oferta de plano/beneficio adicional.",
    },
    "nps_recovery": {
        "label": "Recuperacao de NPS",
        "objective": "Resolver insatisfacao sinalizada antes de virar churn.",
        "cta": "Preparar recuperacao",
        "summary": "Alunos com NPS baixo ou feedback negativo recente.",
        "experiment": "Teste ligacao do gerente contra abordagem inicial do professor responsavel.",
    },
}


def list_growth_audiences(db: Session, *, gym_id: UUID, limit_per_audience: int = 25) -> list[GrowthAudienceOut]:
    limit = max(1, min(100, limit_per_audience))
    lead_items = _build_lead_opportunities(db, gym_id=gym_id)
    member_items = _build_member_opportunities(db, gym_id=gym_id)
    by_audience: dict[str, list[GrowthOpportunityOut]] = {
        key: [] for key in AUDIENCE_META
    }
    for item in [*lead_items, *member_items]:
        by_audience.setdefault(item.audience_id, []).append(item)

    audiences: list[GrowthAudienceOut] = []
    for audience_id, meta in AUDIENCE_META.items():
        items = sorted(by_audience.get(audience_id, []), key=lambda item: item.score, reverse=True)
        audiences.append(
            GrowthAudienceOut(
                id=audience_id,  # type: ignore[arg-type]
                label=meta["label"],
                objective=meta["objective"],
                count=len(items),
                priority=_audience_priority(items),
                recommended_channel=_audience_channel(items),
                cta_label=meta["cta"],
                summary=meta["summary"],
                experiment_hint=meta["experiment"],
                items=items[:limit],
            )
        )
    return audiences


def prepare_growth_opportunity(
    db: Session,
    *,
    gym_id: UUID,
    opportunity_id: str,
    payload: GrowthOpportunityPrepareInput,
    actor_id: UUID | None = None,
    actor_name: str | None = None,
    actor_role: str | None = None,
    commit: bool = True,
) -> GrowthOpportunityPreparedOut:
    opportunity = _find_opportunity(db, gym_id=gym_id, opportunity_id=opportunity_id)
    channel = payload.channel or opportunity.channel
    warnings: list[str] = []
    if opportunity.consent_required and not opportunity.consent_ok:
        warnings.append("Consentimento de comunicacao ausente ou nao confirmado. Revise antes de enviar mensagem.")
    if channel == "whatsapp" and not opportunity.contact:
        warnings.append("Contato sem telefone. Use tarefa interna ou atualize o cadastro antes do WhatsApp.")

    task_id = None
    crm_note_created = False
    if payload.create_task or channel == "task":
        task_id = _create_growth_task(db, gym_id=gym_id, opportunity=opportunity, operator_note=payload.operator_note)

    if opportunity.subject_type == "lead":
        lead = _get_lead(db, opportunity.subject_id, gym_id=gym_id)
        note_text = _build_operator_note(opportunity, payload.operator_note)
        append_lead_note(
            db,
            lead,
            {
                "type": "growth_prepare",
                "channel": channel,
                "outcome": "prepared",
                "note": note_text,
                "text": note_text,
                "audience_id": opportunity.audience_id,
                "opportunity_id": opportunity.id,
                "author_id": str(actor_id) if actor_id else None,
                "author_name": actor_name,
                "author_role": actor_role,
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        lead.last_contact_at = datetime.now(tz=timezone.utc)
        db.add(lead)
        crm_note_created = True

    if commit:
        db.commit()
    else:
        db.flush()

    if task_id:
        invalidate_dashboard_cache("tasks")
    if opportunity.subject_type == "lead":
        invalidate_dashboard_cache("leads")

    return GrowthOpportunityPreparedOut(
        opportunity_id=opportunity.id,
        prepared_action="manual_review_required" if warnings else "ready",
        action_label=opportunity.action_label,
        channel=channel,
        target_name=opportunity.display_name,
        message=opportunity.suggested_message,
        whatsapp_url=_build_whatsapp_url(opportunity.contact, opportunity.suggested_message)
        if channel == "whatsapp"
        else None,
        task_id=task_id,
        crm_note_created=crm_note_created,
        kommo_status="not_configured_in_this_action" if channel == "kommo" else None,
        warnings=warnings,
    )


def _build_lead_opportunities(db: Session, *, gym_id: UUID) -> list[GrowthOpportunityOut]:
    leads = list(
        db.scalars(
            select(Lead)
            .where(Lead.gym_id == gym_id, Lead.deleted_at.is_(None), Lead.stage.in_(OPEN_LEAD_STAGES))
            .order_by(Lead.updated_at.desc())
            .limit(500)
        ).all()
    )
    opportunities: list[GrowthOpportunityOut] = []
    for lead in leads:
        capture = _latest_note(lead.notes, "acquisition_capture")
        qualification = _latest_note(lead.notes, "acquisition_qualification")
        qualification_score = _coerce_int(qualification.get("score") if qualification else None, default=0)
        has_trial = bool(capture and capture.get("scheduled_for")) or lead.stage == LeadStage.TRIAL
        consent_ok = bool(capture and capture.get("consent_communication") is True)
        preferred_shift = _string_value(capture.get("preferred_shift") if capture else None)
        channel = _lead_channel(lead)

        if qualification_score >= 70 or has_trial:
            score = min(100, max(qualification_score, 70) + (10 if has_trial else 0))
            opportunities.append(
                GrowthOpportunityOut(
                    id=_opportunity_id("lead", lead.id, "conversion_hot_leads"),
                    audience_id="conversion_hot_leads",
                    subject_type="lead",
                    subject_id=lead.id,
                    display_name=lead.full_name,
                    contact=lead.phone or lead.email,
                    preferred_shift=preferred_shift,
                    stage_or_status=lead.stage.value,
                    score=score,
                    priority="high" if score < 90 else "urgent",
                    channel=channel,
                    action_label="Confirmar aula e avancar matricula" if has_trial else "Priorizar contato comercial",
                    reason="Lead com alta propensao por score, origem ou aula experimental.",
                    suggested_message=_lead_hot_message(lead, capture),
                    next_step="Registrar contato e mover o lead no funil conforme resposta.",
                    consent_required=True,
                    consent_ok=consent_ok,
                    source_tags=_lead_tags(lead, capture, qualification),
                    metadata={"qualification_score": qualification_score, "has_trial": has_trial},
                )
            )

        days_without_contact = _days_since(lead.last_contact_at or lead.updated_at)
        if days_without_contact is None or days_without_contact >= 3:
            stale_days = days_without_contact or 999
            score = min(100, 55 + min(30, stale_days * 3))
            opportunities.append(
                GrowthOpportunityOut(
                    id=_opportunity_id("lead", lead.id, "conversion_stale_leads"),
                    audience_id="conversion_stale_leads",
                    subject_type="lead",
                    subject_id=lead.id,
                    display_name=lead.full_name,
                    contact=lead.phone or lead.email,
                    preferred_shift=preferred_shift,
                    stage_or_status=lead.stage.value,
                    score=score,
                    priority="urgent" if stale_days >= 7 else "high",
                    channel=channel,
                    action_label="Retomar lead parado",
                    reason="Lead aberto sem contato recente no CRM.",
                    suggested_message=_lead_stale_message(lead, stale_days),
                    next_step="Registrar resposta ou motivo de perda para limpar o funil.",
                    consent_required=True,
                    consent_ok=consent_ok,
                    source_tags=_lead_tags(lead, capture, qualification),
                    metadata={"days_without_contact": stale_days, "qualification_score": qualification_score},
                )
            )
    return opportunities


def _build_member_opportunities(db: Session, *, gym_id: UUID) -> list[GrowthOpportunityOut]:
    members = list(
        db.scalars(
            select(Member)
            .where(Member.gym_id == gym_id, Member.deleted_at.is_(None), Member.status == MemberStatus.ACTIVE)
            .order_by(Member.updated_at.desc())
            .limit(800)
        ).all()
    )
    latest_nps = _latest_nps_by_member(db, gym_id=gym_id)
    opportunities: list[GrowthOpportunityOut] = []
    for member in members:
        consent_ok = _member_communication_ok(db, member)
        days_inactive = _days_since(member.last_checkin_at)
        preferred_shift = member.preferred_shift or _string_value((member.extra_data or {}).get("preferred_shift"))
        nps_score = latest_nps.get(member.id, member.nps_last_score)

        if days_inactive is not None and days_inactive >= 14:
            score = min(100, 60 + min(35, days_inactive))
            opportunities.append(
                GrowthOpportunityOut(
                    id=_opportunity_id("member", member.id, "reactivation_inactive_members"),
                    audience_id="reactivation_inactive_members",
                    subject_type="member",
                    subject_id=member.id,
                    display_name=member.full_name,
                    contact=member.phone or member.email,
                    preferred_shift=preferred_shift,
                    stage_or_status=member.risk_level.value,
                    score=score,
                    priority="urgent" if days_inactive >= 30 or member.risk_level == RiskLevel.RED else "high",
                    channel=_member_channel(member),
                    action_label="Reativar aluno inativo",
                    reason=f"Aluno ativo ha {days_inactive} dias sem check-in.",
                    suggested_message=_member_reactivation_message(member, days_inactive),
                    next_step="Registrar retorno do aluno e criar tarefa de acompanhamento se houver obstaculo.",
                    consent_required=True,
                    consent_ok=consent_ok,
                    source_tags=["retencao", "inatividade", member.risk_level.value],
                    metadata={"days_inactive": days_inactive, "risk_score": member.risk_score},
                )
            )

        plan_name = (member.plan_name or "").lower()
        is_long_cycle = any(token in plan_name for token in ("anual", "semestral", "12", "6 "))
        if is_long_cycle and ((days_inactive is not None and days_inactive >= 21) or (nps_score is not None and nps_score <= 7)):
            score = 75 + (10 if nps_score is not None and nps_score <= 6 else 0)
            opportunities.append(
                GrowthOpportunityOut(
                    id=_opportunity_id("member", member.id, "renewal_attention"),
                    audience_id="renewal_attention",
                    subject_type="member",
                    subject_id=member.id,
                    display_name=member.full_name,
                    contact=member.phone or member.email,
                    preferred_shift=preferred_shift,
                    stage_or_status=member.plan_name,
                    score=min(100, score),
                    priority="high",
                    channel=_member_channel(member),
                    action_label="Antecipar conversa de renovacao",
                    reason="Plano longo com sinal de queda de engajamento ou satisfacao.",
                    suggested_message=_member_renewal_message(member),
                    next_step="Registrar contexto no perfil do aluno antes de qualquer oferta.",
                    consent_required=True,
                    consent_ok=consent_ok,
                    source_tags=["renovacao", "plano_longo"],
                    metadata={"nps_score": nps_score, "days_inactive": days_inactive},
                )
            )

        if nps_score is not None and nps_score <= 6:
            opportunities.append(
                GrowthOpportunityOut(
                    id=_opportunity_id("member", member.id, "nps_recovery"),
                    audience_id="nps_recovery",
                    subject_type="member",
                    subject_id=member.id,
                    display_name=member.full_name,
                    contact=member.phone or member.email,
                    preferred_shift=preferred_shift,
                    stage_or_status=f"NPS {nps_score}",
                    score=90 if nps_score <= 4 else 80,
                    priority="urgent" if nps_score <= 4 else "high",
                    channel="task",
                    action_label="Tratar NPS baixo",
                    reason="Aluno registrou NPS baixo e precisa de contato humano.",
                    suggested_message=_member_nps_recovery_message(member),
                    next_step="Gerente/professor conversa, registra causa e acao combinada.",
                    consent_required=False,
                    consent_ok=True,
                    source_tags=["nps", "recuperacao"],
                    metadata={"nps_score": nps_score},
                )
            )

        if nps_score is not None and nps_score >= 9 and member.risk_level == RiskLevel.GREEN and (days_inactive is None or days_inactive <= 7):
            opportunities.append(
                GrowthOpportunityOut(
                    id=_opportunity_id("member", member.id, "upsell_promoters"),
                    audience_id="upsell_promoters",
                    subject_type="member",
                    subject_id=member.id,
                    display_name=member.full_name,
                    contact=member.phone or member.email,
                    preferred_shift=preferred_shift,
                    stage_or_status=f"NPS {nps_score}",
                    score=75 + min(20, max(0, member.loyalty_months)),
                    priority="medium",
                    channel=_member_channel(member),
                    action_label="Convidar para indicacao ou upgrade",
                    reason="Aluno satisfeito, ativo e com baixo risco.",
                    suggested_message=_member_promoter_message(member),
                    next_step="Usar abordagem consultiva, sem pressionar venda.",
                    consent_required=True,
                    consent_ok=consent_ok,
                    source_tags=["upsell", "indicacao", "promotor"],
                    metadata={"nps_score": nps_score, "loyalty_months": member.loyalty_months},
                )
            )
    return opportunities


def _find_opportunity(db: Session, *, gym_id: UUID, opportunity_id: str) -> GrowthOpportunityOut:
    for audience in list_growth_audiences(db, gym_id=gym_id, limit_per_audience=100):
        for item in audience.items:
            if item.id == opportunity_id:
                return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidade de growth nao encontrada")


def _get_lead(db: Session, lead_id: UUID, *, gym_id: UUID) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead or lead.deleted_at is not None or lead.gym_id != gym_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead nao encontrado")
    return lead


def _create_growth_task(
    db: Session,
    *,
    gym_id: UUID,
    opportunity: GrowthOpportunityOut,
    operator_note: str | None,
) -> UUID:
    existing = db.scalar(
        select(Task).where(
            Task.gym_id == gym_id,
            Task.member_id == (opportunity.subject_id if opportunity.subject_type == "member" else None),
            Task.lead_id == (opportunity.subject_id if opportunity.subject_type == "lead" else None),
            Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
            Task.deleted_at.is_(None),
            Task.extra_data["growth_opportunity_id"].astext == opportunity.id,
        )
    )
    if existing:
        return existing.id

    task = Task(
        gym_id=gym_id,
        member_id=opportunity.subject_id if opportunity.subject_type == "member" else None,
        lead_id=opportunity.subject_id if opportunity.subject_type == "lead" else None,
        title=opportunity.action_label,
        description=_build_operator_note(opportunity, operator_note),
        priority=TaskPriority.URGENT if opportunity.priority == "urgent" else TaskPriority.HIGH,
        status=TaskStatus.TODO,
        kanban_column=TaskStatus.TODO.value,
        suggested_message=opportunity.suggested_message,
        extra_data={
            "source": "growth_os",
            "audience_id": opportunity.audience_id,
            "growth_opportunity_id": opportunity.id,
            "preferred_shift": opportunity.preferred_shift,
        },
    )
    db.add(task)
    db.flush()
    return task.id


def _latest_nps_by_member(db: Session, *, gym_id: UUID) -> dict[UUID, int]:
    rows = list(
        db.scalars(
            select(NPSResponse)
            .where(NPSResponse.gym_id == gym_id, NPSResponse.member_id.isnot(None))
            .order_by(NPSResponse.response_date.desc())
            .limit(1000)
        ).all()
    )
    latest: dict[UUID, int] = {}
    for response in rows:
        if response.member_id and response.member_id not in latest:
            latest[response.member_id] = response.score
    return latest


def _member_communication_ok(db: Session, member: Member) -> bool:
    try:
        consent_map = current_consent_status_map(db, member.id, gym_id=member.gym_id)
        return bool(consent_map.get("communication") is True)
    except Exception:
        extra = member.extra_data or {}
        return bool(extra.get("consent_communication") is True or extra.get("lgpd_consent") is True)


def _latest_note(notes: list[Any] | None, note_type: str) -> dict[str, Any] | None:
    if not isinstance(notes, list):
        return None
    for note in reversed(notes):
        if isinstance(note, dict) and note.get("type") == note_type:
            return note
    return None


def _opportunity_id(subject_type: str, subject_id: UUID, audience_id: str) -> str:
    return f"{audience_id}:{subject_type}:{subject_id}"


def _days_since(value: datetime | None) -> int | None:
    if value is None:
        return None
    ref = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(tz=timezone.utc) - ref).days)


def _coerce_int(value: object, *, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _string_value(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _lead_channel(lead: Lead) -> GrowthChannel:
    return "whatsapp" if lead.phone else "task"


def _member_channel(member: Member) -> GrowthChannel:
    return "whatsapp" if member.phone else "task"


def _audience_priority(items: list[GrowthOpportunityOut]) -> str:
    if any(item.priority == "urgent" for item in items):
        return "urgent"
    if any(item.priority == "high" for item in items):
        return "high"
    if items:
        return "medium"
    return "low"


def _audience_channel(items: list[GrowthOpportunityOut]) -> GrowthChannel:
    whatsapp_count = sum(1 for item in items if item.channel == "whatsapp")
    return "whatsapp" if whatsapp_count >= max(1, len(items) // 2) else "task"


def _lead_tags(lead: Lead, capture: dict[str, Any] | None, qualification: dict[str, Any] | None) -> list[str]:
    tags = ["crm", lead.stage.value]
    for value in (lead.source, capture.get("channel") if capture else None, capture.get("campaign") if capture else None):
        text = _string_value(value)
        if text:
            tags.append(text)
    label = _string_value(qualification.get("label") if qualification else None)
    if label:
        tags.append(label)
    return tags


def _lead_hot_message(lead: Lead, capture: dict[str, Any] | None) -> str:
    goal = _string_value(capture.get("desired_goal") if capture else None)
    if goal:
        return f"Ola {lead.full_name}, vi seu objetivo de {goal}. Vamos confirmar o melhor horario para sua aula experimental e montar seu plano de inicio?"
    return f"Ola {lead.full_name}, vamos confirmar sua aula experimental e organizar seu primeiro passo aqui na academia?"


def _lead_stale_message(lead: Lead, stale_days: int) -> str:
    day_text = "alguns dias" if stale_days >= 999 else f"{stale_days} dias"
    return f"Ola {lead.full_name}, passamos por aqui porque ficou pendente seu retorno ha {day_text}. Quer que eu te ajude a escolher o melhor horario para visitar a academia?"


def _member_reactivation_message(member: Member, days_inactive: int) -> str:
    return f"Ola {member.full_name}, sentimos sua falta nos treinos nos ultimos {days_inactive} dias. Quer que a gente ajuste um horario ou treino para voce voltar esta semana?"


def _member_renewal_message(member: Member) -> str:
    return f"Ola {member.full_name}, queria revisar como esta sua evolucao e ajustar o plano para voce continuar tendo resultado. Podemos combinar uma conversa rapida?"


def _member_nps_recovery_message(member: Member) -> str:
    return f"Ola {member.full_name}, vimos seu feedback e queremos entender melhor o que aconteceu para corrigir com voce. Pode falar com a gente hoje?"


def _member_promoter_message(member: Member) -> str:
    return f"Ola {member.full_name}, que bom ver sua constancia por aqui. Temos uma condicao/acao para alunos que estao evoluindo bem e tambem indicacoes. Posso te explicar rapidinho?"


def _build_operator_note(opportunity: GrowthOpportunityOut, operator_note: str | None) -> str:
    parts = [
        f"Growth OS: {opportunity.action_label}.",
        f"Motivo: {opportunity.reason}",
        f"Mensagem sugerida: {opportunity.suggested_message}",
    ]
    if operator_note and operator_note.strip():
        parts.append(f"Observacao do operador: {operator_note.strip()}")
    return "\n".join(parts)


def _build_whatsapp_url(contact: str | None, message: str) -> str | None:
    if not contact:
        return None
    digits = "".join(char for char in contact if char.isdigit())
    if not digits:
        return None
    if not digits.startswith("55"):
        digits = f"55{digits}"
    return f"https://wa.me/{digits}?text={quote(message)}"
