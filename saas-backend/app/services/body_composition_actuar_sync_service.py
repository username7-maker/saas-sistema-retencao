from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.distributed_lock import with_distributed_lock
from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.integrations.actuar import (
    ActuarAssistedRpaProvider,
    ActuarBodyCompositionProvider,
    ActuarCsvExportProvider,
    ActuarHttpApiProvider,
)
from app.models import BodyCompositionEvaluation, BodyCompositionSyncAttempt, Member
from app.models.body_composition_constants import ACTUAR_SYNC_TERMINAL_STATUSES
from app.schemas.body_composition import BodyCompositionActuarSyncStatusRead, BodyCompositionSyncAttemptRead
from app.services.member_service import get_member_or_404


logger = logging.getLogger(__name__)

_PROVIDER_REGISTRY: dict[str, type[ActuarBodyCompositionProvider]] = {
    "http_api": ActuarHttpApiProvider,
    "csv_export": ActuarCsvExportProvider,
    "assisted_rpa": ActuarAssistedRpaProvider,
}


def resolve_actuar_sync_mode() -> str:
    if not settings.actuar_enabled:
        return "disabled"
    mode = (settings.actuar_sync_mode or "").strip().lower()
    if mode in _PROVIDER_REGISTRY:
        return mode
    return "disabled"


def build_body_composition_canonical_payload(member: Member, evaluation: BodyCompositionEvaluation) -> dict:
    external_ref = None
    extra_data = getattr(member, "extra_data", {}) or {}
    if isinstance(extra_data, dict):
        external_ref = extra_data.get("actuar_external_id") or extra_data.get("external_ref")

    payload = {
        "evaluation_id": str(evaluation.id),
        "member_id": str(member.id),
        "member_external_ref": str(external_ref or member.id),
        "evaluation_date": evaluation.evaluation_date.isoformat(),
        "weight_kg": _to_float(evaluation.weight_kg),
        "body_fat_percent": _to_float(evaluation.body_fat_percent),
        "body_fat_kg": _to_float(evaluation.body_fat_kg),
        "bmi": _to_float(evaluation.bmi),
        "visceral_fat_level": _to_float(evaluation.visceral_fat_level),
        "skeletal_muscle_kg": _to_float(evaluation.skeletal_muscle_kg),
        "basal_metabolic_rate_kcal": _to_float(evaluation.basal_metabolic_rate_kcal),
        "health_score": _to_float(evaluation.health_score),
        "notes": evaluation.notes,
        "source": evaluation.source,
        "device_profile": evaluation.device_profile,
        "device_model": evaluation.device_model,
    }
    return payload


def prepare_body_composition_sync_attempt(
    db: Session,
    *,
    member: Member,
    evaluation: BodyCompositionEvaluation,
    force_retry: bool = False,
) -> BodyCompositionSyncAttempt | None:
    sync_mode = resolve_actuar_sync_mode()
    evaluation.actuar_sync_mode = sync_mode

    if sync_mode == "disabled":
        evaluation.actuar_sync_status = "disabled"
        evaluation.actuar_last_error = None
        return None

    provider = _get_provider(sync_mode)
    payload_snapshot = _safe_payload_snapshot(member, evaluation)
    attempt = BodyCompositionSyncAttempt(
        gym_id=evaluation.gym_id,
        body_composition_evaluation_id=evaluation.id,
        sync_mode=sync_mode,
        provider=provider.provider_name,
        status="pending",
        payload_snapshot_json=payload_snapshot,
    )
    db.add(attempt)
    evaluation.actuar_sync_status = "pending"
    evaluation.actuar_last_error = None
    if force_retry:
        evaluation.actuar_last_synced_at = None
    db.flush()
    return attempt


def get_body_composition_sync_status(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
) -> BodyCompositionActuarSyncStatusRead:
    evaluation = get_body_composition_evaluation_or_404(db, gym_id=gym_id, member_id=member_id, evaluation_id=evaluation_id)
    attempts = list(
        db.scalars(
            select(BodyCompositionSyncAttempt)
            .where(BodyCompositionSyncAttempt.body_composition_evaluation_id == evaluation.id)
            .order_by(desc(BodyCompositionSyncAttempt.created_at))
            .limit(10)
        ).all()
    )
    return BodyCompositionActuarSyncStatusRead(
        evaluation_id=evaluation.id,
        sync_mode=evaluation.actuar_sync_mode,
        sync_status=evaluation.actuar_sync_status,
        external_id=evaluation.actuar_external_id,
        last_synced_at=evaluation.actuar_last_synced_at,
        last_error=evaluation.actuar_last_error,
        can_retry=evaluation.actuar_sync_status == "failed",
        attempts=[BodyCompositionSyncAttemptRead.model_validate(attempt) for attempt in attempts],
    )


def schedule_body_composition_sync_retry(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
) -> tuple[BodyCompositionEvaluation, BodyCompositionSyncAttempt]:
    evaluation = get_body_composition_evaluation_or_404(db, gym_id=gym_id, member_id=member_id, evaluation_id=evaluation_id)
    if evaluation.actuar_sync_status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Retry de sync permitido apenas para avaliacoes com status failed",
        )

    member = get_member_or_404(db, member_id, gym_id=gym_id)
    attempt = prepare_body_composition_sync_attempt(db, member=member, evaluation=evaluation, force_retry=True)
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sync externo desabilitado para esta avaliacao")
    db.flush()
    return evaluation, attempt


def get_body_composition_evaluation_or_404(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
) -> BodyCompositionEvaluation:
    evaluation = db.scalar(
        select(BodyCompositionEvaluation).where(
            BodyCompositionEvaluation.id == evaluation_id,
            BodyCompositionEvaluation.gym_id == gym_id,
            BodyCompositionEvaluation.member_id == member_id,
        )
    )
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bioimpedancia nao encontrada")
    return evaluation


def run_body_composition_sync_background(evaluation_id: UUID, attempt_id: UUID, force_retry: bool = False) -> None:
    # BackgroundTasks is the initial post-commit strategy for this feature.
    # It keeps the external sync off the request path, but it is not a durable queue.
    @with_distributed_lock(f"body-composition-sync:{evaluation_id}", ttl_seconds=max(settings.actuar_timeout_seconds * 4, 60))
    def _run() -> None:
        db = SessionLocal()
        try:
            _execute_body_composition_sync_attempt(
                db,
                evaluation_id=evaluation_id,
                attempt_id=attempt_id,
                force_retry=force_retry,
            )
        except Exception:
            logger.exception("Falha inesperada no sync de bioimpedancia %s / tentativa %s", evaluation_id, attempt_id)
            db.rollback()
        finally:
            clear_current_gym_id()
            db.close()

    _run()


def _execute_body_composition_sync_attempt(
    db: Session,
    *,
    evaluation_id: UUID,
    attempt_id: UUID,
    force_retry: bool,
) -> None:
    evaluation = db.scalar(
        select(BodyCompositionEvaluation)
        .where(BodyCompositionEvaluation.id == evaluation_id)
        .execution_options(include_all_tenants=True)
    )
    if not evaluation:
        logger.warning("Sync de bioimpedancia ignorado: avaliacao %s nao encontrada", evaluation_id)
        return

    set_current_gym_id(evaluation.gym_id)
    attempt = db.scalar(
        select(BodyCompositionSyncAttempt)
        .where(
            BodyCompositionSyncAttempt.id == attempt_id,
            BodyCompositionSyncAttempt.body_composition_evaluation_id == evaluation.id,
        )
        .execution_options(include_all_tenants=True)
    )
    if not attempt:
        logger.warning("Sync de bioimpedancia ignorado: tentativa %s nao encontrada", attempt_id)
        return

    if not force_retry and evaluation.actuar_sync_status in ACTUAR_SYNC_TERMINAL_STATUSES:
        _finalize_attempt_only(db, attempt, status="skipped", error="Avaliacao ja estava em estado terminal para sync.")
        return

    if not _claim_attempt(db, attempt.id):
        logger.info("Tentativa %s ja foi reivindicada por outra execucao. Abortando duplicata.", attempt.id)
        return

    db.commit()
    db.refresh(attempt)

    latest_attempt = db.scalar(
        select(BodyCompositionSyncAttempt)
        .where(BodyCompositionSyncAttempt.body_composition_evaluation_id == evaluation.id)
        .order_by(desc(BodyCompositionSyncAttempt.created_at))
        .limit(1)
    )
    if latest_attempt and latest_attempt.id != attempt.id and not force_retry:
        _finalize_attempt_only(db, attempt, status="skipped", error="Tentativa superada por agendamento mais recente.")
        return

    member = get_member_or_404(db, evaluation.member_id, gym_id=evaluation.gym_id)
    payload = _payload_from_attempt_or_live(member, evaluation, attempt)
    provider = _get_provider(evaluation.actuar_sync_mode)

    try:
        outcome = provider.push_body_composition(payload)
        _finalize_sync_success(
            db,
            evaluation=evaluation,
            attempt=attempt,
            payload=payload,
            outcome=outcome,
        )
    except Exception as exc:
        _finalize_sync_failure(db, evaluation=evaluation, attempt=attempt, payload=payload, error=str(exc))


def _claim_attempt(db: Session, attempt_id: UUID) -> bool:
    result = db.execute(
        update(BodyCompositionSyncAttempt)
        .where(
            BodyCompositionSyncAttempt.id == attempt_id,
            BodyCompositionSyncAttempt.status == "pending",
        )
        .values(status="processing", error=None)
    )
    return bool(result.rowcount)


def _finalize_attempt_only(db: Session, attempt: BodyCompositionSyncAttempt, *, status: str, error: str | None) -> None:
    attempt.status = status
    attempt.error = error
    db.add(attempt)
    db.commit()


def _finalize_sync_success(
    db: Session,
    *,
    evaluation: BodyCompositionEvaluation,
    attempt: BodyCompositionSyncAttempt,
    payload: dict,
    outcome,
) -> None:
    attempt.status = outcome.status
    attempt.error = outcome.error
    attempt.payload_snapshot_json = outcome.payload_snapshot_json or payload
    evaluation.actuar_sync_status = outcome.status
    evaluation.actuar_external_id = outcome.external_id
    evaluation.actuar_last_error = outcome.error
    if outcome.status in {"synced", "exported"}:
        evaluation.actuar_last_synced_at = datetime.now(tz=timezone.utc)
    db.add(attempt)
    db.add(evaluation)
    db.commit()


def _finalize_sync_failure(
    db: Session,
    *,
    evaluation: BodyCompositionEvaluation,
    attempt: BodyCompositionSyncAttempt,
    payload: dict,
    error: str,
) -> None:
    attempt.status = "failed"
    attempt.error = error[:1000]
    attempt.payload_snapshot_json = payload
    evaluation.actuar_sync_status = "failed"
    evaluation.actuar_last_error = error[:1000]
    db.add(attempt)
    db.add(evaluation)
    db.commit()


def _payload_from_attempt_or_live(
    member: Member,
    evaluation: BodyCompositionEvaluation,
    attempt: BodyCompositionSyncAttempt,
) -> dict:
    snapshot = attempt.payload_snapshot_json
    if isinstance(snapshot, dict) and snapshot.get("evaluation_id") == str(evaluation.id):
        return snapshot
    return build_body_composition_canonical_payload(member, evaluation)


def _safe_payload_snapshot(member: Member, evaluation: BodyCompositionEvaluation) -> dict:
    try:
        return build_body_composition_canonical_payload(member, evaluation)
    except Exception as exc:
        logger.exception("Falha ao montar snapshot canonico de bioimpedancia para sync.")
        return {
            "evaluation_id": str(evaluation.id),
            "member_id": str(evaluation.member_id),
            "sync_mode": evaluation.actuar_sync_mode,
            "snapshot_error": str(exc),
        }


def _get_provider(sync_mode: str) -> ActuarBodyCompositionProvider:
    provider_cls = _PROVIDER_REGISTRY.get(sync_mode)
    if provider_cls is None:
        return ActuarHttpApiProvider()
    return provider_cls()


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
