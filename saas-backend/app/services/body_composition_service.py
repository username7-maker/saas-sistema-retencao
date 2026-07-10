from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.actuar_sync import ActuarSyncJob
from app.models.body_composition import BodyCompositionEvaluation
from app.schemas.body_composition import (
    BodyCompositionEvaluationCreate,
    BodyCompositionEvaluationRead,
    BodyCompositionEvaluationReviewInput,
    BodyCompositionEvaluationUpdate,
)
from app.services.ai_assistant_service import build_body_composition_assistant
from app.services.assessment_service import ensure_body_composition_technical_ladder_tasks
from app.services.body_composition_actuar_sync_service import (
    get_body_composition_evaluation_or_404,
    prepare_body_composition_sync_attempt,
)
from app.services.body_composition_ai_service import generate_body_composition_ai
from app.services.body_composition_anthropometry_service import ANTHROPOMETRY_FIELDS
from app.services.body_composition_report_service import resolve_body_composition_persistence_fields
from app.services.member_service import get_member_or_404

BODY_COMPOSITION_MEASUREMENT_FIELDS = (
    "weight_kg",
    "body_fat_kg",
    "body_fat_percent",
    "waist_hip_ratio",
    "fat_free_mass_kg",
    "inorganic_salt_kg",
    "protein_kg",
    "body_water_kg",
    "lean_mass_kg",
    "muscle_mass_kg",
    "skeletal_muscle_kg",
    "body_water_percent",
    "visceral_fat_level",
    "bmi",
    "basal_metabolic_rate_kcal",
    "target_weight_kg",
    "weight_control_kg",
    "muscle_control_kg",
    "fat_control_kg",
    "total_energy_kcal",
    "physical_age",
    "health_score",
    "body_fat_used_percent",
    "body_fat_bioimpedance_percent",
    "body_fat_anthropometric_percent",
    "body_fat_manual_override_percent",
    *ANTHROPOMETRY_FIELDS,
)


def create_body_composition_evaluation(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    payload: BodyCompositionEvaluationCreate,
    *,
    reviewer_user_id: UUID | None = None,
    sync_actuar: bool = True,
) -> tuple[BodyCompositionEvaluation, ActuarSyncJob | None]:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    previous_evaluation = _find_previous_evaluation(db, gym_id=gym_id, member_id=member_id)
    evaluation_data = resolve_body_composition_persistence_fields(
        payload.model_dump(),
        reviewer_user_id=reviewer_user_id,
        previous_evaluation=previous_evaluation,
    )
    _validate_body_composition_payload(payload)
    evaluation_data["reviewed_manually"] = _resolve_reviewed_manually(payload)
    evaluation = BodyCompositionEvaluation(
        gym_id=gym_id,
        member_id=member_id,
        **evaluation_data,
    )
    db.add(evaluation)
    db.flush()
    _apply_ai_payload(db, member=member, evaluation=evaluation)
    ensure_body_composition_technical_ladder_tasks(
        db,
        member=member,
        evaluation=evaluation,
        reviewer_user_id=reviewer_user_id,
        commit=False,
    )
    sync_attempt = prepare_body_composition_sync_attempt(db, member=member, evaluation=evaluation) if sync_actuar else None
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
    *,
    reviewer_user_id: UUID | None = None,
    sync_actuar: bool = True,
) -> tuple[BodyCompositionEvaluation, ActuarSyncJob | None]:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    evaluation = get_body_composition_evaluation_or_404(db, gym_id=gym_id, member_id=member_id, evaluation_id=evaluation_id)

    previous_evaluation = _find_previous_evaluation(db, gym_id=gym_id, member_id=member_id, exclude_evaluation_id=evaluation_id)
    payload_values = payload.model_dump()
    if payload.source == "ocr_receipt":
        payload_values = _preserve_existing_anthropometry_for_ocr_update(payload_values, evaluation)
    update_data = resolve_body_composition_persistence_fields(
        payload_values,
        reviewer_user_id=reviewer_user_id,
        previous_evaluation=previous_evaluation,
    )
    _validate_body_composition_payload(payload)
    update_data["reviewed_manually"] = _resolve_reviewed_manually(payload)
    for field, value in update_data.items():
        setattr(evaluation, field, value)

    _apply_ai_payload(db, member=member, evaluation=evaluation)
    ensure_body_composition_technical_ladder_tasks(
        db,
        member=member,
        evaluation=evaluation,
        reviewer_user_id=reviewer_user_id,
        commit=False,
    )
    sync_attempt = prepare_body_composition_sync_attempt(db, member=member, evaluation=evaluation) if sync_actuar else None
    db.flush()
    return evaluation, sync_attempt


def review_body_composition_evaluation(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
    payload: BodyCompositionEvaluationReviewInput,
    *,
    reviewer_user_id: UUID,
    sync_actuar: bool = True,
) -> tuple[BodyCompositionEvaluation, ActuarSyncJob | None]:
    review_payload = BodyCompositionEvaluationUpdate.model_validate(
        payload.model_dump() | {"reviewed_manually": True, "needs_review": False}
    )
    return update_body_composition_evaluation(
        db,
        gym_id,
        member_id,
        evaluation_id,
        review_payload,
        reviewer_user_id=reviewer_user_id,
        sync_actuar=sync_actuar,
    )


def serialize_body_composition_evaluation(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    evaluation: BodyCompositionEvaluation,
) -> BodyCompositionEvaluationRead:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    previous_evaluation = db.scalar(
        select(BodyCompositionEvaluation)
        .where(
            BodyCompositionEvaluation.member_id == member_id,
            BodyCompositionEvaluation.id != evaluation.id,
        )
        .order_by(desc(BodyCompositionEvaluation.evaluation_date), desc(BodyCompositionEvaluation.created_at))
        .limit(1)
    )
    payload = BodyCompositionEvaluationRead.model_validate(evaluation)
    return payload.model_copy(
        update={"assistant": build_body_composition_assistant(member, evaluation, previous_evaluation)}
    )


def serialize_body_composition_evaluations(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    evaluations: list[BodyCompositionEvaluation],
) -> list[BodyCompositionEvaluationRead]:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    serialized: list[BodyCompositionEvaluationRead] = []
    for index, evaluation in enumerate(evaluations):
        previous_evaluation = evaluations[index + 1] if index + 1 < len(evaluations) else None
        payload = BodyCompositionEvaluationRead.model_validate(evaluation)
        serialized.append(
            payload.model_copy(
                update={"assistant": build_body_composition_assistant(member, evaluation, previous_evaluation)}
            )
        )
    return serialized


def _resolve_reviewed_manually(payload: BodyCompositionEvaluationCreate | BodyCompositionEvaluationUpdate) -> bool:
    source = payload.source
    if source == "manual":
        return True
    if source == "ocr_receipt":
        return bool(payload.reviewed_manually)
    return bool(payload.reviewed_manually)


def _preserve_existing_anthropometry_for_ocr_update(
    values: dict,
    evaluation: BodyCompositionEvaluation,
) -> dict:
    """Merge stored anthropometry into an OCR update so bioimpedance cannot erase it."""
    merged = dict(values)
    preserved_fields = (
        "age_years",
        "sex",
        "height_cm",
        "weight_kg",
        *ANTHROPOMETRY_FIELDS,
        "anthropometry_notes",
        "measurement_protocol",
        "preferred_body_fat_source",
        "body_fat_manual_override_percent",
        "body_fat_manual_review_completed",
        "anthropometry_review_completed",
    )
    for field in preserved_fields:
        incoming = merged.get(field)
        stored = getattr(evaluation, field, None)
        is_empty = incoming is None or incoming == "" or (isinstance(incoming, bool) and not incoming)
        if is_empty and stored is not None:
            merged[field] = stored
    return merged


def _apply_ai_payload(db: Session, *, member, evaluation: BodyCompositionEvaluation) -> None:
    ai_payload = generate_body_composition_ai(db, member=member, evaluation=evaluation)
    evaluation.ai_coach_summary = ai_payload["coach_summary"]
    evaluation.ai_member_friendly_summary = ai_payload["member_friendly_summary"]
    evaluation.ai_risk_flags_json = ai_payload["risk_flags"]
    evaluation.ai_training_focus_json = ai_payload.get("training_focus")
    generated_at = ai_payload.get("generated_at")
    if isinstance(generated_at, str):
        from datetime import datetime

        evaluation.ai_generated_at = datetime.fromisoformat(generated_at)


def _find_previous_evaluation(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    exclude_evaluation_id: UUID | None = None,
) -> BodyCompositionEvaluation | None:
    statement = (
        select(BodyCompositionEvaluation)
        .where(
            BodyCompositionEvaluation.gym_id == gym_id,
            BodyCompositionEvaluation.member_id == member_id,
        )
        .order_by(desc(BodyCompositionEvaluation.evaluation_date), desc(BodyCompositionEvaluation.created_at))
        .limit(1)
    )
    if exclude_evaluation_id is not None:
        statement = statement.where(BodyCompositionEvaluation.id != exclude_evaluation_id)
    return db.scalar(statement)


def _validate_body_composition_payload(
    payload: BodyCompositionEvaluationCreate | BodyCompositionEvaluationUpdate,
) -> None:
    has_any_measurement = any(getattr(payload, field, None) is not None for field in BODY_COMPOSITION_MEASUREMENT_FIELDS)
    if has_any_measurement:
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Preencha ao menos uma metrica da bioimpedancia antes de salvar a avaliacao.",
    )
