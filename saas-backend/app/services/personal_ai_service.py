from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment,
    AutopilotAction,
    BodyCompositionEvaluation,
    Checkin,
    Member,
    MemberConstraints,
    MemberGoal,
    MessageLog,
    Task,
    TrainingPlan,
)
from app.models.enums import MemberStatus
from app.schemas.personal_ai import (
    PersonalAiContextOut,
    PersonalAiDraftCreate,
    PersonalAiDraftOut,
    PersonalAiPrepareResultOut,
    PersonalAiSettingsOut,
    PersonalAiSettingsUpdate,
)
from app.services.autopilot_event_service import record_event
from app.services.autopilot_settings_service import get_or_create_autopilot_settings
from app.services.ai_prompt_registry_service import AiPromptResult, generate_specialist_text
from app.services.kommo_service import handoff_member_to_kommo

PERSONAL_AI_EXTRA_KEY = "personal_ai"
PERSONAL_AI_ACTION_TYPE = "personal_ai_guidance_draft"
PERSONAL_AI_DRAFT_READY = "draft_ready"

DEFAULT_PERSONAL_AI_SETTINGS = {
    "enabled": False,
    "mode": "coach_review",
    "auto_send_enabled": False,
    "sensitive_escalation_enabled": True,
    "kommo_prepare_enabled": True,
    "max_drafts_per_day": 50,
    "allowed_domains": [
        "training_guidance",
        "routine_support",
        "assessment_explanation",
        "body_composition_explanation",
    ],
}

PAIN_TERMS = ("dor", "dor forte", "lesao", "lesão", "machuquei", "emergencia", "emergência", "lesionado")
MEDICAL_TERMS = ("remedio", "remédio", "medicamento", "diagnostico", "diagnóstico", "pressao", "pressão", "cardiaco", "cardíaco")
NUTRITION_TERMS = ("dieta", "caloria", "suplemento", "whey", "creatina", "medicacao", "medicação", "nutricional")
CANCEL_TERMS = ("cancelar", "cancelamento", "trancar", "trancamento", "reclamacao", "reclamação", "advogado")
PRESCRIPTION_TERMS = ("monte um treino", "montar treino", "prescreva", "prescricao", "prescrição", "novo treino", "trocar treino")


@dataclass(frozen=True)
class PersonalAiClassification:
    intent: str
    sensitivity: str
    summary: str
    next_action: str
    recommended_owner_role: str
    blocked_reasons: list[str]
    evidence: list[str]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def get_personal_ai_settings(db: Session, *, gym_id: UUID) -> PersonalAiSettingsOut:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    payload = _merge_settings((settings.extra_data or {}).get(PERSONAL_AI_EXTRA_KEY))
    return PersonalAiSettingsOut(**payload)


def update_personal_ai_settings(
    db: Session,
    *,
    gym_id: UUID,
    payload: PersonalAiSettingsUpdate,
) -> PersonalAiSettingsOut:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    current = _merge_settings((settings.extra_data or {}).get(PERSONAL_AI_EXTRA_KEY))
    updates = payload.model_dump(exclude_unset=True)
    updates["auto_send_enabled"] = False
    updates["mode"] = "coach_review"
    current.update(updates)
    current = _merge_settings(current)

    extra = dict(settings.extra_data or {})
    extra[PERSONAL_AI_EXTRA_KEY] = current
    settings.extra_data = extra
    db.add(settings)
    db.flush()
    return PersonalAiSettingsOut(**current)


def build_personal_ai_context(db: Session, *, gym_id: UUID, member_id: UUID) -> PersonalAiContextOut:
    member = _get_member_or_404(db, gym_id=gym_id, member_id=member_id)
    latest_assessment = _latest_assessment(db, gym_id=gym_id, member_id=member_id)
    latest_body_composition = _latest_body_composition(db, gym_id=gym_id, member_id=member_id)
    active_plan = _active_training_plan(db, gym_id=gym_id, member_id=member_id)
    goals = _active_goals(db, gym_id=gym_id, member_id=member_id)
    constraints = db.scalar(
        select(MemberConstraints).where(
            MemberConstraints.gym_id == gym_id,
            MemberConstraints.member_id == member_id,
            MemberConstraints.deleted_at.is_(None),
        )
    )
    checkins_30d = _checkins_30d(db, gym_id=gym_id, member_id=member_id)
    recent_tasks = _recent_technical_tasks(db, gym_id=gym_id, member_id=member_id)

    evidence: list[str] = []
    missing_data: list[str] = []
    if latest_assessment:
        evidence.append("formal_assessment")
    else:
        missing_data.append("formal_assessment")
    if latest_body_composition:
        evidence.append("body_composition")
    else:
        missing_data.append("body_composition")
    if active_plan:
        evidence.append("active_training_plan")
    else:
        missing_data.append("active_training_plan")
    if goals:
        evidence.append("active_goals")
    else:
        missing_data.append("active_goals")
    if constraints:
        evidence.append("constraints_checked")
    if checkins_30d:
        evidence.append("checkins_30d")

    return PersonalAiContextOut(
        member_id=member.id,
        member_name=member.full_name,
        preferred_shift=member.preferred_shift,
        lifecycle_stage=getattr(member, "lifecycle_stage", None),
        risk_level=_enum_value(getattr(member, "risk_level", None)),
        risk_score=member.risk_score,
        latest_assessment=_assessment_snapshot(latest_assessment),
        latest_body_composition=_body_composition_snapshot(latest_body_composition),
        active_training_plan=_training_plan_snapshot(active_plan),
        active_goals=[_goal_snapshot(goal) for goal in goals],
        constraints=_constraints_snapshot(constraints),
        checkins_30d=checkins_30d,
        recent_technical_tasks=recent_tasks,
        evidence=evidence,
        missing_data=missing_data,
    )


def create_personal_ai_draft(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    payload: PersonalAiDraftCreate,
    created_by_user_id: UUID | None = None,
    flush: bool = True,
) -> PersonalAiDraftOut:
    settings = get_personal_ai_settings(db, gym_id=gym_id)
    context = build_personal_ai_context(db, gym_id=gym_id, member_id=member_id)
    member = _get_member_or_404(db, gym_id=gym_id, member_id=member_id)
    classification = classify_personal_ai_request(payload.question, requested_domain=payload.domain)
    blocked_reasons = list(classification.blocked_reasons)

    if not settings.enabled:
        blocked_reasons.append("personal_ai_disabled")
    if payload.domain and payload.domain not in settings.allowed_domains:
        blocked_reasons.append("domain_disabled")
    if _drafts_created_today(db, gym_id=gym_id) >= settings.max_drafts_per_day:
        blocked_reasons.append("daily_draft_limit_reached")
    if member.status != MemberStatus.ACTIVE and _requires_active_member_for_personal_ai(classification.intent):
        blocked_reasons.append("member_not_active")
    if classification.intent in {"training_guidance", "routine_support"} and not context.active_training_plan:
        blocked_reasons.append("missing_active_training_plan")
    if classification.intent in {"training_guidance", "assessment_explanation", "body_composition_explanation"} and (
        not context.latest_assessment and not context.latest_body_composition
    ):
        blocked_reasons.append("missing_technical_baseline")

    status_value = "escalated" if classification.sensitivity == "sensitive" else PERSONAL_AI_DRAFT_READY
    if blocked_reasons:
        status_value = "blocked" if classification.sensitivity != "sensitive" else "escalated"

    reply_result = None if blocked_reasons else _build_personal_ai_reply_result(member=member, context=context, intent=classification.intent)
    draft_reply = reply_result.text if reply_result else None
    context_payload = context.model_dump(mode="json")
    metadata = {
        "personal_ai_state": status_value,
        "intent": classification.intent,
        "sensitivity": classification.sensitivity,
        "summary": classification.summary,
        "draft_reply": draft_reply,
        "prompt_metadata": reply_result.metadata if reply_result else None,
        "next_action": classification.next_action,
        "recommended_owner_role": classification.recommended_owner_role,
        "blocked_reasons": blocked_reasons,
        "evidence": sorted(set([*classification.evidence, *context.evidence])),
        "question": payload.question,
        "context_snapshot": context_payload,
        "created_by_user_id": str(created_by_user_id) if created_by_user_id else None,
        "auto_send_enabled": False,
        "mode": "coach_review",
    }
    action = AutopilotAction(
        gym_id=gym_id,
        policy_key=f"personal_ai_{classification.intent}",
        domain="trainer",
        action_type=PERSONAL_AI_ACTION_TYPE,
        status=status_value,
        member_id=member_id,
        lead_id=None,
        channel=payload.channel,
        template_key=f"personal_ai_{classification.intent}",
        message_body=draft_reply,
        timeout_at=_now() + timedelta(hours=48),
        max_attempts=1,
        failure_reason=",".join(blocked_reasons) if blocked_reasons else None,
        escalation_reason=classification.summary if status_value == "escalated" else None,
        metadata_json=metadata,
    )
    db.add(action)
    db.flush()

    record_event(
        db,
        gym_id=gym_id,
        event_type="personal_ai_draft_created" if status_value == PERSONAL_AI_DRAFT_READY else "human_intervention_required",
        source="personal_ai",
        member_id=member_id,
        autopilot_action_id=action.id,
        metadata={
            "intent": classification.intent,
            "status": status_value,
            "blocked_reasons": blocked_reasons,
            "evidence": metadata["evidence"],
        },
        flush=False,
    )
    if flush:
        db.flush()
    return serialize_personal_ai_draft(action)


def list_personal_ai_drafts(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID | None = None,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[PersonalAiDraftOut]:
    query = select(AutopilotAction).where(
        AutopilotAction.gym_id == gym_id,
        AutopilotAction.action_type == PERSONAL_AI_ACTION_TYPE,
    )
    if member_id:
        query = query.where(AutopilotAction.member_id == member_id)
    if status_filter:
        query = query.where(AutopilotAction.status == status_filter)
    actions = db.scalars(query.order_by(AutopilotAction.created_at.desc()).limit(limit)).all()
    return [serialize_personal_ai_draft(action) for action in actions]


def prepare_personal_ai_draft_in_kommo(
    db: Session,
    *,
    gym_id: UUID,
    draft_id: UUID,
    flush: bool = True,
) -> PersonalAiPrepareResultOut:
    settings = get_personal_ai_settings(db, gym_id=gym_id)
    if not settings.kommo_prepare_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Preparacao Kommo do Cordex Coach esta desativada.")
    action = db.scalar(
        select(AutopilotAction).where(
            AutopilotAction.gym_id == gym_id,
            AutopilotAction.id == draft_id,
            AutopilotAction.action_type == PERSONAL_AI_ACTION_TYPE,
        )
    )
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rascunho do Cordex Coach nao encontrado.")
    if action.status != PERSONAL_AI_DRAFT_READY:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este rascunho nao esta pronto para Kommo.")
    member = db.get(Member, action.member_id) if action.member_id else None
    if member is None or member.gym_id != gym_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno do rascunho nao encontrado.")

    metadata = dict(action.metadata_json or {})
    summary = "\n".join(
        [
            "Cordex Coach V1 - revisar orientacao tecnica antes de enviar.",
            f"Pergunta: {metadata.get('question') or '-'}",
            f"Resumo: {metadata.get('summary') or '-'}",
            f"Orientacao sugerida: {action.message_body or '-'}",
            f"Proxima acao: {metadata.get('next_action') or '-'}",
            f"Evidencias: {', '.join(metadata.get('evidence') or []) or '-'}",
        ]
    )
    result = handoff_member_to_kommo(
        db,
        gym_id=gym_id,
        member=member,
        title=f"Revisar orientacao Cordex Coach - {member.full_name}"[:120],
        summary=summary,
        source="personal_ai",
        due_in_hours=8,
    )
    if result.status != "sent":
        action.status = "failed"
        action.failure_reason = result.detail or result.status
        db.add(action)
        if flush:
            db.flush()
        return PersonalAiPrepareResultOut(draft=serialize_personal_ai_draft(action), detail=result.detail or result.status)

    metadata.update(
        {
            "kommo_contact_id": result.contact_id,
            "kommo_lead_id": result.lead_id,
            "kommo_task_id": result.task_id,
            "prepared_at": _now().isoformat(),
            "personal_ai_state": "waiting_coach_review",
        }
    )
    action.status = "awaiting_outcome"
    action.metadata_json = metadata
    db.add(action)
    record_event(
        db,
        gym_id=gym_id,
        event_type="personal_ai_draft_prepared_kommo",
        source="personal_ai",
        member_id=member.id,
        autopilot_action_id=action.id,
        metadata={
            "kommo_contact_id": result.contact_id,
            "kommo_lead_id": result.lead_id,
            "kommo_task_id": result.task_id,
        },
        flush=False,
    )
    db.add(
        MessageLog(
            gym_id=gym_id,
            member_id=member.id,
            lead_id=None,
            channel="kommo",
            recipient=(member.phone or member.email or str(member.id)),
            template_name=action.template_key,
            content=action.message_body or "",
            status="sent",
            direction="outbound",
            event_type="personal_ai_kommo_draft",
            provider_message_id=result.task_id,
            extra_data={
                "autopilot_action_id": str(action.id),
                "source": "personal_ai",
                "operator_review_required": True,
                "kommo_contact_id": result.contact_id,
                "kommo_lead_id": result.lead_id,
                "kommo_task_id": result.task_id,
            },
        )
    )
    if flush:
        db.flush()
    return PersonalAiPrepareResultOut(
        draft=serialize_personal_ai_draft(action),
        detail="Rascunho tecnico preparado na Kommo para revisao do professor.",
        kommo_contact_id=result.contact_id,
        kommo_lead_id=result.lead_id,
        kommo_task_id=result.task_id,
    )


def serialize_personal_ai_draft(action: AutopilotAction) -> PersonalAiDraftOut:
    metadata = dict(action.metadata_json or {})
    context_snapshot = metadata.get("context_snapshot")
    return PersonalAiDraftOut(
        id=action.id,
        status=action.status,
        gym_id=action.gym_id,
        member_id=action.member_id,
        intent=str(metadata.get("intent") or action.policy_key.replace("personal_ai_", "")),
        sensitivity=str(metadata.get("sensitivity") or "normal"),
        summary=str(metadata.get("summary") or action.policy_key),
        draft_reply=action.message_body or metadata.get("draft_reply"),
        next_action=str(metadata.get("next_action") or "Professor deve revisar a orientacao."),
        recommended_owner_role=str(metadata.get("recommended_owner_role") or "coach"),
        blocked_reasons=list(metadata.get("blocked_reasons") or []),
        evidence=list(metadata.get("evidence") or []),
        question=str(metadata.get("question") or ""),
        context_snapshot=PersonalAiContextOut(**context_snapshot) if isinstance(context_snapshot, dict) else None,
        prompt_metadata=metadata.get("prompt_metadata") if isinstance(metadata.get("prompt_metadata"), dict) else None,
        kommo_contact_id=metadata.get("kommo_contact_id"),
        kommo_lead_id=metadata.get("kommo_lead_id"),
        kommo_task_id=metadata.get("kommo_task_id"),
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


def classify_personal_ai_request(question: str, *, requested_domain: str | None = None) -> PersonalAiClassification:
    normalized = _normalize_text(question)
    sensitive = _matched_sensitive(normalized)
    if sensitive:
        intent, reason = sensitive
        return PersonalAiClassification(
            intent=intent,
            sensitivity="sensitive",
            summary=f"Solicitacao sensivel detectada: {intent}.",
            next_action="Escalar para professor/gestor antes de responder.",
            recommended_owner_role="coach" if intent in {"injury", "medical"} else "manager",
            blocked_reasons=[reason],
            evidence=["personal_ai_request", "sensitive_keyword"],
        )

    intent = requested_domain or "routine_support"
    if not requested_domain:
        if any(term in normalized for term in ("bioimpedancia", "bioimpedância", "gordura", "massa muscular", "imc")):
            intent = "body_composition_explanation"
        elif any(term in normalized for term in ("avaliacao", "avaliação", "evolucao", "evolução", "resultado")):
            intent = "assessment_explanation"
        elif any(term in normalized for term in ("treino", "exercicio", "exercício", "carga", "serie", "série")):
            intent = "training_guidance"

    blocked_reasons = []
    if any(term in normalized for term in PRESCRIPTION_TERMS):
        blocked_reasons.append("autonomous_prescription_not_allowed")

    return PersonalAiClassification(
        intent=intent,
        sensitivity="normal",
        summary=f"Solicitacao tecnica classificada como {intent}.",
        next_action="Professor revisa o rascunho antes de usar com o aluno.",
        recommended_owner_role="coach",
        blocked_reasons=blocked_reasons,
        evidence=["personal_ai_request", f"intent:{intent}", "coach_review"],
    )


def _requires_active_member_for_personal_ai(intent: str) -> bool:
    return intent in {"training_guidance", "routine_support"}


def _build_personal_ai_reply(*, member: Member, context: PersonalAiContextOut, intent: str) -> str:
    return _build_personal_ai_reply_result(member=member, context=context, intent=intent).text


def _build_personal_ai_reply_result(*, member: Member, context: PersonalAiContextOut, intent: str) -> AiPromptResult:
    first_name = ((member.full_name or "").split(" ")[0] or "aluno").strip()
    plan = context.active_training_plan or {}
    goal = (context.active_goals[0] if context.active_goals else {})
    latest_assessment = context.latest_assessment or {}
    latest_bio = context.latest_body_composition or {}
    sessions = plan.get("sessions_per_week")
    objective = plan.get("objective") or goal.get("title") or "manter consistencia"
    caution = "Se sentir dor, tontura ou desconforto forte, pare e chame o professor antes de continuar."

    if intent == "body_composition_explanation":
        fallback = (
            f"Oi, {first_name}! Pela sua bioimpedancia mais recente, o foco agora e acompanhar tendencia, "
            f"manter regularidade no treino e revisar o plano com o professor. "
            f"Peso: {latest_bio.get('weight_kg') or '-'} kg, gordura: {latest_bio.get('body_fat_percent') or '-'}%, "
            f"massa muscular: {latest_bio.get('skeletal_muscle_kg') or latest_bio.get('muscle_mass_kg') or '-'} kg. {caution}"
        )
    elif intent == "assessment_explanation":
        fallback = (
            f"Oi, {first_name}! Sua avaliacao mais recente serve como base para ajustar meta, frequencia e treino. "
            f"Peso: {latest_assessment.get('weight_kg') or '-'} kg, gordura: {latest_assessment.get('body_fat_pct') or '-'}%, "
            f"proxima reavaliacao: {latest_assessment.get('next_assessment_due') or 'a definir'}. {caution}"
        )
    elif intent == "training_guidance":
        fallback = (
            f"Oi, {first_name}! Pelo plano atual ({plan.get('name') or 'treino ativo'}), o foco e executar o que ja foi prescrito, "
            f"com frequencia alvo de {sessions or '-'}x por semana e objetivo: {objective}. "
            "Nao vou mudar exercicios por aqui; qualquer ajuste de carga, exercicio ou dor deve ser validado com o professor. "
            f"{caution}"
        )
    else:
        fallback = (
            f"Oi, {first_name}! Para evoluir com seguranca, o melhor agora e manter a rotina do treino atual "
            f"({sessions or '-'}x/semana), registrar feedback do que esta facil ou dificil e revisar com o professor no proximo contato. {caution}"
        )

    user_prompt = (
        "Prepare um rascunho tecnico curto para o professor revisar antes de usar.\n"
        f"Aluno: {member.full_name}\n"
        f"Intencao: {intent}\n"
        f"Plano ativo: {plan}\n"
        f"Meta principal: {objective}\n"
        f"Sessoes por semana: {sessions or '-'}\n"
        f"Avaliacao: {latest_assessment}\n"
        f"Bioimpedancia: {latest_bio}\n"
        f"Evidencias: {context.evidence}\n"
        f"Lacunas: {context.missing_data}\n"
        "A resposta deve ser segura, sem prescricao autonoma e pronta para revisao humana."
    )
    return generate_specialist_text(
        "personal_ai_coach_v1",
        user_prompt=user_prompt,
        fallback_text=fallback,
        max_output_chars=1200,
    )


def _merge_settings(raw: dict | None) -> dict:
    merged = {**DEFAULT_PERSONAL_AI_SETTINGS, **(raw or {})}
    merged["mode"] = "coach_review"
    merged["auto_send_enabled"] = False
    if not isinstance(merged.get("allowed_domains"), list):
        merged["allowed_domains"] = list(DEFAULT_PERSONAL_AI_SETTINGS["allowed_domains"])
    return merged


def _matched_sensitive(normalized: str) -> tuple[str, str] | None:
    if any(term in normalized for term in PAIN_TERMS):
        return ("injury", "sensitive_injury_or_pain")
    if any(term in normalized for term in MEDICAL_TERMS):
        return ("medical", "sensitive_medical")
    if any(term in normalized for term in NUTRITION_TERMS):
        return ("nutrition", "nutrition_or_supplement_not_allowed")
    if any(term in normalized for term in CANCEL_TERMS):
        return ("cancellation_or_complaint", "sensitive_cancellation_or_complaint")
    return None


def _get_member_or_404(db: Session, *, gym_id: UUID, member_id: UUID) -> Member:
    member = db.scalar(
        select(Member).where(Member.id == member_id, Member.gym_id == gym_id, Member.deleted_at.is_(None))
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno nao encontrado.")
    return member


def _latest_assessment(db: Session, *, gym_id: UUID, member_id: UUID) -> Assessment | None:
    return db.scalar(
        select(Assessment)
        .where(Assessment.gym_id == gym_id, Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
        .order_by(Assessment.assessment_date.desc())
        .limit(1)
    )


def _latest_body_composition(db: Session, *, gym_id: UUID, member_id: UUID) -> BodyCompositionEvaluation | None:
    return db.scalar(
        select(BodyCompositionEvaluation)
        .where(BodyCompositionEvaluation.gym_id == gym_id, BodyCompositionEvaluation.member_id == member_id)
        .order_by(BodyCompositionEvaluation.evaluation_date.desc(), BodyCompositionEvaluation.created_at.desc())
        .limit(1)
    )


def _active_training_plan(db: Session, *, gym_id: UUID, member_id: UUID) -> TrainingPlan | None:
    return db.scalar(
        select(TrainingPlan)
        .where(
            TrainingPlan.gym_id == gym_id,
            TrainingPlan.member_id == member_id,
            TrainingPlan.is_active.is_(True),
            TrainingPlan.deleted_at.is_(None),
        )
        .order_by(TrainingPlan.start_date.desc(), TrainingPlan.created_at.desc())
        .limit(1)
    )


def _active_goals(db: Session, *, gym_id: UUID, member_id: UUID) -> list[MemberGoal]:
    return list(
        db.scalars(
            select(MemberGoal)
            .where(
                MemberGoal.gym_id == gym_id,
                MemberGoal.member_id == member_id,
                MemberGoal.status == "active",
                MemberGoal.deleted_at.is_(None),
            )
            .order_by(MemberGoal.target_date.asc().nullslast(), MemberGoal.created_at.desc())
            .limit(5)
        ).all()
    )


def _checkins_30d(db: Session, *, gym_id: UUID, member_id: UUID) -> int:
    since = _now() - timedelta(days=30)
    value = db.scalar(
        select(func.count(Checkin.id)).where(
            Checkin.gym_id == gym_id,
            Checkin.member_id == member_id,
            Checkin.checkin_at >= since,
        )
    )
    return int(value or 0)


def _recent_technical_tasks(db: Session, *, gym_id: UUID, member_id: UUID) -> list[dict]:
    tasks = db.scalars(
        select(Task)
        .where(
            Task.gym_id == gym_id,
            Task.member_id == member_id,
            Task.deleted_at.is_(None),
            Task.extra_data["domain"].astext.in_(["trainer", "assessment"]),
        )
        .order_by(Task.created_at.desc())
        .limit(5)
    ).all()
    return [
        {
            "id": str(task.id),
            "title": task.title,
            "status": _enum_value(task.status),
            "due_date": _json_value(task.due_date),
            "source": (task.extra_data or {}).get("source"),
        }
        for task in tasks
    ]


def _drafts_created_today(db: Session, *, gym_id: UUID) -> int:
    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    value = db.scalar(
        select(func.count(AutopilotAction.id)).where(
            AutopilotAction.gym_id == gym_id,
            AutopilotAction.action_type == PERSONAL_AI_ACTION_TYPE,
            AutopilotAction.created_at >= today_start,
        )
    )
    return int(value or 0)


def _assessment_snapshot(assessment: Assessment | None) -> dict | None:
    if assessment is None:
        return None
    return {
        "id": str(assessment.id),
        "assessment_number": assessment.assessment_number,
        "assessment_date": _json_value(assessment.assessment_date),
        "next_assessment_due": _json_value(assessment.next_assessment_due),
        "weight_kg": _json_value(assessment.weight_kg),
        "body_fat_pct": _json_value(assessment.body_fat_pct),
        "lean_mass_kg": _json_value(assessment.lean_mass_kg),
        "observations": assessment.observations,
        "ai_recommendations": assessment.ai_recommendations,
    }


def _body_composition_snapshot(evaluation: BodyCompositionEvaluation | None) -> dict | None:
    if evaluation is None:
        return None
    return {
        "id": str(evaluation.id),
        "evaluation_date": _json_value(evaluation.evaluation_date),
        "weight_kg": _json_value(evaluation.weight_kg),
        "body_fat_percent": _json_value(evaluation.body_fat_percent),
        "skeletal_muscle_kg": _json_value(evaluation.skeletal_muscle_kg),
        "muscle_mass_kg": _json_value(evaluation.muscle_mass_kg),
        "health_score": evaluation.health_score,
        "training_ready": evaluation.training_ready,
        "ai_coach_summary": evaluation.ai_coach_summary,
        "ai_training_focus": evaluation.ai_training_focus_json,
    }


def _training_plan_snapshot(plan: TrainingPlan | None) -> dict | None:
    if plan is None:
        return None
    return {
        "id": str(plan.id),
        "name": plan.name,
        "objective": plan.objective,
        "sessions_per_week": plan.sessions_per_week,
        "split_type": plan.split_type,
        "start_date": _json_value(plan.start_date),
        "end_date": _json_value(plan.end_date),
        "notes": plan.notes,
    }


def _goal_snapshot(goal: MemberGoal) -> dict:
    return {
        "id": str(goal.id),
        "title": goal.title,
        "category": goal.category,
        "target_value": _json_value(goal.target_value),
        "current_value": _json_value(goal.current_value),
        "unit": goal.unit,
        "target_date": _json_value(goal.target_date),
        "progress_pct": goal.progress_pct,
    }


def _constraints_snapshot(constraints: MemberConstraints | None) -> dict | None:
    if constraints is None:
        return None
    return {
        "has_medical_conditions": bool(constraints.medical_conditions),
        "has_injuries": bool(constraints.injuries),
        "has_contraindications": bool(constraints.contraindications),
        "preferred_training_times": constraints.preferred_training_times,
        "restrictions": constraints.restrictions or {},
        "notes": constraints.notes,
    }


def _json_value(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _enum_value(value) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", str(value))


def _normalize_text(value: str) -> str:
    return (value or "").strip().lower()
