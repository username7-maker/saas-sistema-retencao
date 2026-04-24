from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.distributed_lock import with_distributed_lock
from app.database import SessionLocal, clear_current_gym_id, include_all_tenants, set_current_gym_id
from app.integrations.actuar.assisted_rpa_provider import ActuarAssistedRpaProvider
from app.integrations.actuar.base import ActuarSyncOutcome
from app.integrations.actuar.browser_client import ActuarPlaywrightProvider, _normalize_base_url
from app.integrations.actuar.csv_export_provider import ActuarCsvExportProvider
from app.integrations.actuar.http_api_provider import ActuarHttpApiProvider
from app.models import (
    ActuarMemberLink,
    ActuarSyncAttempt,
    ActuarSyncJob,
    BodyCompositionEvaluation,
    Gym,
    Member,
)
from app.schemas.body_composition import (
    ActuarMemberLinkRead,
    ActuarSyncAttemptRead,
    ActuarSyncJobRead,
    BodyCompositionActuarSyncStatusRead,
    BodyCompositionManualSyncSummaryRead,
)
from app.services.actuar_member_link_service import (
    ActuarMemberResolution,
    get_actuar_member_link,
    resolve_actuar_member,
    upsert_actuar_member_link,
)
from app.services.actuar_bridge_service import count_online_actuar_bridge_devices
from app.services.actuar_settings_service import has_actuar_credentials, resolve_effective_actuar_sync_mode
from app.services.body_composition_actuar_mapping_service import (
    build_actuar_field_mapping,
    build_manual_sync_summary,
)
from app.services.member_service import get_member_or_404


logger = logging.getLogger(__name__)

ACTIVE_JOB_STATUSES = {"pending", "processing"}
LOCAL_BRIDGE_OFFLINE_DETAIL = "Nenhuma estacao Actuar Bridge esta online para esta academia."


@dataclass(slots=True)
class ActuarSyncServiceError(RuntimeError):
    code: str
    message: str
    retryable: bool = False
    manual_fallback: bool = False

    def __str__(self) -> str:
        return self.message


def resolve_actuar_sync_mode(gym: Gym | None = None) -> str:
    return resolve_effective_actuar_sync_mode(gym)


def prepare_body_composition_sync_attempt(
    db: Session,
    *,
    member: Member,
    evaluation: BodyCompositionEvaluation,
    force_retry: bool = False,
    require_online_bridge: bool = False,
) -> ActuarSyncJob | None:
    gym = _get_gym(db, evaluation.gym_id)
    mapping = build_actuar_field_mapping(member, evaluation)
    evaluation.sync_required_for_training = bool(settings.actuar_sync_required_for_training)
    evaluation.actuar_sync_mode = resolve_actuar_sync_mode(gym)
    evaluation.actuar_last_error = None
    evaluation.sync_last_error_code = None
    evaluation.sync_last_error_message = None

    if not _should_auto_sync(gym):
        evaluation.actuar_sync_status = "saved"
        evaluation.actuar_sync_job_id = None
        logger.info(
            "Actuar sync not auto-enabled for evaluation; keeping local save only.",
            extra={
                "extra_fields": {
                    "event": "actuar_training_blocked_pending_sync",
                    "status": "saved",
                    "evaluation_id": str(evaluation.id),
                    "gym_id": str(evaluation.gym_id),
                }
            },
        )
        return None

    if not _ensure_local_bridge_ready(
        db,
        gym_id=evaluation.gym_id,
        sync_mode=evaluation.actuar_sync_mode,
        raise_on_unavailable=require_online_bridge,
    ):
        evaluation.actuar_sync_status = "saved"
        evaluation.actuar_sync_job_id = None
        logger.info(
            "Actuar local bridge offline; keeping evaluation saved only.",
            extra={
                "extra_fields": {
                    "event": "actuar_local_bridge_offline",
                    "status": "saved",
                    "evaluation_id": str(evaluation.id),
                    "gym_id": str(evaluation.gym_id),
                }
            },
        )
        return None

    _cancel_superseded_jobs(db, evaluation.id)
    job = ActuarSyncJob(
        gym_id=evaluation.gym_id,
        member_id=member.id,
        body_composition_evaluation_id=evaluation.id,
        job_type="body_composition_push",
        status="pending",
        payload_json=mapping["payload"],
        mapped_fields_json={"mapped_fields": mapping["mapped_fields"]},
        critical_fields_json=mapping["critical_fields"],
        non_critical_fields_json=mapping["non_critical_fields"],
        max_retries=settings.actuar_sync_max_retries,
    )
    db.add(job)
    db.flush()
    evaluation.actuar_sync_job_id = job.id
    evaluation.actuar_sync_status = "sync_pending"
    if force_retry:
        evaluation.actuar_last_synced_at = None
        evaluation.sync_last_success_at = None

    logger.info(
        "Actuar sync job created.",
        extra={
            "extra_fields": {
                "event": "actuar_sync_job_created",
                "status": "pending",
                "job_id": str(job.id),
                "evaluation_id": str(evaluation.id),
                "member_id": str(member.id),
                "gym_id": str(evaluation.gym_id),
            }
        },
    )
    return job


def create_body_composition_sync_job(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
    created_by_user_id: UUID | None = None,
    force_new: bool = False,
) -> ActuarSyncJob | None:
    evaluation = get_body_composition_evaluation_or_404(db, gym_id=gym_id, member_id=member_id, evaluation_id=evaluation_id)
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    gym = _get_gym(db, evaluation.gym_id)
    current_job = _get_current_sync_job(db, evaluation)
    if current_job and current_job.status in ACTIVE_JOB_STATUSES and not force_new:
        _ensure_local_bridge_ready(
            db,
            gym_id=gym_id,
            sync_mode=resolve_actuar_sync_mode(gym),
            raise_on_unavailable=True,
        )
        return current_job

    job = prepare_body_composition_sync_attempt(
        db,
        member=member,
        evaluation=evaluation,
        force_retry=force_new,
        require_online_bridge=True,
    )
    if job:
        job.created_by_user_id = created_by_user_id
    db.flush()
    return job


def schedule_body_composition_sync_retry(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
) -> tuple[BodyCompositionEvaluation, ActuarSyncJob]:
    evaluation = get_body_composition_evaluation_or_404(db, gym_id=gym_id, member_id=member_id, evaluation_id=evaluation_id)
    if evaluation.actuar_sync_status == "synced_to_actuar":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Avaliacao ja sincronizada com o Actuar")

    job = create_body_composition_sync_job(
        db,
        gym_id=gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
        force_new=True,
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sync Actuar desabilitado para esta academia")
    return evaluation, job


def get_body_composition_sync_status(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
) -> BodyCompositionActuarSyncStatusRead:
    evaluation = get_body_composition_evaluation_or_404(db, gym_id=gym_id, member_id=member_id, evaluation_id=evaluation_id)
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    current_job = _get_current_sync_job(db, evaluation)
    attempts = list(current_job.attempts[:10]) if current_job else []
    mapping = build_actuar_field_mapping(member, evaluation)
    manual_summary = build_manual_sync_summary(member, evaluation)
    member_link = get_actuar_member_link(db, gym_id=gym_id, member_id=member_id)
    unsupported_fields = [
        item for item in mapping["non_critical_fields"] if item.get("classification") == "unsupported" or not item.get("supported", True)
    ]

    return BodyCompositionActuarSyncStatusRead(
        evaluation_id=evaluation.id,
        member_id=member_id,
        sync_mode=evaluation.actuar_sync_mode,
        sync_status=evaluation.actuar_sync_status,
        training_ready=evaluation.training_ready,
        sync_required_for_training=evaluation.sync_required_for_training,
        external_id=evaluation.actuar_external_id,
        last_synced_at=evaluation.sync_last_success_at or evaluation.actuar_last_synced_at,
        last_attempt_at=evaluation.sync_last_attempt_at,
        last_error_code=evaluation.sync_last_error_code,
        last_error=evaluation.sync_last_error_message or evaluation.actuar_last_error,
        can_retry=evaluation.actuar_sync_status != "synced_to_actuar",
        critical_fields=mapping["critical_fields"],
        unsupported_fields=unsupported_fields,
        fallback_manual_summary=manual_summary,
        current_job=ActuarSyncJobRead.model_validate(current_job) if current_job else None,
        attempts=[ActuarSyncAttemptRead.model_validate(item) for item in attempts],
        member_link=ActuarMemberLinkRead.model_validate(member_link) if member_link else None,
    )


def get_body_composition_manual_sync_summary(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
) -> BodyCompositionManualSyncSummaryRead:
    evaluation = get_body_composition_evaluation_or_404(db, gym_id=gym_id, member_id=member_id, evaluation_id=evaluation_id)
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    payload = build_manual_sync_summary(member, evaluation)
    return BodyCompositionManualSyncSummaryRead(
        evaluation_id=evaluation.id,
        member_id=member.id,
        sync_status=evaluation.actuar_sync_status,
        training_ready=evaluation.training_ready,
        critical_fields=payload["critical_fields"],
        summary_text=payload["summary_text"],
    )


def upsert_body_composition_actuar_link(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    user_id: UUID | None,
    actuar_external_id: str | None,
    actuar_search_name: str | None,
    actuar_search_document: str | None,
    actuar_search_birthdate,
    match_confidence: float | None,
) -> ActuarMemberLink:
    get_member_or_404(db, member_id, gym_id=gym_id)
    return upsert_actuar_member_link(
        db,
        gym_id=gym_id,
        member_id=member_id,
        user_id=user_id,
        actuar_external_id=actuar_external_id,
        actuar_search_name=actuar_search_name,
        actuar_search_document=actuar_search_document,
        actuar_search_birthdate=actuar_search_birthdate,
        match_confidence=match_confidence,
    )


def confirm_manual_actuar_sync(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
    confirmed_by_user_id: UUID,
    reason: str,
    note: str | None,
) -> BodyCompositionEvaluation:
    evaluation = get_body_composition_evaluation_or_404(db, gym_id=gym_id, member_id=member_id, evaluation_id=evaluation_id)
    current_job = _get_current_sync_job(db, evaluation)
    now = _now()
    if current_job is None:
        current_job = ActuarSyncJob(
            gym_id=gym_id,
            member_id=member_id,
            body_composition_evaluation_id=evaluation.id,
            job_type="body_composition_push",
            status="synced",
            created_by_user_id=confirmed_by_user_id,
            synced_at=now,
        )
        db.add(current_job)
        db.flush()
        evaluation.actuar_sync_job_id = current_job.id
    else:
        current_job.status = "synced"
        current_job.error_code = None
        current_job.error_message = None
        current_job.next_retry_at = None
        current_job.locked_at = None
        current_job.locked_by = None
        current_job.synced_at = now

    attempt = ActuarSyncAttempt(
        gym_id=gym_id,
        sync_job_id=current_job.id,
        status="succeeded",
        started_at=now,
        finished_at=now,
        worker_id=f"manual:{confirmed_by_user_id}",
        action_log_json=[{"event": "manual_confirmed", "reason": reason, "note": note or ""}],
    )
    db.add(attempt)
    _mark_evaluation_synced(evaluation, external_id=evaluation.actuar_external_id, synced_at=now)
    logger.info(
        "Actuar sync manually confirmed.",
        extra={
            "extra_fields": {
                "event": "actuar_sync_manual_confirmed",
                "status": "synced",
                "evaluation_id": str(evaluation.id),
                "member_id": str(member_id),
                "job_id": str(current_job.id),
            }
        },
    )
    db.flush()
    return evaluation


def list_actuar_sync_queue(
    db: Session,
    *,
    gym_id: UUID,
    sync_status: str | None = None,
    error_code: str | None = None,
    search: str | None = None,
) -> list[dict]:
    stmt = (
        select(BodyCompositionEvaluation, Member, ActuarSyncJob)
        .join(Member, Member.id == BodyCompositionEvaluation.member_id)
        .outerjoin(ActuarSyncJob, ActuarSyncJob.id == BodyCompositionEvaluation.actuar_sync_job_id)
        .where(BodyCompositionEvaluation.gym_id == gym_id)
        .order_by(
            Member.id.asc(),
            desc(BodyCompositionEvaluation.evaluation_date),
            desc(BodyCompositionEvaluation.created_at),
            desc(BodyCompositionEvaluation.id),
        )
    )
    if search:
        stmt = stmt.where(Member.full_name.ilike(f"%{search.strip()}%"))

    rows = db.execute(stmt).all()
    items: list[dict] = []
    seen_members: set[UUID] = set()
    for evaluation, member, job in rows:
        if member.id in seen_members:
            continue
        seen_members.add(member.id)
        if evaluation.actuar_sync_status == "synced_to_actuar":
            continue
        if sync_status and evaluation.actuar_sync_status != sync_status:
            continue
        if error_code and evaluation.sync_last_error_code != error_code:
            continue
        items.append(
            {
                "evaluation_id": evaluation.id,
                "member_id": member.id,
                "member_name": member.full_name,
                "evaluation_date": evaluation.evaluation_date,
                "sync_status": evaluation.actuar_sync_status,
                "training_ready": evaluation.training_ready,
                "error_code": evaluation.sync_last_error_code,
                "error_message": evaluation.sync_last_error_message or evaluation.actuar_last_error,
                "next_retry_at": job.next_retry_at if job else None,
                "current_job": ActuarSyncJobRead.model_validate(job) if job else None,
            }
        )
    return items


def process_pending_actuar_sync_jobs(batch_size: int = 3, worker_id: str | None = None) -> int:
    processed = 0
    resolved_worker_id = worker_id or f"worker:{socket.gethostname()}"
    for _ in range(batch_size):
        db = SessionLocal()
        try:
            job = claim_next_actuar_sync_job(db, worker_id=resolved_worker_id)
            if not job:
                break
            job_id = job.id
        finally:
            db.close()

        execute_actuar_sync_job(job_id=job_id, worker_id=resolved_worker_id)
        processed += 1
    return processed


def claim_next_actuar_sync_job(db: Session, *, worker_id: str) -> ActuarSyncJob | None:
    now = _now()
    candidate = db.scalar(
        include_all_tenants(
            select(ActuarSyncJob)
            .join(BodyCompositionEvaluation, BodyCompositionEvaluation.id == ActuarSyncJob.body_composition_evaluation_id)
            .where(
                or_(
                    ActuarSyncJob.status == "pending",
                    (
                        (ActuarSyncJob.status == "failed")
                        & (ActuarSyncJob.next_retry_at.is_not(None))
                        & (ActuarSyncJob.next_retry_at <= now)
                        & (ActuarSyncJob.retry_count < ActuarSyncJob.max_retries)
                    ),
                )
            )
            .where(BodyCompositionEvaluation.actuar_sync_mode != "local_bridge")
            .order_by(ActuarSyncJob.created_at.asc())
            .limit(1),
            reason="actuar_sync.claim_next_job",
        )
    )
    if not candidate:
        return None

    current_status = candidate.status
    result = db.execute(
        include_all_tenants(
            update(ActuarSyncJob)
            .where(ActuarSyncJob.id == candidate.id, ActuarSyncJob.status == current_status)
            .values(status="processing", locked_at=now, locked_by=worker_id),
            reason="actuar_sync.claim_job_lock",
        )
    )
    if not result.rowcount:
        db.rollback()
        return None
    db.commit()
    db.refresh(candidate)
    return candidate


def execute_actuar_sync_job(*, job_id: UUID, worker_id: str) -> None:
    @with_distributed_lock(
        f"actuar-sync-job:{job_id}",
        ttl_seconds=max(settings.actuar_sync_timeout_seconds * 2, 120),
        fail_open=False,
    )
    def _run() -> None:
        db = SessionLocal()
        provider: object | None = None
        try:
            job = db.scalar(
                include_all_tenants(select(ActuarSyncJob).where(ActuarSyncJob.id == job_id), reason="actuar_sync.execute_job")
            )
            if not job:
                return
            evaluation = db.scalar(
                include_all_tenants(
                    select(BodyCompositionEvaluation)
                    .where(BodyCompositionEvaluation.id == job.body_composition_evaluation_id),
                    reason="actuar_sync.load_evaluation",
                )
            )
            member = db.scalar(
                include_all_tenants(select(Member).where(Member.id == job.member_id), reason="actuar_sync.load_member")
            )
            gym = _get_gym(db, job.gym_id)
            if not evaluation or not member:
                raise ActuarSyncServiceError("validation_failed", "Job de sync sem avaliacao ou membro valido.", retryable=False)

            set_current_gym_id(job.gym_id)
            attempt = _start_attempt(db, job=job, evaluation=evaluation, worker_id=worker_id)
            logger.info(
                "Actuar sync job started.",
                extra={
                    "extra_fields": {
                        "event": "actuar_sync_job_started",
                        "status": "processing",
                        "job_id": str(job.id),
                        "evaluation_id": str(evaluation.id),
                        "member_id": str(member.id),
                        "gym_id": str(job.gym_id),
                    }
                },
            )

            mapping = build_actuar_field_mapping(member, evaluation)
            missing_critical = mapping["missing_critical_fields"]
            if missing_critical:
                raise ActuarSyncServiceError(
                    "critical_fields_missing",
                    f"Campos criticos ausentes para sync Actuar: {', '.join(missing_critical)}",
                    retryable=False,
                    manual_fallback=True,
                )

            provider = _build_provider(
                gym=gym,
                sync_mode=evaluation.actuar_sync_mode,
                worker_id=worker_id,
                evidence_dir=_build_evidence_dir(job.gym_id, job.id),
            )
            if isinstance(provider, (ActuarCsvExportProvider, ActuarHttpApiProvider)):
                outcome = provider.push_body_composition(mapping["payload"])
                _finalize_non_browser_outcome(
                    db,
                    job=job,
                    evaluation=evaluation,
                    attempt=attempt,
                    outcome=outcome,
                )
                return

            assert isinstance(provider, ActuarPlaywrightProvider)
            provider.login()
            resolution = resolve_actuar_member(db, gym_id=job.gym_id, member=member, provider=provider, user_id=job.created_by_user_id)
            _log_resolution(resolution, member_id=member.id, job_id=job.id, gym_id=job.gym_id)
            if resolution.status != "matched":
                raise ActuarSyncServiceError(
                    resolution.error_code or "member_not_linked",
                    "Nao foi possivel vincular com seguranca o aluno no Actuar.",
                    retryable=False,
                    manual_fallback=True,
                )

            member_context = {
                **(resolution.member_context or {}),
                "external_id": resolution.actuar_external_id,
                "full_name": member.full_name,
                "email": getattr(member, "email", None),
                "birthdate": member.birthdate.isoformat() if getattr(member, "birthdate", None) else None,
            }

            result = provider.push_body_composition(
                member_context=member_context,
                mapped_payload=[item for item in mapping["mapped_fields"] if item["supported"] and item["value"] is not None],
                capture_success=settings.actuar_sync_screenshot_on_success,
                evidence_prefix=f"gym-{job.gym_id}-job-{job.id}",
            )
            logger.info(
                "Actuar body composition form filled.",
                extra={"extra_fields": {"event": "actuar_sync_form_filled", "job_id": str(job.id), "status": "processing"}},
            )
            _finalize_sync_success(
                db,
                job=job,
                evaluation=evaluation,
                attempt=attempt,
                external_id=result.get("actuar_external_id") or resolution.actuar_external_id,
                action_log=(resolution.action_log or []) + (result.get("action_log") or []),
                screenshot_path=result.get("screenshot_path"),
                page_html_path=result.get("page_html_path"),
            )
        except ActuarSyncServiceError as exc:
            _finalize_sync_failure(db, job_id=job_id, worker_id=worker_id, error=exc, provider=provider)
        except Exception as exc:
            logger.exception(
                "Unexpected Actuar sync failure.",
                extra={
                    "extra_fields": {
                        "event": "actuar_sync_unexpected_exception",
                        "job_id": str(job_id),
                        "worker_id": worker_id,
                        "error_type": type(exc).__name__,
                        "error_repr": repr(exc)[:1000],
                        "provider_state": _provider_debug_state(provider),
                    }
                },
            )
            mapped_error = _map_unexpected_error(exc)
            _finalize_sync_failure(db, job_id=job_id, worker_id=worker_id, error=mapped_error, provider=provider)
        finally:
            if provider:
                close = getattr(provider, "close", None)
                if callable(close):
                    close()
            clear_current_gym_id()
            db.close()

    _run()


def run_body_composition_sync_background(evaluation_id: UUID, attempt_id: UUID, force_retry: bool = False) -> None:
    # Backwards-compatible wrapper kept for tests and legacy callers.
    execute_actuar_sync_job(job_id=attempt_id, worker_id=f"legacy:{'retry' if force_retry else 'initial'}")


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


def _should_auto_sync(gym: Gym) -> bool:
    return bool(settings.actuar_sync_enabled and gym.actuar_enabled and gym.actuar_auto_sync_body_composition)


def _ensure_local_bridge_ready(
    db: Session,
    *,
    gym_id: UUID,
    sync_mode: str | None,
    raise_on_unavailable: bool,
) -> bool:
    if (sync_mode or "").strip().lower() != "local_bridge":
        return True
    if count_online_actuar_bridge_devices(db, gym_id=gym_id) > 0:
        return True
    if raise_on_unavailable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=LOCAL_BRIDGE_OFFLINE_DETAIL)
    return False


def _get_gym(db: Session, gym_id: UUID) -> Gym:
    gym = db.scalar(include_all_tenants(select(Gym).where(Gym.id == gym_id), reason="actuar_sync.fetch_gym"))
    if not gym:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academia nao encontrada")
    return gym


def _get_current_sync_job(db: Session, evaluation: BodyCompositionEvaluation) -> ActuarSyncJob | None:
    if evaluation.actuar_sync_job_id:
        job = db.scalar(
            include_all_tenants(
                select(ActuarSyncJob).where(ActuarSyncJob.id == evaluation.actuar_sync_job_id),
                reason="actuar_sync.fetch_current_job_by_id",
            )
        )
        if job:
            return job
    return db.scalar(
        include_all_tenants(
            select(ActuarSyncJob)
            .where(ActuarSyncJob.body_composition_evaluation_id == evaluation.id)
            .order_by(desc(ActuarSyncJob.created_at))
            .limit(1),
            reason="actuar_sync.fetch_current_job_latest",
        )
    )


def _cancel_superseded_jobs(db: Session, evaluation_id: UUID) -> None:
    jobs = list(
        db.scalars(
            include_all_tenants(
                select(ActuarSyncJob)
                .where(
                    ActuarSyncJob.body_composition_evaluation_id == evaluation_id,
                    ActuarSyncJob.status.in_(ACTIVE_JOB_STATUSES),
                ),
                reason="actuar_sync.cancel_superseded_jobs",
            )
        ).all()
    )
    for job in jobs:
        job.status = "cancelled"
        job.error_code = "superseded"
        job.error_message = "Job substituido por uma avaliacao ou reprocessamento mais recente."


def _start_attempt(db: Session, *, job: ActuarSyncJob, evaluation: BodyCompositionEvaluation, worker_id: str) -> ActuarSyncAttempt:
    now = _now()
    attempt = ActuarSyncAttempt(gym_id=job.gym_id, sync_job_id=job.id, status="started", started_at=now, worker_id=worker_id)
    evaluation.actuar_sync_status = "syncing"
    evaluation.sync_last_attempt_at = now
    db.add(attempt)
    db.add(job)
    db.add(evaluation)
    db.commit()
    db.refresh(attempt)
    return attempt


def _finalize_sync_success(
    db: Session,
    *,
    job: ActuarSyncJob,
    evaluation: BodyCompositionEvaluation,
    attempt: ActuarSyncAttempt,
    external_id: str | None,
    action_log: list[dict],
    screenshot_path: str | None,
    page_html_path: str | None,
) -> None:
    now = _now()
    attempt.status = "succeeded"
    attempt.finished_at = now
    attempt.action_log_json = action_log
    attempt.screenshot_path = screenshot_path
    attempt.page_html_path = page_html_path
    job.status = "synced"
    job.error_code = None
    job.error_message = None
    job.next_retry_at = None
    job.synced_at = now
    job.locked_at = None
    job.locked_by = None
    _mark_evaluation_synced(evaluation, external_id=external_id, synced_at=now)
    db.add_all([attempt, job, evaluation])
    db.commit()
    logger.info(
        "Actuar sync job succeeded.",
        extra={
            "extra_fields": {
                "event": "actuar_sync_job_succeeded",
                "status": "synced",
                "job_id": str(job.id),
                "evaluation_id": str(evaluation.id),
                "member_id": str(evaluation.member_id),
                "gym_id": str(evaluation.gym_id),
            }
        },
    )


def _finalize_sync_failure(
    db: Session,
    *,
    job_id: UUID,
    worker_id: str,
    error: ActuarSyncServiceError,
    provider: ActuarPlaywrightProvider | None,
) -> None:
    job = db.scalar(include_all_tenants(select(ActuarSyncJob).where(ActuarSyncJob.id == job_id), reason="actuar_sync.finalize_failure_job"))
    if not job:
        return
    evaluation = db.scalar(
        include_all_tenants(
            select(BodyCompositionEvaluation)
            .where(BodyCompositionEvaluation.id == job.body_composition_evaluation_id),
            reason="actuar_sync.finalize_failure_evaluation",
        )
    )
    if not evaluation:
        return
    attempt = db.scalar(
        include_all_tenants(
            select(ActuarSyncAttempt)
            .where(ActuarSyncAttempt.sync_job_id == job.id)
            .order_by(desc(ActuarSyncAttempt.started_at))
            .limit(1),
            reason="actuar_sync.finalize_failure_attempt",
        )
    )
    now = _now()
    evidence = {"screenshot_path": None, "page_html_path": None}
    if provider and settings.actuar_sync_screenshot_on_failure:
        evidence = provider.capture_failure_evidence(f"gym-{job.gym_id}-job-{job.id}-failure")

    if attempt:
        attempt.status = "failed"
        attempt.finished_at = now
        attempt.error_code = error.code
        attempt.error_message = error.message[:1000]
        attempt.screenshot_path = evidence["screenshot_path"]
        attempt.page_html_path = evidence["page_html_path"]

    job.error_code = error.code
    job.error_message = error.message[:1000]
    job.locked_at = None
    job.locked_by = None
    evaluation.sync_last_error_code = error.code
    evaluation.sync_last_error_message = error.message[:1000]
    evaluation.actuar_last_error = error.message[:1000]

    if error.retryable:
        job.retry_count += 1
        if job.retry_count < job.max_retries:
            job.status = "failed"
            job.next_retry_at = _now() + timedelta(minutes=5 * max(job.retry_count, 1))
            evaluation.actuar_sync_status = "sync_failed"
            logger.info(
                "Actuar sync job scheduled for retry.",
                extra={
                    "extra_fields": {
                        "event": "actuar_sync_job_retried",
                        "status": "failed",
                        "job_id": str(job.id),
                        "retry_count": job.retry_count,
                        "error_code": error.code,
                    }
                },
            )
        else:
            job.status = "failed"
            job.next_retry_at = None
            evaluation.actuar_sync_status = "sync_failed"
    else:
        job.next_retry_at = None
        job.status = "needs_review"
        evaluation.actuar_sync_status = "manual_sync_required" if error.manual_fallback else "needs_review"
        logger.info(
            "Actuar sync job marked as needs review.",
            extra={
                "extra_fields": {
                    "event": "actuar_sync_job_needs_review",
                    "status": "needs_review",
                    "job_id": str(job.id),
                    "error_code": error.code,
                }
            },
        )

    db.add(job)
    db.add(evaluation)
    if attempt:
        db.add(attempt)
    db.commit()
    logger.warning(
        "Actuar sync job failed.",
        extra={
            "extra_fields": {
                "event": "actuar_sync_job_failed",
                "status": job.status,
                "job_id": str(job.id),
                "evaluation_id": str(evaluation.id),
                "worker_id": worker_id,
                "error_code": error.code,
            }
        },
    )


def _finalize_non_browser_outcome(
    db: Session,
    *,
    job: ActuarSyncJob,
    evaluation: BodyCompositionEvaluation,
    attempt: ActuarSyncAttempt,
    outcome: ActuarSyncOutcome,
) -> None:
    if outcome.status == "exported":
        _finalize_csv_export(
            db,
            job=job,
            evaluation=evaluation,
            attempt=attempt,
            outcome=outcome,
        )
        return

    message = outcome.error or "Provider do Actuar nao concluiu a exportacao nesta tentativa."
    raise ActuarSyncServiceError(
        "actuar_provider_unavailable",
        message,
        retryable=False,
        manual_fallback=True,
    )


def _finalize_csv_export(
    db: Session,
    *,
    job: ActuarSyncJob,
    evaluation: BodyCompositionEvaluation,
    attempt: ActuarSyncAttempt,
    outcome: ActuarSyncOutcome,
) -> None:
    now = _now()
    snapshot = outcome.payload_snapshot_json or job.payload_json or {}
    attempt.status = "succeeded"
    attempt.finished_at = now
    attempt.action_log_json = [
        {
            "event": "csv_export_ready",
            "provider": outcome.provider,
            "status": outcome.status,
            "external_id": outcome.external_id,
            "payload_snapshot_json": snapshot,
        }
    ]
    job.status = "needs_review"
    job.error_code = "csv_export_ready"
    job.error_message = "Exportacao CSV pronta para lancamento manual no Actuar."
    job.next_retry_at = None
    job.locked_at = None
    job.locked_by = None
    evaluation.actuar_sync_status = "manual_sync_required"
    evaluation.actuar_external_id = outcome.external_id or evaluation.actuar_external_id
    evaluation.sync_last_error_code = "csv_export_ready"
    evaluation.sync_last_error_message = "Exportacao CSV pronta para lancamento manual no Actuar."
    evaluation.actuar_last_error = "Exportacao CSV pronta para lancamento manual no Actuar."
    db.add_all([attempt, job, evaluation])
    db.commit()
    logger.info(
        "Actuar CSV export generated for manual sync.",
        extra={
            "extra_fields": {
                "event": "actuar_sync_csv_export_ready",
                "status": "manual_sync_required",
                "job_id": str(job.id),
                "evaluation_id": str(evaluation.id),
                "member_id": str(evaluation.member_id),
                "gym_id": str(evaluation.gym_id),
            }
        },
    )


def _mark_evaluation_synced(evaluation: BodyCompositionEvaluation, *, external_id: str | None, synced_at: datetime) -> None:
    evaluation.actuar_sync_status = "synced_to_actuar"
    evaluation.actuar_external_id = external_id or evaluation.actuar_external_id
    evaluation.sync_last_success_at = synced_at
    evaluation.sync_last_error_code = None
    evaluation.sync_last_error_message = None
    evaluation.actuar_last_synced_at = synced_at
    evaluation.actuar_last_error = None


def _get_actuar_credentials(gym: Gym) -> dict[str, str]:
    base_url = _normalize_base_url((gym.actuar_base_url or settings.actuar_base_url or "").strip())
    username = (gym.actuar_username or settings.actuar_username or "").strip()
    password = (gym.actuar_password_encrypted or settings.actuar_password or "").strip()
    if not base_url or not username or not password:
        raise ActuarSyncServiceError(
            "actuar_login_failed",
            "Credenciais do Actuar ausentes ou incompletas para esta academia.",
            retryable=False,
            manual_fallback=True,
        )
    return {"base_url": base_url, "username": username, "password": password}


def _build_provider(
    *,
    gym: Gym,
    sync_mode: str | None,
    worker_id: str,
    evidence_dir: Path,
) -> ActuarPlaywrightProvider | ActuarCsvExportProvider | ActuarHttpApiProvider:
    normalized_mode = (sync_mode or "assisted_rpa").strip().lower()
    if normalized_mode == "csv_export":
        return ActuarCsvExportProvider()
    if normalized_mode == "http_api":
        return ActuarHttpApiProvider()
    if normalized_mode == "local_bridge":
        raise ActuarSyncServiceError(
            "actuar_bridge_required",
            "Este job deve ser processado por uma estacao local Actuar Bridge, nao pelo worker server-side.",
            retryable=False,
            manual_fallback=True,
        )

    if normalized_mode == "assisted_rpa" and not has_actuar_credentials(gym):
        return ActuarCsvExportProvider()

    credentials = _get_actuar_credentials(gym)
    return ActuarAssistedRpaProvider(
        base_url=credentials["base_url"],
        username=credentials["username"],
        password=credentials["password"],
        worker_id=worker_id,
        evidence_dir=evidence_dir,
    )


def _build_evidence_dir(gym_id: UUID, job_id: UUID) -> Path:
    return Path(settings.actuar_sync_evidence_dir) / str(gym_id) / str(job_id)


def _log_resolution(resolution: ActuarMemberResolution, *, member_id: UUID, job_id: UUID, gym_id: UUID) -> None:
    if resolution.status == "matched":
        logger.info(
            "Actuar member matched.",
            extra={
                "extra_fields": {
                    "event": "actuar_sync_member_matched",
                    "job_id": str(job_id),
                    "member_id": str(member_id),
                    "gym_id": str(gym_id),
                }
            },
        )
        return

    logger.warning(
        "Actuar member matching needs review.",
        extra={
            "extra_fields": {
                "event": "actuar_sync_member_match_ambiguous" if resolution.error_code == "member_match_ambiguous" else "actuar_sync_job_needs_review",
                "job_id": str(job_id),
                "member_id": str(member_id),
                "gym_id": str(gym_id),
                "error_code": resolution.error_code,
            }
        },
    )


def _provider_debug_state(provider: object | None) -> dict | None:
    if provider is None:
        return None
    client = getattr(provider, "client", None)
    page = getattr(client, "page", None)
    if client is None or page is None:
        return {"has_page": False}
    try:
        page_url = page.url
    except Exception:
        page_url = None
    try:
        page_hash = client._page_hash()
    except Exception:
        page_hash = None
    try:
        visible_actions = client._visible_action_texts()
    except Exception:
        visible_actions = []
    try:
        visible_fields = client._visible_field_keys()
    except Exception:
        visible_fields = []
    return {
        "has_page": True,
        "page_url": page_url,
        "page_hash": page_hash,
        "visible_actions": visible_actions,
        "visible_fields": visible_fields,
    }


def _map_unexpected_error(exc: Exception) -> ActuarSyncServiceError:
    raw_code = str(exc).strip()
    if raw_code.startswith("actuar_missing_tab:"):
        tab_name = raw_code.split(":", 1)[1] or "unknown"
        return ActuarSyncServiceError(
            "actuar_form_changed",
            f"Aba obrigatoria do Actuar nao encontrada: {tab_name}.",
            retryable=False,
            manual_fallback=True,
        )
    if raw_code.startswith("actuar_missing_action:"):
        action_name = raw_code.split(":", 1)[1] or "unknown"
        return ActuarSyncServiceError(
            "actuar_form_changed",
            f"Acao obrigatoria do fluxo Actuar nao encontrada: {action_name}.",
            retryable=False,
            manual_fallback=True,
        )
    if raw_code.startswith("actuar_missing_form:"):
        form_name = raw_code.split(":", 1)[1] or "unknown"
        return ActuarSyncServiceError(
            "actuar_form_changed",
            f"Formulario obrigatorio do Actuar nao encontrado: {form_name}.",
            retryable=False,
            manual_fallback=True,
        )
    if raw_code == "actuar_missing_save_button":
        return ActuarSyncServiceError(
            "actuar_form_changed",
            "Botao de salvar do formulario Actuar nao encontrado.",
            retryable=False,
            manual_fallback=True,
        )
    if raw_code == "actuar_save_unconfirmed":
        return ActuarSyncServiceError(
            "actuar_form_changed",
            "O Actuar nao confirmou o salvamento da avaliacao dentro da janela esperada.",
            retryable=False,
            manual_fallback=True,
        )
    if raw_code.startswith("actuar_missing_field:"):
        field_name = raw_code.split(":", 1)[1] or "unknown"
        return ActuarSyncServiceError(
            "actuar_form_changed",
            f"Campo obrigatorio do formulario Actuar nao encontrado: {field_name}.",
            retryable=False,
            manual_fallback=True,
        )
    if raw_code == "actuar_form_changed":
        return ActuarSyncServiceError("actuar_form_changed", "Formulario do Actuar mudou e requer revisao.", retryable=False, manual_fallback=True)
    if raw_code.startswith("critical_fields_missing:"):
        field_name = raw_code.split(":", 1)[1] or "unknown"
        return ActuarSyncServiceError(
            "critical_fields_missing",
            f"Campo critico ausente para sincronizacao: {field_name}.",
            retryable=False,
            manual_fallback=True,
        )
    if raw_code == "critical_fields_missing":
        return ActuarSyncServiceError("critical_fields_missing", "Campos criticos ausentes para sincronizacao.", retryable=False, manual_fallback=True)
    if raw_code == "playwright_unavailable":
        return ActuarSyncServiceError("external_unavailable", "Playwright indisponivel no worker para executar o sync.", retryable=True)
    if "Executable doesn't exist" in raw_code:
        return ActuarSyncServiceError("external_unavailable", "Navegador do Playwright ausente no worker para executar o sync.", retryable=True)
    return ActuarSyncServiceError("external_unavailable", f"Falha externa no sync Actuar: {type(exc).__name__}.", retryable=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)
