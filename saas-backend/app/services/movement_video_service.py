from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutopilotAction, Member, MovementVideoReview
from app.schemas.movement_video import (
    MovementVideoAiSettingsOut,
    MovementVideoAiSettingsUpdate,
    MovementVideoApproveInput,
    MovementVideoAnalyzeInput,
    MovementVideoKommoPrepareOut,
    MovementVideoRejectInput,
    MovementVideoReviewCreate,
    MovementVideoReviewOut,
)
from app.services.autopilot_event_service import record_event
from app.services.autopilot_settings_service import get_or_create_autopilot_settings
from app.services.ai_prompt_registry_service import generate_specialist_text, prompt_metadata
from app.services.compliance_service import current_consent_status_map
from app.services.kommo_service import handoff_member_to_kommo

MOVEMENT_VIDEO_EXTRA_KEY = "movement_video_ai"
MOVEMENT_VIDEO_ACTION_TYPE = "movement_video_feedback_draft"

DEFAULT_MOVEMENT_VIDEO_AI_SETTINGS = {
    "enabled": False,
    "mode": "coach_review",
    "auto_send_enabled": False,
    "require_image_consent": True,
    "store_original_video": False,
    "retention_days": 30,
    "max_video_mb": 100,
    "max_duration_seconds": 120,
    "allowed_media_types": ["video/mp4", "video/quicktime", "video/webm"],
}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def get_movement_video_ai_settings(db: Session, *, gym_id: UUID) -> MovementVideoAiSettingsOut:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    payload = _merge_settings((settings.extra_data or {}).get(MOVEMENT_VIDEO_EXTRA_KEY))
    return MovementVideoAiSettingsOut(**payload)


def update_movement_video_ai_settings(
    db: Session,
    *,
    gym_id: UUID,
    payload: MovementVideoAiSettingsUpdate,
) -> MovementVideoAiSettingsOut:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    current = _merge_settings((settings.extra_data or {}).get(MOVEMENT_VIDEO_EXTRA_KEY))
    updates = payload.model_dump(exclude_unset=True)
    updates["mode"] = "coach_review"
    updates["auto_send_enabled"] = False
    current.update(updates)
    current = _merge_settings(current)

    extra = dict(settings.extra_data or {})
    extra[MOVEMENT_VIDEO_EXTRA_KEY] = current
    settings.extra_data = extra
    db.add(settings)
    db.flush()
    return MovementVideoAiSettingsOut(**current)


def create_movement_video_review(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    payload: MovementVideoReviewCreate,
    trainer_user_id: UUID | None = None,
    flush: bool = True,
) -> MovementVideoReviewOut:
    member = _get_member_or_404(db, gym_id=gym_id, member_id=member_id)
    settings = get_movement_video_ai_settings(db, gym_id=gym_id)
    blocked_reasons = _initial_blocked_reasons(db, gym_id=gym_id, member_id=member.id, settings=settings)
    blocked_reasons.extend(_video_validation_reasons(payload, settings=settings))
    blocked_reasons = sorted(set(blocked_reasons))
    is_blocked = bool(blocked_reasons)

    metadata = {
        "notes": payload.notes,
        "mode": "coach_review",
        "auto_send_enabled": False,
        "retention_days": settings.retention_days,
    }
    now = _now()
    review = MovementVideoReview(
        id=uuid.uuid4(),
        gym_id=gym_id,
        member_id=member.id,
        trainer_user_id=trainer_user_id,
        exercise_name=payload.exercise_name.strip(),
        video_asset_url=str(payload.video_asset_url) if payload.video_asset_url else None,
        video_asset_hash=payload.video_asset_hash,
        media_type=payload.media_type,
        file_size_bytes=payload.file_size_bytes,
        duration_seconds=payload.duration_seconds,
        original_video_stored=False,
        status="blocked" if is_blocked else "pending_review",
        analysis_status="blocked" if is_blocked else "not_started",
        safety_level="blocked" if is_blocked else "coach_review",
        summary="Review bloqueado por guardrails antes da analise." if is_blocked else None,
        detected_points=[],
        suggested_feedback=None,
        blocked_reasons=blocked_reasons,
        metadata_json=metadata,
        created_at=now,
        updated_at=now,
    )
    db.add(review)
    db.flush()
    record_event(
        db,
        gym_id=gym_id,
        event_type="movement_video_review_created",
        source="movement_video",
        member_id=member.id,
        metadata={
            "review_id": str(review.id),
            "status": review.status,
            "analysis_status": review.analysis_status,
            "blocked_reasons": blocked_reasons,
        },
        flush=flush,
    )
    return serialize_movement_video_review(review)


def list_movement_video_reviews(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    limit: int = 50,
) -> list[MovementVideoReviewOut]:
    _get_member_or_404(db, gym_id=gym_id, member_id=member_id)
    reviews = db.scalars(
        select(MovementVideoReview)
        .where(MovementVideoReview.gym_id == gym_id, MovementVideoReview.member_id == member_id)
        .order_by(MovementVideoReview.created_at.desc())
        .limit(limit)
    ).all()
    return [serialize_movement_video_review(review) for review in reviews]


def analyze_movement_video_review(
    db: Session,
    *,
    gym_id: UUID,
    review_id: UUID,
    payload: MovementVideoAnalyzeInput | None = None,
    flush: bool = True,
) -> MovementVideoReviewOut:
    review = _get_review_or_404(db, gym_id=gym_id, review_id=review_id)
    if review.blocked_reasons:
        review.updated_at = _now()
        review.status = "blocked"
        review.analysis_status = "blocked"
        review.safety_level = "blocked"
        db.add(review)
        if flush:
            db.flush()
        return serialize_movement_video_review(review)

    review.analysis_status = "manual_observation"
    review.status = "needs_coach_review"
    review.safety_level = "coach_review"
    review.updated_at = _now()
    review.summary = (
        "Analise automatica de video ainda nao configurada. O sistema preservou o video como evidencia "
        "e preparou uma revisao supervisionada para o professor."
    )
    detected_points = [
        {
            "label": "Revisao humana obrigatoria",
            "description": "A V1 nao emite veredito tecnico autonomo; o professor deve revisar a execucao no video.",
        },
        {
            "label": "Exercicio declarado",
            "description": f"Exercicio informado: {review.exercise_name}.",
        },
    ]
    if payload and payload.coach_observation:
        detected_points.append(
            {
                "label": "Observacao inicial do professor",
                "description": payload.coach_observation,
            }
        )
    review.detected_points = detected_points
    fallback_feedback = (
        f"Revisei sua execucao de {review.exercise_name}. Vou deixar um ponto de atencao tecnico "
        "e, se precisar, ajustamos no proximo treino presencial."
    )
    feedback_result = generate_specialist_text(
        "movement_video_feedback_v1",
        user_prompt=(
            "Prepare um feedback supervisionado para aluno, baseado no video e na observacao do professor.\n"
            f"Exercicio: {review.exercise_name}\n"
            f"Observacao do professor: {(payload.coach_observation if payload else None) or '-'}\n"
            "Nao diga que corrigiu automaticamente. Nao diagnostique dor/lesao. Deve ser aprovado pelo professor."
        ),
        fallback_text=fallback_feedback,
        max_output_chars=900,
    )
    review.suggested_feedback = feedback_result.text
    metadata = dict(review.metadata_json or {})
    metadata["analysis_mode"] = "manual_observation"
    metadata["coach_review_required"] = True
    metadata["prompt_metadata"] = feedback_result.metadata
    review.metadata_json = metadata
    db.add(review)
    if flush:
        db.flush()
    record_event(
        db,
        gym_id=review.gym_id,
        event_type="movement_video_review_analyzed",
        source="movement_video",
        member_id=review.member_id,
        metadata={"review_id": str(review.id), "analysis_status": review.analysis_status},
        flush=flush,
    )
    return serialize_movement_video_review(review)


def approve_movement_video_review(
    db: Session,
    *,
    gym_id: UUID,
    review_id: UUID,
    payload: MovementVideoApproveInput,
    flush: bool = True,
) -> MovementVideoReviewOut:
    review = _get_review_or_404(db, gym_id=gym_id, review_id=review_id)
    if review.status == "blocked":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review bloqueado por guardrails; nao pode ser aprovado.")
    review.status = "approved"
    review.coach_feedback = payload.coach_feedback
    review.reviewed_at = _now()
    review.updated_at = review.reviewed_at
    metadata = dict(review.metadata_json or {})
    metadata["approved_for_student"] = True
    review.metadata_json = metadata
    db.add(review)

    action = AutopilotAction(
        id=uuid.uuid4(),
        gym_id=review.gym_id,
        policy_key="movement_video_feedback_approved",
        domain="trainer",
        action_type=MOVEMENT_VIDEO_ACTION_TYPE,
        status="draft_ready",
        member_id=review.member_id,
        channel="kommo",
        message_body=review.coach_feedback,
        metadata_json={
            "movement_video_review_id": str(review.id),
            "exercise_name": review.exercise_name,
            "coach_review_required": True,
            "auto_send_enabled": False,
            "prompt_metadata": (review.metadata_json or {}).get("prompt_metadata")
            or prompt_metadata("movement_video_feedback_v1", model="deterministic_fallback", fallback_used=True),
        },
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(action)
    db.flush()
    record_event(
        db,
        gym_id=review.gym_id,
        event_type="movement_video_feedback_approved",
        source="movement_video",
        member_id=review.member_id,
        autopilot_action_id=action.id,
        metadata={"review_id": str(review.id), "action_id": str(action.id)},
        flush=flush,
    )
    return serialize_movement_video_review(review)


def reject_movement_video_review(
    db: Session,
    *,
    gym_id: UUID,
    review_id: UUID,
    payload: MovementVideoRejectInput,
    flush: bool = True,
) -> MovementVideoReviewOut:
    review = _get_review_or_404(db, gym_id=gym_id, review_id=review_id)
    review.status = "rejected"
    review.analysis_status = "rejected"
    review.rejected_at = _now()
    review.updated_at = review.rejected_at
    metadata = dict(review.metadata_json or {})
    metadata["rejection_reason"] = payload.reason
    review.metadata_json = metadata
    review.updated_at = _now()
    db.add(review)
    if flush:
        db.flush()
    record_event(
        db,
        gym_id=review.gym_id,
        event_type="movement_video_review_rejected",
        source="movement_video",
        member_id=review.member_id,
        metadata={"review_id": str(review.id), "reason": payload.reason},
        flush=flush,
    )
    return serialize_movement_video_review(review)


def prepare_movement_video_review_in_kommo(
    db: Session,
    *,
    gym_id: UUID,
    review_id: UUID,
    flush: bool = True,
) -> MovementVideoKommoPrepareOut:
    review = _get_review_or_404(db, gym_id=gym_id, review_id=review_id)
    if review.status != "approved" or not review.coach_feedback:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Aprove o feedback do professor antes de preparar na Kommo.")
    member = _get_member_or_404(db, gym_id=gym_id, member_id=review.member_id)
    result = handoff_member_to_kommo(
        db,
        gym_id=gym_id,
        member=member,
        title=f"Feedback tecnico - {review.exercise_name}",
        summary=review.coach_feedback,
        source="movement_video_feedback",
        ai_gym_profile_url=None,
        due_in_hours=24,
    )
    metadata = dict(review.metadata_json or {})
    metadata.update(
        {
            "kommo_status": result.status,
            "kommo_contact_id": result.contact_id,
            "kommo_lead_id": result.lead_id,
            "kommo_task_id": result.task_id,
            "kommo_detail": result.detail,
        }
    )
    review.metadata_json = metadata
    review.updated_at = _now()
    db.add(review)
    if flush:
        db.flush()
    record_event(
        db,
        gym_id=review.gym_id,
        event_type="movement_video_feedback_prepared_kommo",
        source="movement_video",
        member_id=review.member_id,
        metadata={"review_id": str(review.id), "kommo_status": result.status},
        flush=flush,
    )
    return MovementVideoKommoPrepareOut(
        review=serialize_movement_video_review(review),
        detail=result.detail or "Feedback preparado para Kommo.",
        kommo_contact_id=result.contact_id,
        kommo_lead_id=result.lead_id,
        kommo_task_id=result.task_id,
    )


def serialize_movement_video_review(review: MovementVideoReview) -> MovementVideoReviewOut:
    return MovementVideoReviewOut(
        id=review.id,
        gym_id=review.gym_id,
        member_id=review.member_id,
        trainer_user_id=review.trainer_user_id,
        exercise_name=review.exercise_name,
        video_asset_url=review.video_asset_url,
        video_asset_hash=review.video_asset_hash,
        media_type=review.media_type,
        file_size_bytes=review.file_size_bytes,
        duration_seconds=review.duration_seconds,
        original_video_stored=review.original_video_stored,
        status=review.status,
        analysis_status=review.analysis_status,
        safety_level=review.safety_level,
        summary=review.summary,
        detected_points=list(review.detected_points or []),
        suggested_feedback=review.suggested_feedback,
        coach_feedback=review.coach_feedback,
        blocked_reasons=list(review.blocked_reasons or []),
        metadata_json=dict(review.metadata_json or {}),
        created_at=review.created_at,
        updated_at=review.updated_at,
        reviewed_at=review.reviewed_at,
        rejected_at=review.rejected_at,
    )


def _merge_settings(raw: dict | None) -> dict:
    merged = dict(DEFAULT_MOVEMENT_VIDEO_AI_SETTINGS)
    if isinstance(raw, dict):
        merged.update(raw)
    merged["mode"] = "coach_review"
    merged["auto_send_enabled"] = False
    merged["enabled"] = bool(merged.get("enabled"))
    merged["require_image_consent"] = bool(merged.get("require_image_consent", True))
    merged["store_original_video"] = False
    merged["retention_days"] = max(1, min(int(merged.get("retention_days") or 30), 365))
    merged["max_video_mb"] = max(1, min(int(merged.get("max_video_mb") or 100), 500))
    merged["max_duration_seconds"] = max(5, min(int(merged.get("max_duration_seconds") or 120), 600))
    media_types = merged.get("allowed_media_types") or DEFAULT_MOVEMENT_VIDEO_AI_SETTINGS["allowed_media_types"]
    merged["allowed_media_types"] = sorted({str(item).strip().lower() for item in media_types if str(item).strip()})
    return merged


def _get_member_or_404(db: Session, *, gym_id: UUID, member_id: UUID) -> Member:
    member = db.scalar(
        select(Member).where(
            Member.gym_id == gym_id,
            Member.id == member_id,
            Member.deleted_at.is_(None),
        )
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")
    return member


def _get_review_or_404(db: Session, *, gym_id: UUID, review_id: UUID) -> MovementVideoReview:
    review = db.scalar(select(MovementVideoReview).where(MovementVideoReview.gym_id == gym_id, MovementVideoReview.id == review_id))
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review de video nao encontrado")
    return review


def _initial_blocked_reasons(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    settings: MovementVideoAiSettingsOut,
) -> list[str]:
    reasons: list[str] = []
    if not settings.enabled:
        reasons.append("movement_video_ai_disabled")
    if settings.auto_send_enabled:
        reasons.append("auto_send_not_allowed_v1")
    if settings.require_image_consent:
        consent_map = current_consent_status_map(db, member_id, gym_id=gym_id)
        if consent_map.get("image") is not True:
            reasons.append("missing_image_consent")
    return reasons


def _video_validation_reasons(payload: MovementVideoReviewCreate, *, settings: MovementVideoAiSettingsOut) -> list[str]:
    reasons: list[str] = []
    if not payload.video_asset_url:
        reasons.append("missing_video_reference")
    if payload.media_type and payload.media_type.lower() not in settings.allowed_media_types:
        reasons.append("unsupported_media_type")
    if payload.file_size_bytes and payload.file_size_bytes > settings.max_video_mb * 1024 * 1024:
        reasons.append("video_too_large")
    if payload.duration_seconds and payload.duration_seconds > settings.max_duration_seconds:
        reasons.append("video_too_long")
    return reasons
