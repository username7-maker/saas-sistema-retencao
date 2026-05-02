from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    AutomationJourney,
    AutomationJourneyEnrollment,
    AutomationJourneyEvent,
    AutomationJourneyStep,
    Lead,
    LeadStage,
    Member,
    MemberStatus,
    RoleEnum,
    Task,
    TaskPriority,
    TaskStatus,
    User,
)
from app.schemas.automation_journey import (
    AutomationJourneyActivationOut,
    AutomationJourneyEnrollmentOut,
    AutomationJourneyOut,
    AutomationJourneyPreviewOut,
    AutomationJourneyPreviewSampleOut,
    AutomationJourneyStepTemplateOut,
    AutomationJourneyTemplateOut,
)

ACTIVE_ENROLLMENT_STATES = {"active"}
WAITING_ENROLLMENT_STATES = {"awaiting_outcome"}
POSITIVE_OUTCOMES = {"responded", "scheduled_assessment", "will_return", "payment_confirmed", "completed"}
NEGATIVE_OUTCOMES = {"not_interested", "invalid_number"}
NEUTRAL_OUTCOMES = {"no_response", "postponed", "forwarded_to_trainer", "forwarded_to_reception", "forwarded_to_manager", "payment_promised", "payment_link_sent", "charge_disputed"}


@dataclass(frozen=True)
class JourneyStepTemplate:
    name: str
    delay_days: int
    action_type: str
    channel: str | None
    owner_role: str | None
    severity: str
    message: str
    delay_hours: int = 0


@dataclass(frozen=True)
class JourneyTemplate:
    id: str
    name: str
    description: str
    domain: str
    entry_trigger: str
    steps: tuple[JourneyStepTemplate, ...]
    requires_human_approval: bool = True
    audience_config: dict[str, Any] | None = None
    exit_conditions: dict[str, Any] | None = None
    metrics_config: dict[str, Any] | None = None


TEMPLATES: tuple[JourneyTemplate, ...] = (
    JourneyTemplate(
        id="onboarding_d0_d30",
        name="Onboarding D0-D30",
        description="Boas-vindas, primeira avaliacao, feedback D14 e fechamento D30 para novos alunos.",
        domain="onboarding",
        entry_trigger="member_joined_30d",
        steps=(
            JourneyStepTemplate("Boas-vindas e combinados iniciais", 0, "create_task", "whatsapp", "reception", "medium", "Oi {nome}, bem-vindo(a)! Vamos combinar sua primeira semana e tirar qualquer duvida."),
            JourneyStepTemplate("Primeira avaliacao", 3, "create_task", "in_person", "coach", "high", "Agendar primeira avaliacao para alinhar objetivo, treino e frequencia."),
            JourneyStepTemplate("Feedback do treino D14", 14, "create_task", "whatsapp", "coach", "medium", "Oi {nome}, como foi a adaptacao aos treinos? Queremos ajustar qualquer ponto agora."),
            JourneyStepTemplate("Fechamento de onboarding D30", 30, "create_task", "whatsapp", "reception", "medium", "Oi {nome}, fechamos seu primeiro mes. Como esta sua rotina e frequencia?"),
        ),
        metrics_config={"north_star": "onboarding_completed_with_checkins"},
    ),
    JourneyTemplate(
        id="retention_absence",
        name="Retencao por ausencia",
        description="Acompanha alunos que reduzem check-ins, com severidade crescente.",
        domain="retention",
        entry_trigger="absence_checkins",
        steps=(
            JourneyStepTemplate("Ausencia 3+ dias", 0, "create_task", "whatsapp", "reception", "medium", "Oi {nome}, sentimos sua falta por aqui. Consegue treinar hoje ou amanha?"),
            JourneyStepTemplate("Ausencia 7+ dias", 4, "create_task", "whatsapp", "reception", "high", "Oi {nome}, ja faz alguns dias que voce nao aparece. Posso te ajudar a encaixar um horario?"),
            JourneyStepTemplate("Ausencia 14+ dias", 11, "create_task", "call", "manager", "critical", "Contato ativo: entender motivo da ausencia e propor retorno assistido."),
            JourneyStepTemplate("Ausencia 21+ dias", 18, "create_task", "call", "manager", "critical", "Risco alto: revisar permanencia, travas e plano de recuperacao."),
        ),
        audience_config={"min_days_without_checkin": 7},
    ),
    JourneyTemplate(
        id="nps_detractor",
        name="NPS detrator",
        description="Transforma feedback ruim em contato rapido de recuperacao.",
        domain="nps",
        entry_trigger="nps_low",
        steps=(
            JourneyStepTemplate("Contato com detrator", 0, "create_task", "call", "manager", "critical", "Entrar em contato com {nome}, entender o motivo do NPS baixo e combinar recuperacao."),
            JourneyStepTemplate("Acompanhamento pos-contato", 3, "create_task", "whatsapp", "manager", "high", "Oi {nome}, passando para confirmar se o ponto combinado melhorou."),
        ),
        audience_config={"max_nps": 6},
    ),
    JourneyTemplate(
        id="renewal",
        name="Renovacao preventiva",
        description="Avisa gestao antes do vencimento de contrato/plano quando houver data disponivel.",
        domain="renewal",
        entry_trigger="contract_ending",
        steps=(
            JourneyStepTemplate("Renovacao em 30 dias", 0, "create_task", "whatsapp", "reception", "medium", "Oi {nome}, seu plano esta chegando perto do vencimento. Posso te mostrar as melhores opcoes de renovacao?"),
            JourneyStepTemplate("Follow-up de renovacao", 7, "create_task", "whatsapp", "reception", "high", "Oi {nome}, conseguiu avaliar sua renovacao? Posso te ajudar a manter sua rotina sem interrupcao."),
        ),
        audience_config={"requires_contract_end_date": True, "days_to_end": 30},
    ),
    JourneyTemplate(
        id="delinquency",
        name="Inadimplencia operacional",
        description="Reaproveita a regua financeira D+1/D+3/D+7/D+15/D+30 e acompanha outcomes.",
        domain="finance",
        entry_trigger="delinquency_task_open",
        steps=(
            JourneyStepTemplate("Regularizacao financeira", 0, "create_task", "whatsapp", "reception", "high", "Oi {nome}, identifiquei uma pendencia no seu plano. Posso te ajudar a regularizar?"),
            JourneyStepTemplate("Escalar pendencia financeira", 7, "create_task", "call", "manager", "critical", "Pendencia financeira sem resolucao. Revisar caso e proxima acao com gerente."),
        ),
    ),
    JourneyTemplate(
        id="commercial",
        name="Comercial - lead parado",
        description="Organiza follow-ups de lead novo, parado, aula experimental e proposta sem resposta.",
        domain="commercial",
        entry_trigger="lead_stale",
        steps=(
            JourneyStepTemplate("Primeiro contato comercial", 0, "create_task", "whatsapp", "sales", "high", "Oi {nome}, vi seu interesse na academia. Quer marcar uma visita ou aula experimental?"),
            JourneyStepTemplate("Follow-up comercial", 2, "create_task", "whatsapp", "sales", "medium", "Oi {nome}, passando para te ajudar com sua escolha. Posso tirar alguma duvida?"),
            JourneyStepTemplate("No-show ou proposta sem resposta", 5, "create_task", "call", "sales", "high", "Recuperar lead parado e atualizar etapa no CRM."),
        ),
    ),
    JourneyTemplate(
        id="promoters_upsell",
        name="Promotores e upsell",
        description="Ativa alunos satisfeitos para indicacao, upgrade ou plano com maior valor.",
        domain="upsell",
        entry_trigger="promoter_signal",
        steps=(
            JourneyStepTemplate("Pedido de indicacao", 0, "create_task", "whatsapp", "reception", "medium", "Oi {nome}, que bom ver sua constancia. Se conhecer alguem que quer treinar, posso liberar uma experiencia."),
            JourneyStepTemplate("Upgrade assistido", 7, "create_task", "whatsapp", "manager", "medium", "Avaliar se {nome} tem perfil para upgrade de plano ou acompanhamento mais completo."),
        ),
        audience_config={"min_nps": 9},
    ),
)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _template_by_id(template_id: str) -> JourneyTemplate:
    for template in TEMPLATES:
        if template.id == template_id:
            return template
    raise ValueError("Template de jornada nao encontrado")


def _template_to_out(template: JourneyTemplate) -> AutomationJourneyTemplateOut:
    return AutomationJourneyTemplateOut(
        id=template.id,
        name=template.name,
        description=template.description,
        domain=template.domain,
        entry_trigger=template.entry_trigger,
        requires_human_approval=template.requires_human_approval,
        steps=[
            AutomationJourneyStepTemplateOut(
                name=step.name,
                delay_days=step.delay_days,
                delay_hours=step.delay_hours,
                action_type=step.action_type,
                channel=step.channel,
                owner_role=step.owner_role,
                severity=step.severity,
                message=step.message,
            )
            for step in template.steps
        ],
    )


def list_journey_templates() -> list[AutomationJourneyTemplateOut]:
    return [_template_to_out(template) for template in TEMPLATES]


def _event(
    db: Session,
    *,
    journey: AutomationJourney,
    event_type: str,
    enrollment: AutomationJourneyEnrollment | None = None,
    step: AutomationJourneyStep | None = None,
    task: Task | None = None,
    user: User | None = None,
    outcome: str | None = None,
    note: str | None = None,
    metadata: dict | None = None,
) -> AutomationJourneyEvent:
    item = AutomationJourneyEvent(
        gym_id=journey.gym_id,
        journey_id=journey.id,
        enrollment_id=enrollment.id if enrollment else None,
        step_id=step.id if step else None,
        task_id=task.id if task else None,
        member_id=(enrollment.member_id if enrollment else None) or (task.member_id if task else None),
        lead_id=(enrollment.lead_id if enrollment else None) or (task.lead_id if task else None),
        user_id=user.id if user else None,
        event_type=event_type,
        outcome=outcome,
        note=note,
        metadata_json=metadata or {},
        created_at=_now(),
    )
    db.add(item)
    return item


def _serialize_journey(db: Session, journey: AutomationJourney) -> AutomationJourneyOut:
    enrollment_rows = list(
        db.scalars(
            select(AutomationJourneyEnrollment).where(
                AutomationJourneyEnrollment.gym_id == journey.gym_id,
                AutomationJourneyEnrollment.journey_id == journey.id,
            )
        ).all()
    )
    event_rows = list(
        db.scalars(
            select(AutomationJourneyEvent).where(
                AutomationJourneyEvent.gym_id == journey.gym_id,
                AutomationJourneyEvent.journey_id == journey.id,
            )
        ).all()
    )
    steps = sorted(list(journey.steps or []), key=lambda step: step.step_order)
    return AutomationJourneyOut(
        id=journey.id,
        name=journey.name,
        description=journey.description,
        domain=journey.domain,
        entry_trigger=journey.entry_trigger,
        audience_config=journey.audience_config or {},
        exit_conditions=journey.exit_conditions or {},
        metrics_config=journey.metrics_config or {},
        is_active=journey.is_active,
        requires_human_approval=journey.requires_human_approval,
        steps=steps,  # type: ignore[arg-type]
        enrollments_total=len(enrollment_rows),
        active_enrollments_total=sum(1 for row in enrollment_rows if row.state == "active"),
        awaiting_outcome_total=sum(1 for row in enrollment_rows if row.state == "awaiting_outcome"),
        tasks_created_total=sum(1 for row in event_rows if row.event_type == "task_created"),
        positive_outcomes_total=sum(1 for row in event_rows if row.outcome in POSITIVE_OUTCOMES),
        neutral_outcomes_total=sum(1 for row in event_rows if row.outcome in NEUTRAL_OUTCOMES),
        negative_outcomes_total=sum(1 for row in event_rows if row.outcome in NEGATIVE_OUTCOMES),
        created_at=journey.created_at,
        updated_at=journey.updated_at,
    )


def list_journeys(db: Session, *, gym_id: UUID) -> list[AutomationJourneyOut]:
    journeys = list(
        db.scalars(
            select(AutomationJourney)
            .options(selectinload(AutomationJourney.steps))
            .where(AutomationJourney.gym_id == gym_id)
            .order_by(AutomationJourney.created_at.desc())
        ).all()
    )
    return [_serialize_journey(db, journey) for journey in journeys]


def get_journey_or_none(db: Session, *, journey_id: UUID, gym_id: UUID) -> AutomationJourney | None:
    return db.scalar(
        select(AutomationJourney)
        .options(selectinload(AutomationJourney.steps))
        .where(AutomationJourney.id == journey_id, AutomationJourney.gym_id == gym_id)
    )


def _eligible_members(db: Session, *, gym_id: UUID, template: JourneyTemplate, limit: int | None = None) -> list[Member]:
    filters = [Member.gym_id == gym_id, Member.deleted_at.is_(None), Member.status == MemberStatus.ACTIVE]
    now = _now()
    if template.id == "onboarding_d0_d30":
        filters.append(Member.join_date >= date.today() - timedelta(days=30))
    elif template.id == "retention_absence":
        min_days = int((template.audience_config or {}).get("min_days_without_checkin") or 7)
        cutoff = now - timedelta(days=min_days)
        filters.append(or_(Member.last_checkin_at.is_(None), Member.last_checkin_at <= cutoff))
    elif template.id == "nps_detractor":
        filters.append(Member.nps_last_score <= 6)
    elif template.id == "renewal":
        # V1 only enrolls when a contract end date exists in imported metadata.
        filters.append(Member.extra_data["contract_end_date"].astext.isnot(None))
    elif template.id == "promoters_upsell":
        filters.append(Member.nps_last_score >= 9)
    elif template.id == "delinquency":
        task_member_ids = select(Task.member_id).where(
            Task.gym_id == gym_id,
            Task.member_id.is_not(None),
            Task.deleted_at.is_(None),
            Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
            or_(Task.extra_data["source"].astext == "delinquency", Task.extra_data["domain"].astext == "finance"),
        )
        filters.append(Member.id.in_(task_member_ids))
    else:
        return []

    stmt = select(Member).where(*filters).order_by(Member.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def _eligible_leads(db: Session, *, gym_id: UUID, template: JourneyTemplate, limit: int | None = None) -> list[Lead]:
    if template.id != "commercial":
        return []
    stmt = (
        select(Lead)
        .where(
            Lead.gym_id == gym_id,
            Lead.deleted_at.is_(None),
            Lead.stage.notin_([LeadStage.WON, LeadStage.LOST]),
        )
        .order_by(Lead.last_contact_at.asc().nullsfirst(), Lead.created_at.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def preview_journey(
    db: Session,
    *,
    gym_id: UUID,
    template_id: str | None = None,
    journey: AutomationJourney | None = None,
) -> AutomationJourneyPreviewOut:
    template = _template_by_id(template_id or str((journey.audience_config or {}).get("template_id") or ""))
    members = _eligible_members(db, gym_id=gym_id, template=template, limit=10)
    leads = _eligible_leads(db, gym_id=gym_id, template=template, limit=10)
    full_member_count = len(_eligible_members(db, gym_id=gym_id, template=template))
    full_lead_count = len(_eligible_leads(db, gym_id=gym_id, template=template))
    warnings: list[str] = []
    if template.id == "renewal":
        warnings.append("Renovacao depende de contract_end_date em extra_data; sem isso, a jornada fica sem publico.")
    if template.id == "delinquency":
        warnings.append("Inadimplencia usa tasks financeiras abertas geradas pela regua 04.43.5.")
    sample: list[AutomationJourneyPreviewSampleOut] = [
        AutomationJourneyPreviewSampleOut(
            id=member.id,
            kind="member",
            name=member.full_name,
            preferred_shift=member.preferred_shift,
            reason=member.risk_level.value if hasattr(member.risk_level, "value") else str(member.risk_level),
        )
        for member in members
    ]
    sample.extend(
        AutomationJourneyPreviewSampleOut(
            id=lead.id,
            kind="lead",
            name=lead.full_name,
            preferred_shift=None,
            reason=lead.stage.value if hasattr(lead.stage, "value") else str(lead.stage),
        )
        for lead in leads
    )
    return AutomationJourneyPreviewOut(
        template_id=template.id,
        journey_id=journey.id if journey else None,
        eligible_count=full_member_count + full_lead_count,
        sample=sample[:10],
        warnings=warnings,
    )


def create_journey_from_template(db: Session, *, gym_id: UUID, template_id: str, current_user: User) -> AutomationJourneyOut:
    template = _template_by_id(template_id)
    existing = db.scalar(
        select(AutomationJourney).where(
            AutomationJourney.gym_id == gym_id,
            AutomationJourney.audience_config["template_id"].astext == template.id,
        )
    )
    if existing:
        return _serialize_journey(db, existing)

    journey = AutomationJourney(
        gym_id=gym_id,
        name=template.name,
        description=template.description,
        domain=template.domain,
        entry_trigger=template.entry_trigger,
        audience_config={"template_id": template.id, **(template.audience_config or {})},
        exit_conditions=template.exit_conditions or {},
        metrics_config=template.metrics_config or {},
        is_active=False,
        requires_human_approval=template.requires_human_approval,
    )
    db.add(journey)
    db.flush()
    for index, step_template in enumerate(template.steps, start=1):
        step = AutomationJourneyStep(
            gym_id=gym_id,
            journey_id=journey.id,
            step_order=index,
            name=step_template.name,
            delay_days=step_template.delay_days,
            delay_hours=step_template.delay_hours,
            condition_config={},
            action_type=step_template.action_type,
            action_config={"message": step_template.message, "primary_action_label": step_template.name},
            channel=step_template.channel,
            owner_role=step_template.owner_role,
            preferred_shift=None,
            template_key=template.id,
            fallback_mode="manual_required",
            severity=step_template.severity,
        )
        db.add(step)
    _event(db, journey=journey, event_type="journey_created", user=current_user, metadata={"template_id": template.id})
    db.flush()
    db.refresh(journey)
    return _serialize_journey(db, journey)


def update_journey(db: Session, *, journey: AutomationJourney, data: dict[str, Any], current_user: User) -> AutomationJourneyOut:
    for field in ("name", "description", "audience_config", "exit_conditions", "metrics_config", "requires_human_approval"):
        if field in data and data[field] is not None:
            setattr(journey, field, data[field])
    _event(db, journey=journey, event_type="journey_updated", user=current_user, metadata={"updated_fields": list(data.keys())})
    db.add(journey)
    db.flush()
    return _serialize_journey(db, journey)


def _first_step(journey: AutomationJourney) -> AutomationJourneyStep | None:
    steps = sorted(list(journey.steps or []), key=lambda step: step.step_order)
    return steps[0] if steps else None


def _upsert_enrollment(
    db: Session,
    *,
    journey: AutomationJourney,
    first_step: AutomationJourneyStep,
    member: Member | None = None,
    lead: Lead | None = None,
) -> tuple[AutomationJourneyEnrollment, bool]:
    filters = [AutomationJourneyEnrollment.gym_id == journey.gym_id, AutomationJourneyEnrollment.journey_id == journey.id]
    if member:
        filters.append(AutomationJourneyEnrollment.member_id == member.id)
    if lead:
        filters.append(AutomationJourneyEnrollment.lead_id == lead.id)
    existing = db.scalar(select(AutomationJourneyEnrollment).where(*filters))
    if existing:
        return existing, False
    due_at = _now() + timedelta(days=first_step.delay_days, hours=first_step.delay_hours)
    enrollment = AutomationJourneyEnrollment(
        gym_id=journey.gym_id,
        journey_id=journey.id,
        member_id=member.id if member else None,
        lead_id=lead.id if lead else None,
        current_step_id=first_step.id,
        state="active",
        current_step_order=first_step.step_order,
        next_step_due_at=due_at,
        metadata_json={
            "subject_name": member.full_name if member else (lead.full_name if lead else None),
            "preferred_shift": member.preferred_shift if member else None,
        },
    )
    db.add(enrollment)
    return enrollment, True


def activate_journey(db: Session, *, journey: AutomationJourney, current_user: User) -> AutomationJourneyActivationOut:
    template_id = str((journey.audience_config or {}).get("template_id") or "")
    template = _template_by_id(template_id)
    first_step = _first_step(journey)
    if first_step is None:
        raise ValueError("Jornada sem etapas configuradas")
    members = _eligible_members(db, gym_id=journey.gym_id, template=template)
    leads = _eligible_leads(db, gym_id=journey.gym_id, template=template)
    enrolled_count = 0
    skipped_count = 0
    for member in members:
        enrollment, created = _upsert_enrollment(db, journey=journey, first_step=first_step, member=member)
        skipped_count += 0 if created else 1
        enrolled_count += 1 if created else 0
        if created:
            _event(db, journey=journey, enrollment=enrollment, step=first_step, event_type="enrolled", user=current_user)
    for lead in leads:
        enrollment, created = _upsert_enrollment(db, journey=journey, first_step=first_step, lead=lead)
        skipped_count += 0 if created else 1
        enrolled_count += 1 if created else 0
        if created:
            _event(db, journey=journey, enrollment=enrollment, step=first_step, event_type="enrolled", user=current_user)
    journey.is_active = True
    _event(
        db,
        journey=journey,
        event_type="journey_activated",
        user=current_user,
        metadata={"enrolled_count": enrolled_count, "skipped_existing_count": skipped_count},
    )
    db.add(journey)
    db.flush()
    return AutomationJourneyActivationOut(
        journey=_serialize_journey(db, journey),
        enrolled_count=enrolled_count,
        skipped_existing_count=skipped_count,
    )


def pause_journey(db: Session, *, journey: AutomationJourney, current_user: User) -> AutomationJourneyOut:
    journey.is_active = False
    _event(db, journey=journey, event_type="journey_paused", user=current_user)
    db.add(journey)
    db.flush()
    return _serialize_journey(db, journey)


def list_enrollments(db: Session, *, journey: AutomationJourney, limit: int = 100) -> list[AutomationJourneyEnrollmentOut]:
    rows = list(
        db.scalars(
            select(AutomationJourneyEnrollment)
            .options(joinedload(AutomationJourneyEnrollment.member), joinedload(AutomationJourneyEnrollment.lead))
            .where(
                AutomationJourneyEnrollment.gym_id == journey.gym_id,
                AutomationJourneyEnrollment.journey_id == journey.id,
            )
            .order_by(AutomationJourneyEnrollment.updated_at.desc())
            .limit(limit)
        ).unique().all()
    )
    return [
        AutomationJourneyEnrollmentOut(
            id=row.id,
            journey_id=row.journey_id,
            member_id=row.member_id,
            lead_id=row.lead_id,
            subject_name=(row.member.full_name if row.member else None) or (row.lead.full_name if row.lead else None) or "Sem nome",
            state=row.state,
            current_step_order=row.current_step_order,
            next_step_due_at=row.next_step_due_at,
            last_executed_at=row.last_executed_at,
            exit_reason=row.exit_reason,
            metadata_json=row.metadata_json or {},
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def _render_message(template: str, *, member: Member | None, lead: Lead | None) -> str:
    name = (member.full_name if member else None) or (lead.full_name if lead else None) or "aluno"
    plan = member.plan_name if member else ""
    return template.replace("{nome}", name).replace("{plano}", plan)


def _task_priority(severity: str) -> TaskPriority:
    if severity == "critical":
        return TaskPriority.URGENT
    if severity == "high":
        return TaskPriority.HIGH
    if severity == "low":
        return TaskPriority.LOW
    return TaskPriority.MEDIUM


def _advance_step(journey: AutomationJourney, enrollment: AutomationJourneyEnrollment, completed_step: AutomationJourneyStep) -> None:
    steps = sorted(list(journey.steps or []), key=lambda step: step.step_order)
    next_step = next((step for step in steps if step.step_order > completed_step.step_order), None)
    if not next_step:
        enrollment.state = "completed"
        enrollment.exit_reason = "journey_completed"
        enrollment.next_step_due_at = None
        enrollment.current_step_id = completed_step.id
        return
    enrollment.state = "active"
    enrollment.current_step_id = next_step.id
    enrollment.current_step_order = next_step.step_order
    enrollment.next_step_due_at = _now() + timedelta(days=next_step.delay_days, hours=next_step.delay_hours)


def _find_existing_step_task(db: Session, *, enrollment: AutomationJourneyEnrollment, step: AutomationJourneyStep) -> Task | None:
    idempotency_key = f"journey:{enrollment.journey_id}:{enrollment.id}:step:{step.id}"
    return db.scalar(
        select(Task).where(
            Task.gym_id == enrollment.gym_id,
            Task.deleted_at.is_(None),
            Task.extra_data["automation_journey_id"].astext == str(enrollment.journey_id),
            Task.extra_data["automation_journey_enrollment_id"].astext == str(enrollment.id),
            Task.extra_data["automation_journey_step_id"].astext == str(step.id),
            Task.extra_data["idempotency_key"].astext == idempotency_key,
            Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
        )
    )


def process_automation_journeys_for_gym(db: Session, *, gym_id: UUID, commit: bool = True) -> dict[str, int]:
    now = _now()
    journeys = list(
        db.scalars(
            select(AutomationJourney)
            .options(selectinload(AutomationJourney.steps))
            .where(AutomationJourney.gym_id == gym_id, AutomationJourney.is_active.is_(True))
        ).all()
    )
    metrics = {"journeys": len(journeys), "enrollments_processed": 0, "tasks_created": 0, "tasks_reused": 0}
    for journey in journeys:
        enrollments = list(
            db.scalars(
                select(AutomationJourneyEnrollment)
                .options(
                    joinedload(AutomationJourneyEnrollment.member),
                    joinedload(AutomationJourneyEnrollment.lead),
                    joinedload(AutomationJourneyEnrollment.current_step),
                )
                .where(
                    AutomationJourneyEnrollment.gym_id == gym_id,
                    AutomationJourneyEnrollment.journey_id == journey.id,
                    AutomationJourneyEnrollment.state.in_(ACTIVE_ENROLLMENT_STATES),
                    AutomationJourneyEnrollment.next_step_due_at.is_not(None),
                    AutomationJourneyEnrollment.next_step_due_at <= now,
                )
                .limit(200)
            ).unique().all()
        )
        for enrollment in enrollments:
            step = enrollment.current_step
            if step is None:
                continue
            existing_task = _find_existing_step_task(db, enrollment=enrollment, step=step)
            if existing_task:
                enrollment.state = "awaiting_outcome"
                metrics["tasks_reused"] += 1
                db.add(enrollment)
                continue
            message = _render_message(str((step.action_config or {}).get("message") or ""), member=enrollment.member, lead=enrollment.lead)
            idempotency_key = f"journey:{journey.id}:{enrollment.id}:step:{step.id}"
            task = Task(
                gym_id=gym_id,
                member_id=enrollment.member_id,
                lead_id=enrollment.lead_id,
                title=step.name,
                description=f"Jornada {journey.name}: {step.name}",
                priority=_task_priority(step.severity),
                status=TaskStatus.TODO,
                kanban_column=TaskStatus.TODO.value,
                due_date=now,
                suggested_message=message or None,
                extra_data={
                    "source": "automation_journey",
                    "domain": journey.domain,
                    "automation_journey_id": str(journey.id),
                    "automation_journey_enrollment_id": str(enrollment.id),
                    "automation_journey_step_id": str(step.id),
                    "automation_journey_step_order": step.step_order,
                    "journey_name": journey.name,
                    "primary_action_label": step.name,
                    "primary_action_type": "prepare_outbound_message" if message else "open_context",
                    "channel": step.channel,
                    "owner_role": step.owner_role,
                    "fallback_mode": step.fallback_mode,
                    "severity": step.severity,
                    "idempotency_key": idempotency_key,
                },
            )
            db.add(task)
            db.flush()
            enrollment.state = "awaiting_outcome"
            enrollment.last_executed_at = now
            enrollment.metadata_json = {
                **(enrollment.metadata_json or {}),
                "prepared_task_id": str(task.id),
                "last_step_name": step.name,
            }
            _event(db, journey=journey, enrollment=enrollment, step=step, task=task, event_type="task_created")
            db.add(enrollment)
            metrics["tasks_created"] += 1
            metrics["enrollments_processed"] += 1
    if commit:
        db.commit()
    else:
        db.flush()
    return metrics


def handle_task_outcome_for_journey(
    db: Session,
    *,
    task: Task,
    outcome: str,
    current_user: User | None = None,
    note: str | None = None,
) -> None:
    extra = task.extra_data or {}
    enrollment_id = extra.get("automation_journey_enrollment_id")
    journey_id = extra.get("automation_journey_id")
    step_id = extra.get("automation_journey_step_id")
    if not enrollment_id or not journey_id:
        return

    enrollment = db.scalar(
        select(AutomationJourneyEnrollment)
        .options(
            joinedload(AutomationJourneyEnrollment.journey).selectinload(AutomationJourney.steps),
            joinedload(AutomationJourneyEnrollment.current_step),
        )
        .where(
            AutomationJourneyEnrollment.id == UUID(str(enrollment_id)),
            AutomationJourneyEnrollment.gym_id == task.gym_id,
        )
    )
    if enrollment is None or enrollment.journey is None:
        return
    step = enrollment.current_step
    if step is None and step_id:
        step = db.get(AutomationJourneyStep, UUID(str(step_id)))
    _event(
        db,
        journey=enrollment.journey,
        enrollment=enrollment,
        step=step,
        task=task,
        user=current_user,
        event_type="outcome_recorded",
        outcome=outcome,
        note=note,
        metadata={"source": "work_queue"},
    )
    if outcome in POSITIVE_OUTCOMES:
        if step is not None:
            _advance_step(enrollment.journey, enrollment, step)
    elif outcome in NEGATIVE_OUTCOMES:
        enrollment.state = "exited"
        enrollment.exit_reason = outcome
        enrollment.next_step_due_at = None
    else:
        enrollment.state = "active"
        enrollment.next_step_due_at = task.due_date or (_now() + timedelta(days=2))
    db.add(enrollment)


def journey_summary_for_job(result: dict[str, int]) -> dict[str, int]:
    return {key: int(value) for key, value in result.items()}
