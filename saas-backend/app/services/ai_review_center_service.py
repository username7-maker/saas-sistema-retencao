from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutopilotAction, Lead, Member, MovementVideoReview, RoleEnum
from app.schemas.ai_review_center import (
    AiReviewCenterActionOut,
    AiReviewCenterFeedbackInput,
    AiReviewCenterItemOut,
    AiReviewCenterListOut,
    AiReviewCenterMetricsOut,
)
from app.schemas.movement_video import MovementVideoRejectInput
from app.services.ai_service_agent_service import (
    AI_SERVICE_AGENT_ACTION_TYPE,
    AI_SERVICE_AGENT_DRAFT_READY,
    prepare_ai_service_agent_draft_in_kommo,
    serialize_ai_service_agent_draft,
)
from app.services.autopilot_event_service import record_event
from app.services.movement_video_service import (
    MOVEMENT_VIDEO_ACTION_TYPE,
    prepare_movement_video_review_in_kommo,
    reject_movement_video_review,
)
from app.services.personal_ai_service import (
    PERSONAL_AI_ACTION_TYPE,
    PERSONAL_AI_DRAFT_READY,
    prepare_personal_ai_draft_in_kommo,
    serialize_personal_ai_draft,
)
from app.services.student_personal_ai_service import (
    STUDENT_PERSONAL_AI_ACTION_TYPE,
    STUDENT_PERSONAL_AI_DRAFT_READY,
    prepare_student_personal_ai_draft_in_kommo,
    reject_student_personal_ai_draft,
    serialize_student_personal_ai_draft,
)


ACTION_SOURCE_BY_TYPE = {
    AI_SERVICE_AGENT_ACTION_TYPE: "ai_service_agent",
    PERSONAL_AI_ACTION_TYPE: "personal_ai",
    STUDENT_PERSONAL_AI_ACTION_TYPE: "student_personal_ai",
    MOVEMENT_VIDEO_ACTION_TYPE: "movement_video",
}

VISIBLE_ACTION_TYPES = tuple(ACTION_SOURCE_BY_TYPE.keys())
DEFAULT_ACTION_STATUSES = {
    "draft_ready",
    "blocked",
    "escalated",
    "awaiting_outcome",
    "failed",
    "cancelled",
}
DEFAULT_REVIEW_STATUSES = {"pending_review", "needs_coach_review", "needs_media_retrieval", "blocked", "approved", "rejected"}
READY_STATUSES = {"draft_ready", "approved"}
TERMINAL_STATUSES = {"cancelled", "rejected", "succeeded", "completed"}


def list_ai_review_center_items(
    db: Session,
    *,
    gym_id: UUID,
    user_role: RoleEnum,
    source_filter: str | None = None,
    status_filter: str | None = None,
    q: str | None = None,
    limit: int = 100,
) -> AiReviewCenterListOut:
    allowed_sources = _allowed_sources_for_role(user_role)
    if source_filter and source_filter != "all":
        if source_filter not in allowed_sources:
            return AiReviewCenterListOut(items=[], metrics=AiReviewCenterMetricsOut(), generated_at=_now())
        allowed_sources = {source_filter}

    actions = _load_actions(db, gym_id=gym_id, allowed_sources=allowed_sources, status_filter=status_filter, limit=limit)
    movement_action_review_ids = _movement_action_review_ids(actions)
    reviews = _load_reviews(
        db,
        gym_id=gym_id,
        allowed_sources=allowed_sources,
        status_filter=status_filter,
        exclude_approved_review_ids=movement_action_review_ids,
        limit=limit,
    )

    member_ids = {action.member_id for action in actions if action.member_id}
    member_ids.update(review.member_id for review in reviews if review.member_id)
    lead_ids = {action.lead_id for action in actions if action.lead_id}
    members = _members_by_id(db, gym_id=gym_id, member_ids=member_ids)
    leads = _leads_by_id(db, gym_id=gym_id, lead_ids=lead_ids)

    items = [
        _item_from_action(action, members=members, leads=leads)
        for action in actions
        if _source_from_action(action) in allowed_sources
    ]
    items.extend(_item_from_review(review, members=members) for review in reviews)
    items = [_item for _item in items if _matches_query(_item, q)]
    items.sort(key=lambda item: (_status_rank(item.status), item.created_at), reverse=True)
    items = items[:limit]
    return AiReviewCenterListOut(items=items, metrics=_build_metrics(items), generated_at=_now())


def prepare_review_center_item_in_kommo(
    db: Session,
    *,
    gym_id: UUID,
    user_role: RoleEnum,
    reviewer_user_id: UUID | None = None,
    source_type: str,
    source_id: UUID,
    flush: bool = True,
) -> AiReviewCenterActionOut:
    _ensure_source_allowed(user_role, source_type)
    if source_type == "ai_service_agent":
        result = prepare_ai_service_agent_draft_in_kommo(db, gym_id=gym_id, draft_id=source_id, flush=False)
        item = _item_from_action(_get_action_or_404(db, gym_id=gym_id, action_id=result.draft.id), members=_members_by_id(db, gym_id=gym_id, member_ids={result.draft.member_id} if result.draft.member_id else set()), leads={})
        detail = result.detail
        contact_id, lead_id, task_id = result.kommo_contact_id, result.kommo_lead_id, result.kommo_task_id
    elif source_type == "personal_ai":
        result = prepare_personal_ai_draft_in_kommo(db, gym_id=gym_id, draft_id=source_id, flush=False)
        item = _item_from_action(_get_action_or_404(db, gym_id=gym_id, action_id=result.draft.id), members=_members_by_id(db, gym_id=gym_id, member_ids={result.draft.member_id} if result.draft.member_id else set()), leads={})
        detail = result.detail
        contact_id, lead_id, task_id = result.kommo_contact_id, result.kommo_lead_id, result.kommo_task_id
    elif source_type == "student_personal_ai":
        result = prepare_student_personal_ai_draft_in_kommo(db, gym_id=gym_id, draft_id=source_id, flush=False)
        item = _item_from_action(_get_action_or_404(db, gym_id=gym_id, action_id=result.draft.id), members=_members_by_id(db, gym_id=gym_id, member_ids={result.draft.member_id} if result.draft.member_id else set()), leads={})
        detail = result.detail
        contact_id, lead_id, task_id = result.kommo_contact_id, result.kommo_lead_id, result.kommo_task_id
    elif source_type in {"movement_video", "movement_video_review"}:
        review_id = source_id
        if source_type == "movement_video":
            action = _get_action_or_404(db, gym_id=gym_id, action_id=source_id)
            review_id = _review_id_from_action(action)
        result = prepare_movement_video_review_in_kommo(db, gym_id=gym_id, review_id=review_id, flush=False)
        members = _members_by_id(db, gym_id=gym_id, member_ids={result.review.member_id})
        item = _item_from_review(_get_review_or_404(db, gym_id=gym_id, review_id=result.review.id), members=members)
        detail = result.detail
        contact_id, lead_id, task_id = result.kommo_contact_id, result.kommo_lead_id, result.kommo_task_id
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Origem de revisao IA nao encontrada.")

    _record_feedback_if_missing(
        db,
        gym_id=gym_id,
        source_type=source_type,
        source_id=source_id,
        reviewer_user_id=reviewer_user_id,
        decision="approved",
        reason="Preparado na Kommo pela Central de Revisao IA.",
    )
    if not (source_type == "movement_video" and item.source_type == "movement_video_review"):
        item = _item_for_source(db, gym_id=gym_id, source_type=source_type, source_id=source_id, fallback_item=item)

    if flush:
        db.flush()
    return AiReviewCenterActionOut(
        item=item,
        detail=detail,
        kommo_contact_id=contact_id,
        kommo_lead_id=lead_id,
        kommo_task_id=task_id,
    )


def record_review_center_feedback(
    db: Session,
    *,
    gym_id: UUID,
    user_role: RoleEnum,
    reviewer_user_id: UUID,
    source_type: str,
    source_id: UUID,
    payload: AiReviewCenterFeedbackInput,
    flush: bool = True,
) -> AiReviewCenterActionOut:
    _ensure_source_allowed(user_role, source_type)
    _validate_feedback_payload(payload)

    if payload.decision == "rejected":
        reject_review_center_item(
            db,
            gym_id=gym_id,
            user_role=user_role,
            source_type=source_type,
            source_id=source_id,
            reason=(payload.reason or "Rascunho rejeitado pela equipe.").strip(),
            flush=False,
        )

    target_kind, target = _get_target_for_source(db, gym_id=gym_id, source_type=source_type, source_id=source_id)
    _apply_feedback_to_target(
        target_kind=target_kind,
        target=target,
        decision=payload.decision,
        reason=payload.reason,
        edited_reply=payload.edited_reply,
        reviewer_user_id=reviewer_user_id,
        overwrite=True,
    )
    db.add(target)
    record_event(
        db,
        gym_id=gym_id,
        event_type="ai_review_center_feedback_recorded",
        source="ai_review_center",
        member_id=getattr(target, "member_id", None),
        lead_id=getattr(target, "lead_id", None),
        autopilot_action_id=target.id if target_kind == "action" else None,
        metadata={
            "source_type": source_type,
            "decision": payload.decision,
            "has_edit": bool(payload.edited_reply),
            "reason": payload.reason,
        },
        flush=False,
    )
    if flush:
        db.flush()
    return AiReviewCenterActionOut(
        item=_item_for_source(db, gym_id=gym_id, source_type=source_type, source_id=source_id),
        detail=_feedback_detail(payload.decision),
    )


def reject_review_center_item(
    db: Session,
    *,
    gym_id: UUID,
    user_role: RoleEnum,
    source_type: str,
    source_id: UUID,
    reason: str,
    flush: bool = True,
) -> AiReviewCenterActionOut:
    _ensure_source_allowed(user_role, source_type)
    if source_type == "student_personal_ai":
        result = reject_student_personal_ai_draft(db, gym_id=gym_id, draft_id=source_id, reason=reason, flush=False)
        action = _get_action_or_404(db, gym_id=gym_id, action_id=result.id)
        item = _item_from_action(action, members=_members_by_id(db, gym_id=gym_id, member_ids={result.member_id} if result.member_id else set()), leads={})
    elif source_type == "movement_video_review":
        result = reject_movement_video_review(
            db,
            gym_id=gym_id,
            review_id=source_id,
            payload=MovementVideoRejectInput(reason=reason),
            flush=False,
        )
        item = _item_from_review(
            _get_review_or_404(db, gym_id=gym_id, review_id=result.id),
            members=_members_by_id(db, gym_id=gym_id, member_ids={result.member_id}),
        )
    else:
        action = _get_action_or_404(db, gym_id=gym_id, action_id=source_id)
        if _source_from_action(action) != source_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de revisao IA nao encontrado.")
        metadata = dict(action.metadata_json or {})
        metadata["review_center_state"] = "rejected"
        metadata["review_center_rejection_reason"] = reason
        metadata["rejected_at"] = _now().isoformat()
        action.status = "cancelled"
        action.outcome = "rejected"
        action.failure_reason = reason
        action.completed_at = _now()
        action.metadata_json = metadata
        db.add(action)
        record_event(
            db,
            gym_id=gym_id,
            event_type="ai_review_center_item_rejected",
            source="ai_review_center",
            member_id=action.member_id,
            lead_id=action.lead_id,
            autopilot_action_id=action.id,
            metadata={"source_type": source_type, "reason": reason},
            flush=False,
        )
        item = _item_from_action(
            action,
            members=_members_by_id(db, gym_id=gym_id, member_ids={action.member_id} if action.member_id else set()),
            leads=_leads_by_id(db, gym_id=gym_id, lead_ids={action.lead_id} if action.lead_id else set()),
        )

    if flush:
        db.flush()
    return AiReviewCenterActionOut(item=item, detail="Item rejeitado na Central de Revisao IA.")


def _load_actions(
    db: Session,
    *,
    gym_id: UUID,
    allowed_sources: set[str],
    status_filter: str | None,
    limit: int,
) -> list[AutopilotAction]:
    action_types = [action_type for action_type, source in ACTION_SOURCE_BY_TYPE.items() if source in allowed_sources]
    if not action_types:
        return []
    query = select(AutopilotAction).where(AutopilotAction.gym_id == gym_id, AutopilotAction.action_type.in_(action_types))
    if status_filter and status_filter != "all":
        query = query.where(AutopilotAction.status == status_filter)
    else:
        query = query.where(AutopilotAction.status.in_(DEFAULT_ACTION_STATUSES))
    return list(db.scalars(query.order_by(AutopilotAction.created_at.desc()).limit(limit)).all())


def _load_reviews(
    db: Session,
    *,
    gym_id: UUID,
    allowed_sources: set[str],
    status_filter: str | None,
    exclude_approved_review_ids: set[UUID],
    limit: int,
) -> list[MovementVideoReview]:
    if "movement_video_review" not in allowed_sources:
        return []
    query = select(MovementVideoReview).where(MovementVideoReview.gym_id == gym_id)
    if status_filter and status_filter != "all":
        query = query.where(MovementVideoReview.status == status_filter)
    else:
        query = query.where(MovementVideoReview.status.in_(DEFAULT_REVIEW_STATUSES))
    reviews = db.scalars(query.order_by(MovementVideoReview.created_at.desc()).limit(limit)).all()
    return [review for review in reviews if not (review.status == "approved" and review.id in exclude_approved_review_ids)]


def _item_from_action(
    action: AutopilotAction,
    *,
    members: dict[UUID, Member],
    leads: dict[UUID, Lead],
) -> AiReviewCenterItemOut:
    source_type = _source_from_action(action)
    metadata = dict(action.metadata_json or {})
    feedback = _feedback_from_metadata(metadata)
    subject_name = _subject_name(action.member_id, action.lead_id, members=members, leads=leads)
    blocked_reasons = list(metadata.get("blocked_reasons") or [])
    evidence = list(metadata.get("evidence") or [])
    status_value = action.status

    if source_type == "ai_service_agent":
        draft = serialize_ai_service_agent_draft(action)
        intent = draft.intent
        sensitivity = draft.sensitivity
        summary = draft.summary
        received_message = draft.received_message
        next_action = draft.next_action
        recommended_owner = draft.recommended_owner_role
    elif source_type == "personal_ai":
        draft = serialize_personal_ai_draft(action)
        intent = draft.intent
        sensitivity = draft.sensitivity
        summary = draft.summary
        received_message = draft.question
        next_action = draft.next_action
        recommended_owner = draft.recommended_owner_role
    elif source_type == "student_personal_ai":
        draft = serialize_student_personal_ai_draft(action)
        intent = draft.intent
        sensitivity = draft.sensitivity
        summary = draft.summary
        received_message = draft.received_message
        next_action = draft.next_action
        recommended_owner = draft.recommended_owner_role
    else:
        intent = str(metadata.get("exercise_name") or "movement_video")
        sensitivity = "normal"
        summary = str(metadata.get("summary") or "Feedback de video aprovado para revisao/envio supervisionado.")
        received_message = metadata.get("exercise_name")
        next_action = "Preparar feedback tecnico na Kommo."
        recommended_owner = "coach"

    return AiReviewCenterItemOut(
        source_type=source_type,  # type: ignore[arg-type]
        source_id=action.id,
        status=status_value,
        domain=action.domain,
        channel=action.channel,
        subject_name=subject_name,
        member_id=action.member_id,
        lead_id=action.lead_id,
        intent=intent,
        sensitivity=sensitivity,
        summary=summary,
        received_message=received_message,
        draft_reply=action.message_body or metadata.get("draft_reply"),
        next_action=next_action,
        recommended_owner_role=recommended_owner,
        blocked_reasons=blocked_reasons,
        evidence=evidence,
        badges=_badges(source_type, status_value, blocked_reasons),
        context_path=_context_path(action.member_id),
        kommo_contact_id=metadata.get("kommo_contact_id"),
        kommo_lead_id=metadata.get("kommo_lead_id"),
        kommo_task_id=metadata.get("kommo_task_id"),
        review_decision=feedback.get("decision"),
        reviewed_at=_parse_datetime(feedback.get("reviewed_at")),
        reviewed_by_user_id=_parse_uuid(feedback.get("reviewed_by_user_id")),
        review_notes=feedback.get("reason"),
        review_latency_minutes=_review_latency_minutes(action.created_at, feedback.get("reviewed_at")),
        can_prepare_kommo=status_value in {AI_SERVICE_AGENT_DRAFT_READY, PERSONAL_AI_DRAFT_READY, STUDENT_PERSONAL_AI_DRAFT_READY},
        can_reject=status_value not in TERMINAL_STATUSES,
        metadata=metadata,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


def _item_from_review(review: MovementVideoReview, *, members: dict[UUID, Member]) -> AiReviewCenterItemOut:
    metadata = dict(review.metadata_json or {})
    feedback = _feedback_from_metadata(metadata)
    blocked_reasons = list(review.blocked_reasons or [])
    summary = review.summary or metadata.get("summary") or "Video aguardando revisao supervisionada."
    draft_reply = review.coach_feedback or review.suggested_feedback
    return AiReviewCenterItemOut(
        source_type="movement_video_review",
        source_id=review.id,
        status=review.status,
        domain="trainer",
        channel="kommo",
        subject_name=_subject_name(review.member_id, None, members=members, leads={}),
        member_id=review.member_id,
        lead_id=None,
        intent=review.exercise_name,
        sensitivity=review.safety_level,
        summary=summary,
        received_message=metadata.get("caption") or metadata.get("notes"),
        draft_reply=draft_reply,
        next_action=_next_action_for_review(review),
        recommended_owner_role="coach",
        blocked_reasons=blocked_reasons,
        evidence=["movement_video", review.analysis_status],
        badges=_badges("movement_video_review", review.status, blocked_reasons),
        context_path=_context_path(review.member_id),
        kommo_contact_id=metadata.get("kommo_contact_id"),
        kommo_lead_id=metadata.get("kommo_lead_id"),
        kommo_task_id=metadata.get("kommo_task_id"),
        review_decision=feedback.get("decision"),
        reviewed_at=_parse_datetime(feedback.get("reviewed_at")),
        reviewed_by_user_id=_parse_uuid(feedback.get("reviewed_by_user_id")),
        review_notes=feedback.get("reason"),
        review_latency_minutes=_review_latency_minutes(review.created_at, feedback.get("reviewed_at")),
        can_prepare_kommo=review.status == "approved" and bool(review.coach_feedback),
        can_reject=review.status not in {"rejected"},
        metadata=metadata,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _build_metrics(items: list[AiReviewCenterItemOut]) -> AiReviewCenterMetricsOut:
    metrics = AiReviewCenterMetricsOut(total=len(items))
    review_minutes: list[int] = []
    for item in items:
        metrics.by_source[item.source_type] = metrics.by_source.get(item.source_type, 0) + 1
        metrics.by_status[item.status] = metrics.by_status.get(item.status, 0) + 1
        if item.status in READY_STATUSES:
            metrics.ready += 1
        if item.status == "blocked":
            metrics.blocked += 1
        if item.status == "escalated":
            metrics.escalated += 1
        if item.status == "awaiting_outcome":
            metrics.awaiting_outcome += 1
        if item.kommo_task_id:
            metrics.prepared += 1
        if item.review_decision:
            metrics.reviewed += 1
            if item.review_decision == "approved":
                metrics.approved += 1
            if item.review_decision == "edited":
                metrics.edited += 1
            if item.review_decision == "rejected":
                metrics.rejected += 1
            if item.review_decision == "escalated":
                metrics.review_escalated += 1
            if item.review_latency_minutes is not None:
                review_minutes.append(item.review_latency_minutes)
    if metrics.reviewed:
        metrics.utilization_rate = round((metrics.approved + metrics.edited) / metrics.reviewed, 4)
    if review_minutes:
        metrics.average_review_minutes = round(sum(review_minutes) / len(review_minutes))
    return metrics


def _members_by_id(db: Session, *, gym_id: UUID, member_ids: set[UUID | None]) -> dict[UUID, Member]:
    valid_ids = {member_id for member_id in member_ids if member_id}
    if not valid_ids:
        return {}
    members = db.scalars(select(Member).where(Member.gym_id == gym_id, Member.id.in_(valid_ids))).all()
    return {member.id: member for member in members}


def _leads_by_id(db: Session, *, gym_id: UUID, lead_ids: set[UUID | None]) -> dict[UUID, Lead]:
    valid_ids = {lead_id for lead_id in lead_ids if lead_id}
    if not valid_ids:
        return {}
    leads = db.scalars(select(Lead).where(Lead.gym_id == gym_id, Lead.id.in_(valid_ids))).all()
    return {lead.id: lead for lead in leads}


def _get_action_or_404(db: Session, *, gym_id: UUID, action_id: UUID) -> AutopilotAction:
    action = db.scalar(select(AutopilotAction).where(AutopilotAction.gym_id == gym_id, AutopilotAction.id == action_id))
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de revisao IA nao encontrado.")
    return action


def _get_review_or_404(db: Session, *, gym_id: UUID, review_id: UUID) -> MovementVideoReview:
    review = db.scalar(select(MovementVideoReview).where(MovementVideoReview.gym_id == gym_id, MovementVideoReview.id == review_id))
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review de video nao encontrado.")
    return review


def _get_target_for_source(
    db: Session,
    *,
    gym_id: UUID,
    source_type: str,
    source_id: UUID,
) -> tuple[str, AutopilotAction | MovementVideoReview]:
    if source_type == "movement_video_review":
        return "review", _get_review_or_404(db, gym_id=gym_id, review_id=source_id)
    action = _get_action_or_404(db, gym_id=gym_id, action_id=source_id)
    if _source_from_action(action) != source_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de revisao IA nao encontrado.")
    return "action", action


def _item_for_source(
    db: Session,
    *,
    gym_id: UUID,
    source_type: str,
    source_id: UUID,
    fallback_item: AiReviewCenterItemOut | None = None,
) -> AiReviewCenterItemOut:
    try:
        target_kind, target = _get_target_for_source(db, gym_id=gym_id, source_type=source_type, source_id=source_id)
    except HTTPException:
        if fallback_item is not None:
            return fallback_item
        raise
    if target_kind == "review":
        review = target
        assert isinstance(review, MovementVideoReview)
        return _item_from_review(
            review,
            members=_members_by_id(db, gym_id=gym_id, member_ids={review.member_id}),
        )
    action = target
    assert isinstance(action, AutopilotAction)
    return _item_from_action(
        action,
        members=_members_by_id(db, gym_id=gym_id, member_ids={action.member_id} if action.member_id else set()),
        leads=_leads_by_id(db, gym_id=gym_id, lead_ids={action.lead_id} if action.lead_id else set()),
    )


def _validate_feedback_payload(payload: AiReviewCenterFeedbackInput) -> None:
    reason = (payload.reason or "").strip()
    edited_reply = (payload.edited_reply or "").strip()
    if payload.decision in {"rejected", "escalated"} and len(reason) < 3:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe um motivo para rejeitar ou escalar.")
    if payload.decision == "edited" and len(edited_reply) < 3:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe o rascunho editado.")


def _record_feedback_if_missing(
    db: Session,
    *,
    gym_id: UUID,
    source_type: str,
    source_id: UUID,
    reviewer_user_id: UUID | None,
    decision: str,
    reason: str,
) -> None:
    target_kind, target = _get_target_for_source(db, gym_id=gym_id, source_type=source_type, source_id=source_id)
    metadata = dict(getattr(target, "metadata_json", None) or {})
    if metadata.get("review_center_feedback"):
        return
    _apply_feedback_to_target(
        target_kind=target_kind,
        target=target,
        decision=decision,
        reason=reason,
        edited_reply=None,
        reviewer_user_id=reviewer_user_id,
        overwrite=False,
    )
    db.add(target)
    record_event(
        db,
        gym_id=gym_id,
        event_type="ai_review_center_feedback_recorded",
        source="ai_review_center",
        member_id=getattr(target, "member_id", None),
        lead_id=getattr(target, "lead_id", None),
        autopilot_action_id=target.id if target_kind == "action" else None,
        metadata={"source_type": source_type, "decision": decision, "reason": reason, "implicit": True},
        flush=False,
    )


def _apply_feedback_to_target(
    *,
    target_kind: str,
    target: AutopilotAction | MovementVideoReview,
    decision: str,
    reason: str | None,
    edited_reply: str | None,
    reviewer_user_id: UUID | None,
    overwrite: bool,
) -> None:
    metadata = dict(target.metadata_json or {})
    if metadata.get("review_center_feedback") and not overwrite:
        return
    feedback = {
        "decision": decision,
        "reason": (reason or "").strip() or None,
        "edited_reply": (edited_reply or "").strip() or None,
        "reviewed_at": _now().isoformat(),
        "reviewed_by_user_id": str(reviewer_user_id) if reviewer_user_id else None,
    }
    metadata["review_center_feedback"] = feedback
    metadata["review_center_state"] = decision
    if feedback["edited_reply"]:
        metadata["draft_reply"] = feedback["edited_reply"]
        if target_kind == "action":
            assert isinstance(target, AutopilotAction)
            target.message_body = feedback["edited_reply"]
        else:
            assert isinstance(target, MovementVideoReview)
            target.coach_feedback = feedback["edited_reply"]
    if decision == "escalated":
        metadata["escalated_by_review_center"] = True
        if target_kind == "action":
            assert isinstance(target, AutopilotAction)
            target.status = "escalated"
            target.escalation_reason = feedback["reason"] or "Escalado pela Central de Revisao IA."
        else:
            assert isinstance(target, MovementVideoReview)
            blocked_reasons = list(target.blocked_reasons or [])
            if "reviewer_escalated" not in blocked_reasons:
                blocked_reasons.append("reviewer_escalated")
            target.blocked_reasons = blocked_reasons
    target.metadata_json = metadata


def _feedback_from_metadata(metadata: dict) -> dict:
    feedback = metadata.get("review_center_feedback")
    return feedback if isinstance(feedback, dict) else {}


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _parse_uuid(value: object) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _review_latency_minutes(created_at: datetime, reviewed_at: object) -> int | None:
    reviewed = _parse_datetime(reviewed_at)
    if reviewed is None:
        return None
    created = created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if reviewed.tzinfo is None:
        reviewed = reviewed.replace(tzinfo=timezone.utc)
    return max(0, round((reviewed - created).total_seconds() / 60))


def _feedback_detail(decision: str) -> str:
    return {
        "approved": "Rascunho aprovado pela Central de Revisao IA.",
        "edited": "Edicao do rascunho registrada.",
        "rejected": "Item rejeitado na Central de Revisao IA.",
        "escalated": "Item escalado para decisao humana.",
    }.get(decision, "Feedback registrado.")


def _source_from_action(action: AutopilotAction) -> str:
    source = ACTION_SOURCE_BY_TYPE.get(action.action_type)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Origem de revisao IA nao encontrada.")
    return source


def _review_id_from_action(action: AutopilotAction) -> UUID:
    raw = (action.metadata_json or {}).get("movement_video_review_id")
    if not raw:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Rascunho de video sem review vinculado.")
    return UUID(str(raw))


def _movement_action_review_ids(actions: list[AutopilotAction]) -> set[UUID]:
    ids: set[UUID] = set()
    for action in actions:
        if action.action_type != MOVEMENT_VIDEO_ACTION_TYPE:
            continue
        try:
            ids.add(_review_id_from_action(action))
        except Exception:
            continue
    return ids


def _allowed_sources_for_role(role: RoleEnum) -> set[str]:
    if role in {RoleEnum.OWNER, RoleEnum.MANAGER}:
        return {"ai_service_agent", "personal_ai", "student_personal_ai", "movement_video", "movement_video_review"}
    if role == RoleEnum.TRAINER:
        return {"personal_ai", "student_personal_ai", "movement_video", "movement_video_review"}
    if role == RoleEnum.RECEPTIONIST:
        return {"ai_service_agent", "student_personal_ai"}
    if role == RoleEnum.SALESPERSON:
        return {"ai_service_agent"}
    return set()


def _ensure_source_allowed(role: RoleEnum, source_type: str) -> None:
    if source_type not in _allowed_sources_for_role(role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissao para revisar esta origem de IA.")


def _subject_name(
    member_id: UUID | None,
    lead_id: UUID | None,
    *,
    members: dict[UUID, Member],
    leads: dict[UUID, Lead],
) -> str:
    if member_id and member_id in members:
        return members[member_id].full_name
    if lead_id and lead_id in leads:
        return leads[lead_id].full_name
    return "Aluno ou lead"


def _context_path(member_id: UUID | None) -> str | None:
    if not member_id:
        return None
    return f"/assessments/members/{member_id}"


def _badges(source_type: str, status_value: str, blocked_reasons: list[str]) -> list[str]:
    labels = [source_type.replace("_", " ").upper(), status_value.replace("_", " ").upper()]
    if blocked_reasons:
        labels.append("BLOQUEIO")
    if source_type in {"personal_ai", "movement_video", "movement_video_review"}:
        labels.append("COACH REVIEW")
    return labels


def _next_action_for_review(review: MovementVideoReview) -> str:
    if review.status == "approved":
        return "Preparar feedback aprovado na Kommo."
    if review.status == "blocked":
        return "Resolver bloqueios antes de responder ao aluno."
    if review.status == "needs_coach_review":
        return "Professor revisa o video e aprova ou rejeita feedback."
    return "Analisar video antes de responder."


def _matches_query(item: AiReviewCenterItemOut, q: str | None) -> bool:
    if not q:
        return True
    needle = q.strip().lower()
    if not needle:
        return True
    haystack = " ".join(
        [
            item.subject_name,
            item.intent or "",
            item.summary or "",
            item.received_message or "",
            item.draft_reply or "",
            item.next_action or "",
        ]
    ).lower()
    return needle in haystack


def _status_rank(status_value: str) -> int:
    return {
        "blocked": 5,
        "escalated": 5,
        "draft_ready": 4,
        "approved": 4,
        "needs_coach_review": 3,
        "pending_review": 3,
        "failed": 2,
        "awaiting_outcome": 1,
    }.get(status_value, 0)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)
