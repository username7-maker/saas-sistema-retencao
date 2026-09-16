import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
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
from app.services.assessment_service import (
    ensure_body_composition_technical_ladder_tasks,
    remove_body_composition_technical_ladder_task_sources,
)
from app.services.body_composition_actuar_sync_service import (
    get_body_composition_evaluation_or_404,
    prepare_body_composition_sync_attempt,
)
from app.services.body_composition_ai_service import generate_body_composition_ai
from app.services.body_composition_anthropometry_service import ANTHROPOMETRY_FIELDS
from app.services.body_composition_report_service import resolve_body_composition_persistence_fields
from app.services.audit_service import log_audit_event
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
    "skeletal_muscle_percent",
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
BUSINESS_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def create_body_composition_evaluation(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    payload: BodyCompositionEvaluationCreate,
    *,
    reviewer_user_id: UUID | None = None,
    sync_actuar: bool = True,
    idempotency_key: UUID | None = None,
) -> tuple[BodyCompositionEvaluation, ActuarSyncJob | None]:
    payload_hash = _body_composition_payload_hash(payload)
    if idempotency_key is not None:
        _lock_body_composition_idempotency_key(db, gym_id=gym_id, idempotency_key=idempotency_key)
        existing = db.scalar(
            select(BodyCompositionEvaluation).where(
                BodyCompositionEvaluation.gym_id == gym_id,
                BodyCompositionEvaluation.idempotency_key == idempotency_key,
                BodyCompositionEvaluation.deleted_at.is_(None),
            )
        )
        if existing is not None:
            if existing.member_id != member_id or (
                existing.idempotency_payload_hash
                and existing.idempotency_payload_hash != payload_hash
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A mesma chave de idempotencia ja foi usada com outra avaliacao.",
                )
            return existing, None
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    previous_evaluation = _find_previous_evaluation(db, gym_id=gym_id, member_id=member_id)
    evaluation_data = resolve_body_composition_persistence_fields(
        payload.model_dump(),
        reviewer_user_id=reviewer_user_id,
        previous_evaluation=previous_evaluation,
        explicit_fields=set(payload.model_fields_set),
    )
    _validate_body_composition_payload(payload)
    evaluation_data["reviewed_manually"] = _resolve_reviewed_manually(payload)
    evaluation = BodyCompositionEvaluation(
        gym_id=gym_id,
        member_id=member_id,
        idempotency_key=idempotency_key,
        idempotency_payload_hash=payload_hash if idempotency_key is not None else None,
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


def _body_composition_payload_hash(payload: BodyCompositionEvaluationCreate) -> str:
    canonical = json.dumps(
        payload.model_dump(mode="json", exclude_none=False),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _lock_body_composition_idempotency_key(db: Session, *, gym_id: UUID, idempotency_key: UUID) -> None:
    """Serialize equal keys in PostgreSQL so concurrent retries cannot both insert."""
    bind = db.get_bind()
    if getattr(getattr(bind, "dialect", None), "name", None) != "postgresql":
        return
    digest = hashlib.sha256(f"{gym_id}:{idempotency_key}".encode("ascii")).digest()
    lock_id = int.from_bytes(digest[:8], byteorder="big", signed=True)
    db.execute(select(func.pg_advisory_xact_lock(lock_id)))


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
                BodyCompositionEvaluation.deleted_at.is_(None),
            )
            .order_by(BodyCompositionEvaluation.evaluation_date.desc())
            .limit(limit)
        ).all()
    )


def delete_body_composition_evaluation(
    db: Session,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
) -> BodyCompositionEvaluation:
    evaluation = get_body_composition_evaluation_or_404(
        db,
        gym_id=gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
        for_update=True,
    )
    remove_body_composition_technical_ladder_task_sources(
        db,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )
    now = datetime.now(tz=timezone.utc)
    active_jobs = list(
        db.scalars(
            select(ActuarSyncJob).where(
                ActuarSyncJob.body_composition_evaluation_id == evaluation_id,
                ActuarSyncJob.status.in_(("pending", "processing")),
            )
        ).all()
    )
    for job in active_jobs:
        job.status = "cancelled"
        job.error_code = "evaluation_deleted"
        job.error_message = "Avaliacao removida do historico antes da sincronizacao."
        job.next_retry_at = None
        job.locked_at = None
        job.locked_by = None
    evaluation.deleted_at = now
    evaluation.actuar_sync_job_id = None
    db.flush()
    return evaluation


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
    evaluation = get_body_composition_evaluation_or_404(
        db,
        gym_id=gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
        for_update=True,
    )

    if _normalize_datetime(evaluation.updated_at) != _normalize_datetime(payload.expected_updated_at):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "body_composition_edit_conflict",
                "message": "A avaliacao foi alterada por outro usuario.",
            },
        )

    before_update = _body_composition_change_snapshot(evaluation)
    previous_evaluation = _find_previous_evaluation(db, gym_id=gym_id, member_id=member_id, exclude_evaluation_id=evaluation_id)
    explicit_fields = set(payload.model_fields_set) - {"expected_updated_at"}
    payload_values = payload.model_dump(exclude={"expected_updated_at"})
    if payload.source == "ocr_receipt":
        payload_values = _preserve_existing_anthropometry_for_ocr_update(payload_values, evaluation)
    update_data = resolve_body_composition_persistence_fields(
        payload_values,
        reviewer_user_id=reviewer_user_id,
        previous_evaluation=previous_evaluation,
        existing_evaluation=evaluation,
        explicit_fields=explicit_fields,
    )
    _validate_body_composition_payload(payload)
    update_data["reviewed_manually"] = _resolve_reviewed_manually(payload)
    manual_changes = _manual_calculation_metric_changes(
        evaluation,
        update_data,
        explicit_fields=explicit_fields,
    )
    if manual_changes:
        log_audit_event(
            db,
            "body_composition_metric_manual_override",
            "body_composition_evaluation",
            gym_id=gym_id,
            member_id=member_id,
            entity_id=evaluation_id,
            details={
                "reviewer_user_id": str(reviewer_user_id) if reviewer_user_id else None,
                "changes": manual_changes,
            },
        )
    for field, value in update_data.items():
        setattr(evaluation, field, value)

    after_update = _body_composition_change_snapshot(evaluation)
    changed_fields = {
        field: {"before": before_update[field], "after": after_update[field]}
        for field in before_update
        if before_update[field] != after_update[field]
    }
    if changed_fields:
        log_audit_event(
            db,
            "body_composition_evaluation_updated",
            "body_composition_evaluation",
            gym_id=gym_id,
            member_id=member_id,
            entity_id=evaluation_id,
            details={
                "reviewer_user_id": str(reviewer_user_id) if reviewer_user_id else None,
                "changes": changed_fields,
            },
        )

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
            BodyCompositionEvaluation.deleted_at.is_(None),
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


def _manual_calculation_metric_changes(
    evaluation: BodyCompositionEvaluation,
    update_data: dict,
    *,
    explicit_fields: set[str],
) -> dict[str, dict[str, object]]:
    changes: dict[str, dict[str, object]] = {}
    for field, origin_field in (
        ("basal_metabolic_rate_kcal", "basal_metabolic_rate_origin"),
        ("muscle_mass_kg", "muscle_mass_origin"),
    ):
        if field not in explicit_fields or update_data.get(origin_field) != "reported":
            continue
        before = getattr(evaluation, field, None)
        after = update_data.get(field)
        if after is None or _same_metric_value(before, after):
            continue
        changes[field] = {
            "before": float(before) if before is not None else None,
            "after": float(after),
            "origin_before": getattr(evaluation, origin_field, None) or "legacy_unknown",
            "origin_after": "reported",
        }
    return changes


def _same_metric_value(left: object, right: object) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return abs(float(left) - float(right)) < 0.005
    except (TypeError, ValueError):
        return left == right


def _body_composition_change_snapshot(evaluation: BodyCompositionEvaluation) -> dict[str, object]:
    fields = (
        "evaluation_date",
        "measured_at",
        "age_years",
        "sex",
        "height_cm",
        *BODY_COMPOSITION_MEASUREMENT_FIELDS,
        "measurement_protocol",
        "notes",
    )
    snapshot: dict[str, object] = {}
    for field in dict.fromkeys(fields):
        value = getattr(evaluation, field, None)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = str(value)
        snapshot[field] = value
    return snapshot


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
        "anthropometry_ethnicity",
        "anthropometry_maturity",
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
            BodyCompositionEvaluation.deleted_at.is_(None),
        )
        .order_by(desc(BodyCompositionEvaluation.evaluation_date), desc(BodyCompositionEvaluation.created_at))
        .limit(1)
    )
    if exclude_evaluation_id is not None:
        statement = statement.where(BodyCompositionEvaluation.id != exclude_evaluation_id)
    return db.scalar(statement)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _validate_body_composition_payload(
    payload: BodyCompositionEvaluationCreate | BodyCompositionEvaluationUpdate,
) -> None:
    now = datetime.now(tz=timezone.utc)
    if payload.evaluation_date > now.astimezone(BUSINESS_TIMEZONE).date():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A data da avaliacao nao pode estar no futuro.",
        )
    if payload.measured_at is not None:
        measured_at = payload.measured_at
        if measured_at.tzinfo is None:
            measured_at = measured_at.replace(tzinfo=BUSINESS_TIMEZONE)
        measured_at_utc = measured_at.astimezone(timezone.utc)
        if measured_at_utc > now:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O horario da avaliacao nao pode estar no futuro.",
            )
        if measured_at.astimezone(BUSINESS_TIMEZONE).date() != payload.evaluation_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A data da avaliacao deve coincidir com o horario informado.",
            )
    has_any_measurement = any(getattr(payload, field, None) is not None for field in BODY_COMPOSITION_MEASUREMENT_FIELDS)
    if has_any_measurement:
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Preencha ao menos uma metrica da bioimpedancia antes de salvar a avaliacao.",
    )
