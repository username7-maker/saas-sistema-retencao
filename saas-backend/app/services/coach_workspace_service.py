from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import RoleEnum, User
from app.schemas.coach import (
    CoachWorkspaceEvidenceOut,
    CoachWorkspaceItemOut,
    CoachWorkspaceLane,
    CoachWorkspaceOut,
    CoachWorkspaceShift,
    CoachWorkspaceState,
    CoachWorkspaceSummaryOut,
)
from app.schemas.work_queue import WorkQueueItemOut
from app.services.work_queue_service import list_work_queue_items


LANE_LABELS: dict[CoachWorkspaceLane, str] = {
    "training_delivery": "Treino entregue",
    "training_feedback": "Feedback do treino",
    "reassessment": "Reavaliacao",
    "assessment_pending": "Avaliacao pendente",
    "body_composition_review": "Bioimpedancia",
    "training_adjustment": "Ajuste de treino",
    "technical_attention": "Atencao tecnica",
}

TECHNICAL_OUTCOMES_BY_LANE: dict[CoachWorkspaceLane, list[str]] = {
    "training_delivery": ["training_delivered", "training_missing", "forwarded_to_reception"],
    "training_feedback": ["feedback_positive", "needs_training_adjustment", "no_response"],
    "reassessment": ["reassessment_scheduled", "postponed", "forwarded_to_reception"],
    "assessment_pending": ["scheduled_assessment", "postponed", "forwarded_to_reception"],
    "body_composition_review": ["training_adjusted", "completed", "needs_training_adjustment"],
    "training_adjustment": ["training_adjusted", "completed", "needs_training_adjustment"],
    "technical_attention": ["completed", "forwarded_to_reception", "no_response"],
}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _lane_for_item(item: WorkQueueItemOut) -> CoachWorkspaceLane:
    step = (item.technical_ladder_step or "").lower()
    action = (item.primary_action_label or "").lower()
    reason = (item.reason or "").lower()
    badges = " ".join(item.autopilot_badges or []).lower()
    text = " ".join([step, action, reason, badges])

    if step == "training_delivery_check_d8" or "verificar treino" in text or "treino entregue" in text:
        return "training_delivery"
    if step == "training_feedback_d14" or "feedback" in text:
        return "training_feedback"
    if step == "reassessment_due" or "reavali" in text:
        return "reassessment"
    if item.source_type == "assessment_queue" or "primeira avaliacao" in text:
        return "assessment_pending"
    if "bioimped" in text or "composicao corporal" in text:
        return "body_composition_review"
    if "ajust" in text or "revisar treino" in text or "training" in text:
        return "training_adjustment"
    return "technical_attention"


def _evidence_for_item(item: WorkQueueItemOut) -> list[CoachWorkspaceEvidenceOut]:
    evidence: list[CoachWorkspaceEvidenceOut] = []
    if item.technical_ladder_step_label:
        evidence.append(CoachWorkspaceEvidenceOut(label="Etapa", value=item.technical_ladder_step_label))
    if item.preferred_shift:
        evidence.append(CoachWorkspaceEvidenceOut(label="Turno do aluno", value=item.preferred_shift))
    if item.due_at:
        evidence.append(CoachWorkspaceEvidenceOut(label="Prazo", value=item.due_at.date().isoformat()))
    if item.reason:
        evidence.append(CoachWorkspaceEvidenceOut(label="Motivo", value=item.reason[:140]))
    if item.outcome_state and item.outcome_state != "pending":
        evidence.append(CoachWorkspaceEvidenceOut(label="Resultado", value=item.outcome_state))
    return evidence


def _to_coach_item(item: WorkQueueItemOut) -> CoachWorkspaceItemOut:
    lane = _lane_for_item(item)
    return CoachWorkspaceItemOut(
        source_type=item.source_type,
        source_id=item.source_id,
        member_id=item.member_id,
        subject_name=item.subject_name,
        preferred_shift=item.preferred_shift,
        lane=lane,
        lane_label=LANE_LABELS[lane],
        severity=item.severity,
        state=item.state,
        next_action_label=item.primary_action_label,
        reason=item.reason,
        due_at=item.due_at,
        visible_from=item.visible_from,
        context_path=item.context_path,
        suggested_message=item.suggested_message,
        technical_ladder_step=item.technical_ladder_step,
        technical_ladder_step_label=item.technical_ladder_step_label,
        evidence=_evidence_for_item(item),
        allowed_outcomes=TECHNICAL_OUTCOMES_BY_LANE[lane],
    )


def _summary_for_items(items: list[CoachWorkspaceItemOut], total: int) -> CoachWorkspaceSummaryOut:
    now = _now()
    by_lane = Counter(item.lane for item in items)
    return CoachWorkspaceSummaryOut(
        total=total,
        do_now=sum(1 for item in items if item.state == "do_now"),
        awaiting_outcome=sum(1 for item in items if item.state == "awaiting_outcome"),
        done=sum(1 for item in items if item.state == "done"),
        overdue=sum(1 for item in items if item.due_at is not None and item.due_at <= now and item.state != "done"),
        by_lane=dict(by_lane),
    )


def get_coach_workspace(
    db: Session,
    *,
    current_user: User,
    state: CoachWorkspaceState = "do_now",
    shift: CoachWorkspaceShift = "my_shift",
    page: int = 1,
    page_size: int = 25,
) -> CoachWorkspaceOut:
    """Return the staff-first technical queue for professors and managers."""
    effective_shift: CoachWorkspaceShift = shift
    if current_user.role not in {RoleEnum.OWNER, RoleEnum.MANAGER} and shift == "all":
        effective_shift = "my_shift"

    queue = list_work_queue_items(
        db,
        current_user=current_user,
        state=state,
        shift=effective_shift,
        assignee="all",
        domain="trainer",
        source="all",
        page=page,
        page_size=page_size,
    )
    items = [_to_coach_item(item) for item in queue.items if item.member_id is not None]
    return CoachWorkspaceOut(
        items=items,
        total=queue.total,
        page=queue.page,
        page_size=queue.page_size,
        state=state,
        shift=effective_shift,
        summary=_summary_for_items(items, queue.total),
        generated_at=_now(),
    )
