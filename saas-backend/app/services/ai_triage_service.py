from __future__ import annotations

from statistics import mean, median
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AITriageRecommendation,
    Assessment,
    AuditLog,
    Member,
    MemberStatus,
    RiskLevel,
    Task,
    TaskPriority,
    TaskStatus,
    User,
)
from app.schemas import (
    AITriageMetricsSummaryRead,
    AITriageRecommendationRead,
    AITriageRecommendedOwner,
    AITriageSafeActionPreparedRead,
    PaginatedResponse,
    RetentionQueueItem,
    TaskCreate,
)
from app.services.audit_service import log_audit_event
from app.services.dashboard_service import get_retention_queue
from app.services.task_service import create_task


ACTIVE_TRIAGE_DOMAINS = ("retention", "onboarding")
PREPARED_EXECUTION_STATES = {"prepared", "queued", "running", "completed"}
FINAL_OUTCOME_STATES = {"positive", "neutral", "negative"}


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _priority_bucket(priority_score: int) -> str:
    if priority_score >= 85:
        return "critical"
    if priority_score >= 65:
        return "high"
    if priority_score >= 40:
        return "medium"
    return "low"


def _owner_label(owner_role: str | None) -> str | None:
    if owner_role == "manager":
        return "Manager"
    if owner_role == "reception":
        return "Recepcao"
    if owner_role == "coach":
        return "Coach"
    return None


def _json_safe(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return [_json_safe(item) for item in sorted(value, key=str)]
    return value


def _recommended_owner_payload(user_id: UUID | None, role: str | None, label: str | None = None) -> dict:
    return {
        "user_id": user_id,
        "role": role,
        "label": label or _owner_label(role),
    }


def _retention_priority_score(item: RetentionQueueItem) -> int:
    score = int(item.risk_score or 0)
    if item.risk_level == RiskLevel.RED:
        score += 15
    if isinstance(item.days_without_checkin, int) and item.days_without_checkin >= 14:
        score += 10
    if item.last_contact_at is None:
        score += 5
    if isinstance(item.forecast_60d, int) and item.forecast_60d < 40:
        score += 5
    return max(0, min(100, score))


def _retention_expected_impact(item: RetentionQueueItem) -> str:
    if item.risk_level == RiskLevel.RED:
        return "Reduzir chance de cancelamento nas proximas 24-72 horas."
    return "Evitar escalada do risco e retomar frequencia antes da perda do habito."


def _retention_why_now_details(item: RetentionQueueItem) -> list[str]:
    details = [f"Risco atual: {item.risk_level.value} ({item.risk_score} pontos)."]
    if isinstance(item.days_without_checkin, int):
        details.append(f"{item.days_without_checkin} dias sem check-in.")
    if isinstance(item.nps_last_score, int) and item.nps_last_score > 0:
        details.append(f"NPS mais recente: {item.nps_last_score}.")
    if isinstance(item.forecast_60d, int):
        details.append(f"Forecast de retencao em 60 dias: {item.forecast_60d}%.")
    if item.signals_summary:
        details.append(item.signals_summary)
    return details[:4]


def _normalize_channel_from_action(action: str | None) -> str | None:
    normalized = (action or "").strip().lower()
    if normalized in {"call", "whatsapp", "task"}:
        return normalized
    if normalized == "notify":
        return "in_app"
    return None


def _build_retention_snapshot(item: RetentionQueueItem, member: Member | None) -> dict:
    member_id = UUID(item.member_id)
    playbook_step = item.playbook_steps[0] if item.playbook_steps else None
    owner_user_id = member.assigned_user_id if member else None
    owner_label = member.assigned_user.full_name if member and getattr(member, "assigned_user", None) else None
    recommended_action = playbook_step.title if playbook_step else (item.next_action or "Revisar risco e preparar contato")
    recommended_channel = _normalize_channel_from_action(playbook_step.action if playbook_step else None)
    suggested_message = playbook_step.message.replace("{nome}", item.full_name) if playbook_step else None
    owner_role = playbook_step.owner if playbook_step else ("manager" if item.risk_level == RiskLevel.RED else "reception")
    priority = _retention_priority_score(item)

    return {
        "source_domain": "retention",
        "source_entity_kind": "member",
        "source_entity_id": member_id,
        "member_id": member_id,
        "lead_id": None,
        "subject_name": item.full_name,
        "priority_score": priority,
        "priority_bucket": _priority_bucket(priority),
        "why_now_summary": item.signals_summary or "Aluno em risco requer acao agora.",
        "why_now_details": _retention_why_now_details(item),
        "recommended_action": recommended_action,
        "recommended_channel": recommended_channel,
        "recommended_owner": _recommended_owner_payload(owner_user_id, owner_role, owner_label),
        "suggested_message": suggested_message,
        "expected_impact": _retention_expected_impact(item),
        "metadata": {
            "risk_level": item.risk_level.value,
            "risk_score": item.risk_score,
            "churn_type": item.churn_type,
            "forecast_60d": item.forecast_60d,
            "days_without_checkin": item.days_without_checkin,
            "next_action": item.next_action,
            "preferred_shift": getattr(member, "preferred_shift", None) if member else None,
            "subject_phone": getattr(member, "phone", None) if member else None,
        },
    }


def _onboarding_priority_score(*, score: int, status: str, has_assessment: bool, total_tasks: int, completed_tasks: int, days_since_join: int) -> int:
    priority = max(0, 100 - score)
    if status == "at_risk":
        priority += 20
    if not has_assessment:
        priority += 10
    if total_tasks > completed_tasks:
        priority += 10
    if days_since_join >= 7:
        priority += 5
    return max(0, min(100, priority))


def _build_onboarding_snapshot(
    *,
    member: Member,
    score: int,
    status: str,
    days_since_join: int,
    has_assessment: bool,
    total_tasks: int,
    completed_tasks: int,
) -> dict:
    days_without_checkin = None
    if member.last_checkin_at is not None:
        reference = member.last_checkin_at
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        days_without_checkin = max(0, (_utcnow() - reference).days)

    if not has_assessment:
        recommended_action = "Concluir primeira avaliacao de onboarding"
        recommended_channel = "task"
        owner_role = "coach"
        suggested_message = "Agendar a primeira avaliacao para destravar a jornada inicial do aluno."
    elif status == "at_risk" or score < 40:
        recommended_action = "Contato humano imediato para destravar onboarding"
        recommended_channel = "whatsapp" if member.phone else "call"
        owner_role = "reception"
        suggested_message = f"Ola {member.full_name}, vamos ajustar seu onboarding para voce ganhar ritmo nesta semana."
    elif total_tasks > completed_tasks:
        recommended_action = "Retomar tarefas da jornada inicial"
        recommended_channel = "task"
        owner_role = "reception"
        suggested_message = "Revisar os proximos checkpoints de onboarding e garantir handoff no prazo."
    else:
        recommended_action = "Check-in proativo de onboarding"
        recommended_channel = "whatsapp" if member.phone else "call"
        owner_role = "reception"
        suggested_message = f"Ola {member.full_name}, quero conferir como esta sua adaptacao aos primeiros dias de treino."

    priority = _onboarding_priority_score(
        score=score,
        status=status,
        has_assessment=has_assessment,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        days_since_join=days_since_join,
    )

    why_now_details = [
        f"Dia {days_since_join} do onboarding.",
        f"Score de onboarding atual: {score}.",
    ]
    if not has_assessment:
        why_now_details.append("Primeira avaliacao ainda nao registrada.")
    if total_tasks:
        why_now_details.append(f"{completed_tasks}/{total_tasks} tarefas de onboarding concluidas.")
    if isinstance(days_without_checkin, int):
        why_now_details.append(f"{days_without_checkin} dias sem check-in.")

    owner_label = member.assigned_user.full_name if getattr(member, "assigned_user", None) else None

    return {
        "source_domain": "onboarding",
        "source_entity_kind": "member",
        "source_entity_id": member.id,
        "member_id": member.id,
        "lead_id": None,
        "subject_name": member.full_name,
        "priority_score": priority,
        "priority_bucket": _priority_bucket(priority),
        "why_now_summary": "Onboarding ativo exige acao coordenada nas proximas 24 horas.",
        "why_now_details": why_now_details[:4],
        "recommended_action": recommended_action,
        "recommended_channel": recommended_channel,
        "recommended_owner": _recommended_owner_payload(member.assigned_user_id, owner_role, owner_label),
        "suggested_message": suggested_message,
        "expected_impact": "Reduzir risco de dropout nos primeiros 30 dias e acelerar a adaptacao do aluno.",
        "metadata": {
            "onboarding_status": status,
            "onboarding_score": score,
            "days_since_join": days_since_join,
            "has_assessment": has_assessment,
            "total_onboarding_tasks": total_tasks,
            "completed_onboarding_tasks": completed_tasks,
            "preferred_shift": getattr(member, "preferred_shift", None),
            "subject_phone": member.phone,
        },
    }


def _load_member_map(db: Session, member_ids: list[UUID]) -> dict[UUID, Member]:
    if not member_ids:
        return {}
    members = db.scalars(
        select(Member)
        .options(joinedload(Member.assigned_user))
        .where(Member.id.in_(member_ids))
    ).all()
    return {member.id: member for member in members}


def _build_retention_snapshots(db: Session, gym_id: UUID, *, limit: int) -> list[dict]:
    queue = get_retention_queue(db, page=1, page_size=limit, gym_id=gym_id)
    member_ids = [UUID(item.member_id) for item in queue.items]
    member_map = _load_member_map(db, member_ids)
    return [_build_retention_snapshot(item, member_map.get(UUID(item.member_id))) for item in queue.items]


def _build_onboarding_snapshots(db: Session, gym_id: UUID, *, limit: int) -> list[dict]:
    cutoff = (_utcnow() - timedelta(days=30)).date()
    members = list(
        db.scalars(
            select(Member)
            .options(joinedload(Member.assigned_user))
            .where(
                Member.gym_id == gym_id,
                Member.deleted_at.is_(None),
                Member.status == MemberStatus.ACTIVE,
                Member.join_date >= cutoff,
                Member.onboarding_status.in_(("active", "at_risk")),
            )
            .order_by(case((Member.onboarding_status == "at_risk", 0), else_=1), Member.onboarding_score.asc(), Member.join_date.asc())
            .limit(limit)
        ).all()
    )
    if not members:
        return []

    member_ids = [member.id for member in members]
    assessment_ids = {
        member_id
        for member_id in db.scalars(
            select(Assessment.member_id)
            .where(Assessment.member_id.in_(member_ids), Assessment.deleted_at.is_(None))
            .distinct()
        ).all()
        if member_id is not None
    }

    task_rows = db.execute(
        select(
            Task.member_id.label("member_id"),
            func.count(Task.id).label("total_tasks"),
            func.sum(case((Task.status == TaskStatus.DONE, 1), else_=0)).label("completed_tasks"),
        )
        .where(
            Task.member_id.in_(member_ids),
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "onboarding",
        )
        .group_by(Task.member_id)
    ).all()
    task_map = {
        row.member_id: {
            "total": int(row.total_tasks or 0),
            "completed": int(row.completed_tasks or 0),
        }
        for row in task_rows
    }

    snapshots: list[dict] = []
    today = _utcnow().date()
    for member in members:
        task_stats = task_map.get(member.id, {"total": 0, "completed": 0})
        snapshots.append(
            _build_onboarding_snapshot(
                member=member,
                score=int(member.onboarding_score or 0),
                status=str(member.onboarding_status or "active"),
                days_since_join=max(1, (today - member.join_date).days),
                has_assessment=member.id in assessment_ids,
                total_tasks=task_stats["total"],
                completed_tasks=task_stats["completed"],
            )
        )
    return snapshots


def _is_degraded_snapshot(snapshot: dict) -> bool:
    owner_snapshot = dict(snapshot.get("recommended_owner") or {})
    return not snapshot.get("recommended_channel") or not owner_snapshot.get("role")


def _requires_explicit_approval(recommendation: AITriageRecommendation, snapshot: dict) -> bool:
    priority_bucket = snapshot.get("priority_bucket", _priority_bucket(recommendation.priority_score))
    return priority_bucket == "critical" or _is_degraded_snapshot(snapshot)


def _primary_action_type(snapshot: dict) -> str:
    channel = snapshot.get("recommended_channel")
    suggested_message = snapshot.get("suggested_message")
    if channel in {"whatsapp", "call", "in_app"} and suggested_message:
        return "prepare_outbound_message"
    if channel == "task":
        return "create_task"
    if snapshot.get("source_domain") == "retention":
        return "open_follow_up"
    return "create_task"


def _primary_action_label(snapshot: dict, action_type: str) -> str:
    channel = snapshot.get("recommended_channel")
    if action_type == "prepare_outbound_message":
        if channel == "whatsapp":
            return "Preparar WhatsApp"
        if channel == "call":
            return "Preparar ligacao"
        return "Preparar mensagem"
    if action_type == "open_follow_up":
        return "Abrir follow-up"
    if action_type == "assign_owner":
        return "Atribuir responsavel"
    return "Criar tarefa"


def _operator_summary(snapshot: dict) -> str:
    return snapshot.get("why_now_summary") or snapshot.get("recommended_action") or "Recommendation pronta para acao."


def _show_outcome_step(recommendation: AITriageRecommendation) -> bool:
    return recommendation.approval_state == "approved" and (
        recommendation.execution_state in PREPARED_EXECUTION_STATES or recommendation.outcome_state != "pending"
    )


def _serialize_recommendation(recommendation: AITriageRecommendation) -> AITriageRecommendationRead:
    snapshot = dict(recommendation.payload_snapshot or {})
    owner_snapshot = snapshot.get("recommended_owner") or {}
    primary_action_type = _primary_action_type(snapshot)
    return AITriageRecommendationRead(
        id=recommendation.id,
        source_domain=recommendation.source_domain,
        source_entity_kind=recommendation.source_entity_kind,
        source_entity_id=recommendation.source_entity_id,
        member_id=recommendation.member_id,
        lead_id=recommendation.lead_id,
        subject_name=snapshot.get("subject_name", ""),
        priority_score=recommendation.priority_score,
        priority_bucket=snapshot.get("priority_bucket", _priority_bucket(recommendation.priority_score)),
        why_now_summary=snapshot.get("why_now_summary", ""),
        why_now_details=list(snapshot.get("why_now_details") or []),
        recommended_action=snapshot.get("recommended_action", ""),
        recommended_channel=snapshot.get("recommended_channel"),
        recommended_owner=AITriageRecommendedOwner.model_validate(owner_snapshot) if owner_snapshot else None,
        suggested_message=snapshot.get("suggested_message"),
        expected_impact=snapshot.get("expected_impact", ""),
        operator_summary=_operator_summary(snapshot),
        primary_action_type=primary_action_type,
        primary_action_label=_primary_action_label(snapshot, primary_action_type),
        requires_explicit_approval=_requires_explicit_approval(recommendation, snapshot),
        show_outcome_step=_show_outcome_step(recommendation),
        suggestion_state=recommendation.suggestion_state,
        approval_state=recommendation.approval_state,
        execution_state=recommendation.execution_state,
        outcome_state=recommendation.outcome_state,
        metadata=dict(snapshot.get("metadata") or {}),
        last_refreshed_at=recommendation.last_refreshed_at,
    )


def _snapshot_copy(recommendation: AITriageRecommendation) -> dict:
    return dict(recommendation.payload_snapshot or {})


def _snapshot_metadata(snapshot: dict) -> dict:
    return dict(snapshot.get("metadata") or {})


def _persist_snapshot(
    recommendation: AITriageRecommendation,
    *,
    snapshot: dict,
    metadata: dict,
    execution_state: str | None = None,
    outcome_state: str | None = None,
) -> None:
    snapshot["metadata"] = metadata
    recommendation.payload_snapshot = _json_safe(snapshot)
    recommendation.last_refreshed_at = _utcnow()
    if execution_state is not None:
        recommendation.execution_state = execution_state
    if outcome_state is not None:
        recommendation.outcome_state = outcome_state


def _task_priority_for_recommendation(recommendation: AITriageRecommendation) -> TaskPriority:
    if recommendation.priority_score >= 85:
        return TaskPriority.URGENT
    if recommendation.priority_score >= 65:
        return TaskPriority.HIGH
    if recommendation.priority_score >= 40:
        return TaskPriority.MEDIUM
    return TaskPriority.LOW


def _follow_up_url_for_recommendation(recommendation: AITriageRecommendation) -> str | None:
    if recommendation.member_id:
        return f"/assessments/members/{recommendation.member_id}?tab=acoes"
    if recommendation.lead_id:
        return f"/crm?leadId={recommendation.lead_id}"
    return None


def _resolve_owner_for_action(
    db: Session,
    *,
    gym_id: UUID,
    assigned_to_user_id: UUID | None,
    owner_role: str | None,
    owner_label: str | None,
    existing_owner: dict | None,
) -> dict | None:
    candidate_id = assigned_to_user_id
    if candidate_id is None and existing_owner:
        candidate_id = existing_owner.get("user_id")
    if candidate_id:
        candidate_uuid = UUID(str(candidate_id))
        owner = db.scalar(
            select(User).where(
                User.id == candidate_uuid,
                User.gym_id == gym_id,
            )
        )
        if owner is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner sugerido nao encontrado")
        return _recommended_owner_payload(owner.id, owner.role.value, owner.full_name)

    resolved_role = owner_role or (existing_owner.get("role") if existing_owner else None)
    resolved_label = owner_label or (existing_owner.get("label") if existing_owner else None)
    if resolved_role or resolved_label:
        return _recommended_owner_payload(None, resolved_role, resolved_label)
    return None


def _task_title_for_recommendation(snapshot: dict) -> str:
    subject_name = snapshot.get("subject_name") or "Contato"
    recommended_action = snapshot.get("recommended_action") or "Revisar recomendacao AI"
    return f"{recommended_action} - {subject_name}"[:160]


def _task_description_for_recommendation(snapshot: dict) -> str:
    why_now_summary = snapshot.get("why_now_summary") or "Recommendation gerada pela AI Inbox."
    expected_impact = snapshot.get("expected_impact") or "Executar follow-up com contexto."
    suggested_message = snapshot.get("suggested_message")
    details = list(snapshot.get("why_now_details") or [])

    chunks = [
        f"Why now: {why_now_summary}",
        f"Impacto esperado: {expected_impact}",
    ]
    if details:
        chunks.append("Sinais: " + " | ".join(details[:3]))
    if suggested_message:
        chunks.append(f"Mensagem sugerida: {suggested_message}")
    return "\n\n".join(chunks)


def _log_recommendation_suggested(
    db: Session,
    *,
    recommendation: AITriageRecommendation,
    action: str,
) -> None:
    log_audit_event(
        db,
        action=action,
        entity="ai_triage_recommendation",
        gym_id=recommendation.gym_id,
        member_id=recommendation.member_id,
        entity_id=recommendation.id,
        details={
            "source_domain": recommendation.source_domain,
            "source_entity_kind": recommendation.source_entity_kind,
            "source_entity_id": str(recommendation.source_entity_id),
            "priority_score": recommendation.priority_score,
            "approval_state": recommendation.approval_state,
            "execution_state": recommendation.execution_state,
            "outcome_state": recommendation.outcome_state,
        },
        flush=False,
    )


def sync_ai_triage_recommendations(db: Session, *, gym_id: UUID, limit_per_domain: int = 50) -> list[AITriageRecommendationRead]:
    now = _utcnow()
    snapshots = [
        *_build_retention_snapshots(db, gym_id, limit=limit_per_domain),
        *_build_onboarding_snapshots(db, gym_id, limit=limit_per_domain),
    ]

    existing = {
        (recommendation.source_domain, recommendation.source_entity_kind, recommendation.source_entity_id): recommendation
        for recommendation in db.scalars(
            select(AITriageRecommendation).where(
                AITriageRecommendation.gym_id == gym_id,
                AITriageRecommendation.source_domain.in_(ACTIVE_TRIAGE_DOMAINS),
            )
        ).all()
    }

    seen_keys: set[tuple[str, str, UUID]] = set()
    for snapshot in snapshots:
        snapshot = _json_safe(snapshot)
        key = (
            snapshot["source_domain"],
            snapshot["source_entity_kind"],
            UUID(str(snapshot["source_entity_id"])),
        )
        seen_keys.add(key)
        recommendation = existing.get(key)

        if recommendation is None:
            recommendation = AITriageRecommendation(
                id=uuid4(),
                gym_id=gym_id,
                source_domain=snapshot["source_domain"],
                source_entity_kind=snapshot["source_entity_kind"],
                source_entity_id=UUID(str(snapshot["source_entity_id"])),
                member_id=UUID(str(snapshot["member_id"])) if snapshot.get("member_id") else None,
                lead_id=UUID(str(snapshot["lead_id"])) if snapshot.get("lead_id") else None,
                priority_score=int(snapshot["priority_score"]),
                suggestion_state="suggested",
                approval_state="pending",
                execution_state="pending",
                outcome_state="pending",
                last_refreshed_at=now,
                payload_snapshot=snapshot,
                is_active=True,
            )
            db.add(recommendation)
            _log_recommendation_suggested(db, recommendation=recommendation, action="ai_triage_recommendation_suggested")
            existing[key] = recommendation
            continue

        changed = (
            recommendation.priority_score != int(snapshot["priority_score"])
            or recommendation.payload_snapshot != snapshot
            or not recommendation.is_active
        )
        recommendation.member_id = UUID(str(snapshot["member_id"])) if snapshot.get("member_id") else None
        recommendation.lead_id = UUID(str(snapshot["lead_id"])) if snapshot.get("lead_id") else None
        recommendation.priority_score = int(snapshot["priority_score"])
        recommendation.payload_snapshot = snapshot
        recommendation.last_refreshed_at = now
        recommendation.is_active = True
        db.add(recommendation)
        if changed:
            _log_recommendation_suggested(db, recommendation=recommendation, action="ai_triage_recommendation_refreshed")

    for key, recommendation in existing.items():
        if key in seen_keys or not recommendation.is_active:
            continue
        recommendation.is_active = False
        recommendation.last_refreshed_at = now
        db.add(recommendation)

    db.flush()
    return list_ai_triage_recommendations(db, gym_id=gym_id, page=1, page_size=limit_per_domain * len(ACTIVE_TRIAGE_DOMAINS)).items


def list_ai_triage_recommendations(
    db: Session,
    *,
    gym_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[AITriageRecommendationRead]:
    criteria = (
        AITriageRecommendation.gym_id == gym_id,
        AITriageRecommendation.is_active.is_(True),
    )
    total = int(
        db.scalar(
            select(func.count()).select_from(AITriageRecommendation).where(*criteria)
        )
        or 0
    )
    recommendations = list(
        db.scalars(
            select(AITriageRecommendation)
            .where(*criteria)
            .order_by(AITriageRecommendation.priority_score.desc(), AITriageRecommendation.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return PaginatedResponse(
        items=[_serialize_recommendation(recommendation) for recommendation in recommendations],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_ai_triage_recommendation_or_404(
    db: Session,
    *,
    recommendation_id: UUID,
    gym_id: UUID,
) -> AITriageRecommendation:
    recommendation = db.scalar(
        select(AITriageRecommendation).where(
            AITriageRecommendation.id == recommendation_id,
            AITriageRecommendation.gym_id == gym_id,
            AITriageRecommendation.is_active.is_(True),
        )
    )
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation nao encontrada")
    return recommendation


def serialize_ai_triage_recommendation(recommendation: AITriageRecommendation) -> AITriageRecommendationRead:
    return _serialize_recommendation(recommendation)


def _apply_approval_decision(
    db: Session,
    *,
    recommendation: AITriageRecommendation,
    decision: str,
    current_user: User,
    note: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    previous_approval_state = recommendation.approval_state
    recommendation.suggestion_state = "reviewed"
    recommendation.approval_state = decision
    recommendation.last_refreshed_at = _utcnow()
    if decision == "approved":
        recommendation.execution_state = "pending"
        if recommendation.outcome_state == "dismissed":
            recommendation.outcome_state = "pending"
    else:
        recommendation.execution_state = "blocked"
        recommendation.outcome_state = "dismissed"

    db.add(recommendation)
    log_audit_event(
        db,
        action=f"ai_triage_recommendation_{decision}",
        entity="ai_triage_recommendation",
        user=current_user,
        member_id=recommendation.member_id,
        entity_id=recommendation.id,
        details={
            "source_domain": recommendation.source_domain,
            "source_entity_kind": recommendation.source_entity_kind,
            "source_entity_id": str(recommendation.source_entity_id),
            "previous_approval_state": previous_approval_state,
            "approval_state": recommendation.approval_state,
            "execution_state": recommendation.execution_state,
            "outcome_state": recommendation.outcome_state,
            "note": note,
        },
        ip_address=ip_address,
        user_agent=user_agent,
        flush=False,
    )


def update_ai_triage_recommendation_approval(
    db: Session,
    *,
    recommendation_id: UUID,
    gym_id: UUID,
    decision: str,
    current_user: User,
    note: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AITriageRecommendationRead:
    recommendation = get_ai_triage_recommendation_or_404(
        db,
        recommendation_id=recommendation_id,
        gym_id=gym_id,
    )
    _apply_approval_decision(
        db,
        recommendation=recommendation,
        decision=decision,
        current_user=current_user,
        note=note,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.flush()
    return serialize_ai_triage_recommendation(recommendation)


def prepare_ai_triage_recommendation_action(
    db: Session,
    *,
    recommendation_id: UUID,
    gym_id: UUID,
    action: str,
    current_user: User,
    assigned_to_user_id: UUID | None = None,
    owner_role: str | None = None,
    owner_label: str | None = None,
    note: str | None = None,
    operator_note: str | None = None,
    auto_approve: bool = False,
    confirm_approval: bool = False,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AITriageSafeActionPreparedRead:
    recommendation = get_ai_triage_recommendation_or_404(
        db,
        recommendation_id=recommendation_id,
        gym_id=gym_id,
    )
    snapshot = _snapshot_copy(recommendation)
    resolved_note = operator_note or note
    requires_explicit_approval = _requires_explicit_approval(recommendation, snapshot)
    if recommendation.approval_state == "rejected":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Recommendation rejeitada; revise antes de agir.")
    if recommendation.approval_state != "approved":
        if requires_explicit_approval:
            if not confirm_approval:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Recommendation critica ou degradada exige confirmacao explicita antes da acao.",
                )
            _apply_approval_decision(
                db,
                recommendation=recommendation,
                decision="approved",
                current_user=current_user,
                note=resolved_note,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        elif auto_approve:
            _apply_approval_decision(
                db,
                recommendation=recommendation,
                decision="approved",
                current_user=current_user,
                note=resolved_note,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Recommendation precisa de aprovacao implicita ou explicita antes de preparar qualquer acao.",
            )

    metadata = _snapshot_metadata(snapshot)
    existing_owner = dict(snapshot.get("recommended_owner") or {})
    now = _utcnow()

    supported = True
    detail = "Acao preparada com sucesso."
    task_id: UUID | None = None
    follow_up_url: str | None = None
    prepared_message: str | None = None

    if action == "create_task":
        resolved_owner = _resolve_owner_for_action(
            db,
            gym_id=gym_id,
            assigned_to_user_id=assigned_to_user_id,
            owner_role=owner_role,
            owner_label=owner_label,
            existing_owner=existing_owner,
        )
        task = create_task(
            db,
            TaskCreate(
                title=_task_title_for_recommendation(snapshot),
                description=_task_description_for_recommendation(snapshot),
                member_id=recommendation.member_id,
                lead_id=recommendation.lead_id,
                assigned_to_user_id=resolved_owner["user_id"] if resolved_owner else None,
                priority=_task_priority_for_recommendation(recommendation),
                suggested_message=snapshot.get("suggested_message"),
                extra_data={
                    "source": "ai_triage",
                    "ai_triage_recommendation_id": str(recommendation.id),
                    "source_domain": recommendation.source_domain,
                    "recommended_channel": snapshot.get("recommended_channel"),
                    "owner_role": (resolved_owner or existing_owner).get("role") if (resolved_owner or existing_owner) else None,
                },
            ),
            commit=False,
        )
        task_id = task.id
        snapshot["recommended_owner"] = resolved_owner or existing_owner
        metadata.update(
                {
                    "prepared_action": "create_task",
                    "prepared_task_id": str(task.id),
                    "prepared_at": now.isoformat(),
                    "prepared_by_user_id": str(current_user.id),
                    "last_action_note": resolved_note,
                }
            )
        _persist_snapshot(recommendation, snapshot=snapshot, metadata=metadata, execution_state="prepared")
        log_audit_event(
            db,
            action="task_created",
            entity="task",
            user=current_user,
            member_id=recommendation.member_id,
            entity_id=task.id,
            details={
                "source": "ai_triage",
                "recommendation_id": str(recommendation.id),
                "priority": task.priority.value,
                "status": task.status.value,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            flush=False,
        )
        detail = "Task preparada a partir da recommendation aprovada."
    elif action == "assign_owner":
        resolved_owner = _resolve_owner_for_action(
            db,
            gym_id=gym_id,
            assigned_to_user_id=assigned_to_user_id,
            owner_role=owner_role,
            owner_label=owner_label,
            existing_owner=existing_owner,
        )
        if resolved_owner is None:
            supported = False
            detail = "Nenhum owner concreto foi informado para esta recommendation."
        else:
            snapshot["recommended_owner"] = resolved_owner
            task_id_raw = metadata.get("prepared_task_id")
            if task_id_raw:
                task = db.get(Task, UUID(str(task_id_raw)))
                if task and task.gym_id == gym_id and task.deleted_at is None:
                    task.assigned_to_user_id = resolved_owner.get("user_id")
                    db.add(task)
                    task_id = task.id
            metadata.update(
                {
                    "prepared_action": "assign_owner",
                    "prepared_at": now.isoformat(),
                    "prepared_by_user_id": str(current_user.id),
                    "last_action_note": resolved_note,
                }
            )
            _persist_snapshot(recommendation, snapshot=snapshot, metadata=metadata, execution_state="prepared")
            detail = "Owner da recommendation atualizado."
    elif action == "open_follow_up":
        follow_up_url = _follow_up_url_for_recommendation(recommendation)
        if follow_up_url is None:
            supported = False
            detail = "Nao ha contexto de follow-up navegavel para esta recommendation."
        else:
            metadata.update(
                {
                    "prepared_action": "open_follow_up",
                    "prepared_at": now.isoformat(),
                    "prepared_by_user_id": str(current_user.id),
                    "follow_up_url": follow_up_url,
                    "last_action_note": resolved_note,
                }
            )
            _persist_snapshot(recommendation, snapshot=snapshot, metadata=metadata, execution_state="prepared")
            detail = "Follow-up seguro preparado no contexto operacional existente."
    elif action == "prepare_outbound_message":
        prepared_message = snapshot.get("suggested_message")
        if not prepared_message:
            supported = False
            detail = "Esta recommendation nao possui mensagem preparada com confianca."
        else:
            metadata.update(
                {
                    "prepared_action": "prepare_outbound_message",
                    "prepared_at": now.isoformat(),
                    "prepared_by_user_id": str(current_user.id),
                    "last_action_note": resolved_note,
                }
            )
            _persist_snapshot(recommendation, snapshot=snapshot, metadata=metadata, execution_state="prepared")
            detail = "Mensagem preparada para revisao humana antes do envio."
    elif action == "enqueue_approved_job":
        supported = False
        detail = "Nenhum job seguro esta mapeado para esta recommendation nesta fase."
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Acao segura nao suportada")

    log_audit_event(
        db,
        action="ai_triage_action_prepared" if supported else "ai_triage_action_unavailable",
        entity="ai_triage_recommendation",
        user=current_user,
        member_id=recommendation.member_id,
        entity_id=recommendation.id,
        details={
            "action": action,
            "supported": supported,
            "detail": detail,
            "execution_state": recommendation.execution_state,
            "outcome_state": recommendation.outcome_state,
            "task_id": str(task_id) if task_id else None,
            "follow_up_url": follow_up_url,
            "note": resolved_note,
            "auto_approve": auto_approve,
            "confirm_approval": confirm_approval,
        },
        ip_address=ip_address,
        user_agent=user_agent,
        flush=False,
    )
    db.flush()
    return AITriageSafeActionPreparedRead(
        recommendation=serialize_ai_triage_recommendation(recommendation),
        action=action,
        supported=supported,
        detail=detail,
        task_id=task_id,
        follow_up_url=follow_up_url,
        prepared_message=prepared_message,
        metadata=dict(metadata),
    )


def update_ai_triage_recommendation_outcome(
    db: Session,
    *,
    recommendation_id: UUID,
    gym_id: UUID,
    outcome: str,
    current_user: User,
    note: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AITriageRecommendationRead:
    recommendation = get_ai_triage_recommendation_or_404(
        db,
        recommendation_id=recommendation_id,
        gym_id=gym_id,
    )
    if recommendation.approval_state != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recommendation precisa estar aprovada antes de registrar outcome.",
        )

    previous_outcome_state = recommendation.outcome_state
    snapshot = _snapshot_copy(recommendation)
    metadata = _snapshot_metadata(snapshot)

    metadata.update(
        {
            "last_outcome_note": note,
            "last_outcome_recorded_at": _utcnow().isoformat(),
            "last_outcome_recorded_by_user_id": str(current_user.id),
        }
    )
    execution_state = recommendation.execution_state
    if outcome in FINAL_OUTCOME_STATES and recommendation.execution_state in {"pending", "prepared", "queued", "running"}:
        execution_state = "completed"

    _persist_snapshot(
        recommendation,
        snapshot=snapshot,
        metadata=metadata,
        execution_state=execution_state,
        outcome_state=outcome,
    )
    db.add(recommendation)
    log_audit_event(
        db,
        action="ai_triage_outcome_updated",
        entity="ai_triage_recommendation",
        user=current_user,
        member_id=recommendation.member_id,
        entity_id=recommendation.id,
        details={
            "previous_outcome_state": previous_outcome_state,
            "outcome_state": recommendation.outcome_state,
            "execution_state": recommendation.execution_state,
            "note": note,
        },
        ip_address=ip_address,
        user_agent=user_agent,
        flush=False,
    )
    db.flush()
    return serialize_ai_triage_recommendation(recommendation)


def get_ai_triage_metrics_summary(
    db: Session,
    *,
    gym_id: UUID,
    window_days: int = 30,
) -> AITriageMetricsSummaryRead:
    recommendations = list(
        db.scalars(
            select(AITriageRecommendation).where(
                AITriageRecommendation.gym_id == gym_id,
                AITriageRecommendation.is_active.is_(True),
            )
        ).all()
    )
    cutoff = _utcnow() - timedelta(days=window_days)
    audit_events = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.gym_id == gym_id,
                AuditLog.entity == "ai_triage_recommendation",
                AuditLog.action.in_(
                    (
                        "ai_triage_recommendation_suggested",
                        "ai_triage_recommendation_refreshed",
                        "ai_triage_recommendation_approved",
                        "ai_triage_recommendation_rejected",
                        "ai_triage_action_prepared",
                        "ai_triage_outcome_updated",
                    )
                ),
                AuditLog.created_at >= cutoff,
            )
            .order_by(AuditLog.created_at.asc())
        ).all()
    )

    suggestion_at: dict[UUID, datetime] = {}
    approval_at: dict[UUID, datetime] = {}
    prepared_at: dict[UUID, datetime] = {}
    for event in audit_events:
        if event.entity_id is None:
            continue
        entity_id = event.entity_id
        if event.action in {"ai_triage_recommendation_suggested", "ai_triage_recommendation_refreshed"}:
            suggestion_at.setdefault(entity_id, event.created_at)
        elif event.action == "ai_triage_recommendation_approved":
            approval_at.setdefault(entity_id, event.created_at)
        elif event.action == "ai_triage_action_prepared":
            prepared_at.setdefault(entity_id, event.created_at)

    approval_deltas = [
        max((approval_at[entity_id] - suggested_at).total_seconds(), 0.0)
        for entity_id, suggested_at in suggestion_at.items()
        if entity_id in approval_at
    ]
    same_day_prepared_total = sum(
        1
        for entity_id, approved_at in approval_at.items()
        if entity_id in prepared_at and prepared_at[entity_id].date() == approved_at.date()
    )

    approved_total = sum(1 for recommendation in recommendations if recommendation.approval_state == "approved")
    rejected_total = sum(1 for recommendation in recommendations if recommendation.approval_state == "rejected")
    decisions_total = approved_total + rejected_total

    return AITriageMetricsSummaryRead(
        total_active=len(recommendations),
        pending_approval_total=sum(1 for recommendation in recommendations if recommendation.approval_state == "pending"),
        approved_total=approved_total,
        rejected_total=rejected_total,
        prepared_action_total=sum(1 for recommendation in recommendations if recommendation.execution_state in PREPARED_EXECUTION_STATES),
        positive_outcome_total=sum(1 for recommendation in recommendations if recommendation.outcome_state == "positive"),
        neutral_outcome_total=sum(1 for recommendation in recommendations if recommendation.outcome_state == "neutral"),
        negative_outcome_total=sum(1 for recommendation in recommendations if recommendation.outcome_state == "negative"),
        acceptance_rate=(approved_total / decisions_total) if decisions_total else None,
        average_time_to_approval_seconds=mean(approval_deltas) if approval_deltas else None,
        median_time_to_approval_seconds=median(approval_deltas) if approval_deltas else None,
        same_day_prepared_total=same_day_prepared_total,
    )
