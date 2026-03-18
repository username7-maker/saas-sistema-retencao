from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.body_composition import BodyCompositionEvaluation
from app.models.body_composition_sync_attempt import BodyCompositionSyncAttempt
from app.schemas.body_composition import BodyCompositionEvaluationCreate, BodyCompositionEvaluationUpdate
from app.services.body_composition_actuar_sync_service import (
    get_body_composition_evaluation_or_404,
    prepare_body_composition_sync_attempt,
)
from app.services.body_composition_ai_service import generate_body_composition_ai
from app.services.member_service import get_member_or_404


def create_body_composition_evaluation(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    payload: BodyCompositionEvaluationCreate,
) -> tuple[BodyCompositionEvaluation, BodyCompositionSyncAttempt | None]:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    evaluation_data = payload.model_dump()
    evaluation_data["reviewed_manually"] = _resolve_reviewed_manually(payload)
    evaluation = BodyCompositionEvaluation(
        gym_id=gym_id,
        member_id=member_id,
        **evaluation_data,
    )
    db.add(evaluation)
    db.flush()
    _apply_ai_payload(db, member=member, evaluation=evaluation)
    sync_attempt = prepare_body_composition_sync_attempt(db, member=member, evaluation=evaluation)
    db.flush()
    return evaluation, sync_attempt


def list_body_composition_evaluations(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    limit: int = 20,
) -> list[BodyCompositionEvaluation]:
    return list(
        db.scalars(
            select(BodyCompositionEvaluation)
            .where(
                BodyCompositionEvaluation.gym_id == gym_id,
                BodyCompositionEvaluation.member_id == member_id,
            )
            .order_by(BodyCompositionEvaluation.evaluation_date.desc())
            .limit(limit)
        ).all()
    )


def update_body_composition_evaluation(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
    payload: BodyCompositionEvaluationUpdate,
) -> tuple[BodyCompositionEvaluation, BodyCompositionSyncAttempt | None]:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    evaluation = get_body_composition_evaluation_or_404(db, gym_id=gym_id, member_id=member_id, evaluation_id=evaluation_id)

    update_data = payload.model_dump()
    update_data["reviewed_manually"] = _resolve_reviewed_manually(payload)
    for field, value in update_data.items():
        setattr(evaluation, field, value)

    _apply_ai_payload(db, member=member, evaluation=evaluation)
    sync_attempt = prepare_body_composition_sync_attempt(db, member=member, evaluation=evaluation)
    db.flush()
    return evaluation, sync_attempt


def _resolve_reviewed_manually(payload: BodyCompositionEvaluationCreate | BodyCompositionEvaluationUpdate) -> bool:
    source = payload.source
    if source == "manual":
        return True
    if source == "ocr_receipt":
        return bool(payload.reviewed_manually)
    return bool(payload.reviewed_manually)


def _apply_ai_payload(db: Session, *, member, evaluation: BodyCompositionEvaluation) -> None:
    ai_payload = generate_body_composition_ai(db, member=member, evaluation=evaluation)
    evaluation.ai_coach_summary = ai_payload["coach_summary"]
    evaluation.ai_member_friendly_summary = ai_payload["member_friendly_summary"]
    evaluation.ai_risk_flags_json = ai_payload["risk_flags"]
    evaluation.ai_training_focus_json = ai_payload["training_focus"]
    generated_at = ai_payload.get("generated_at")
    if isinstance(generated_at, str):
        from datetime import datetime

        evaluation.ai_generated_at = datetime.fromisoformat(generated_at)
