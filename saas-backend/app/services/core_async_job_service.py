import base64
import logging
import socket
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal, clear_current_gym_id, include_all_tenants, set_current_gym_id
from app.models import CoreAsyncJob

logger = logging.getLogger(__name__)

CORE_ASYNC_JOB_TYPE_PUBLIC_DIAGNOSIS = "public_diagnosis"
CORE_ASYNC_JOB_TYPE_LEAD_PROPOSAL_DISPATCH = "lead_proposal_dispatch"
CORE_ASYNC_JOB_TYPE_NPS_DISPATCH = "nps_dispatch"
CORE_ASYNC_JOB_TYPE_MONTHLY_REPORTS_DISPATCH = "monthly_reports_dispatch"
CORE_ASYNC_JOB_TYPE_WHATSAPP_WEBHOOK_SETUP = "whatsapp_webhook_setup"
_RETRY_DELAYS_MINUTES = (1, 5, 15, 60)
_STALE_LOCK_AFTER = timedelta(minutes=15)


class CoreAsyncJobNonRetryableError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _worker_id() -> str:
    return f"{socket.gethostname()}:{settings.app_name}:core-async"


def _queue_wait_seconds(job: CoreAsyncJob) -> int | None:
    if job.started_at is None or job.created_at is None:
        return None
    return max(int((job.started_at - job.created_at).total_seconds()), 0)


def _job_log_extra(job: CoreAsyncJob, *, event: str, status: str | None = None, **extra: Any) -> dict[str, Any]:
    extra_fields: dict[str, Any] = {
        "event": event,
        "job_id": str(job.id),
        "job_type": job.job_type,
        "gym_id": str(job.gym_id),
        "status": status or job.status,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "queue_wait_seconds": _queue_wait_seconds(job),
    }
    for key, value in extra.items():
        if value is not None:
            extra_fields[key] = value
    return {"extra_fields": extra_fields}


def serialize_core_async_job(job: CoreAsyncJob) -> dict[str, Any]:
    return {
        "job_id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "next_retry_at": job.next_retry_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "queue_wait_seconds": _queue_wait_seconds(job),
        "error_code": job.error_code,
        "error_message": job.error_message_redacted,
        "result": job.result_json,
        "related_entity_type": job.related_entity_type,
        "related_entity_id": job.related_entity_id,
    }


def enqueue_public_diagnosis_job(
    db: Session,
    *,
    gym_id: UUID,
    diagnosis_id: UUID,
    lead_id: UUID,
    payload: dict[str, Any],
    csv_content: bytes,
    requester_ip: str | None = None,
    user_agent: str | None = None,
) -> CoreAsyncJob:
    encoded_csv = base64.b64encode(csv_content).decode("ascii")
    payload_with_meta = {
        **payload,
        "__request_meta": {
            "requester_ip": requester_ip,
            "user_agent": user_agent,
        },
    }
    job = CoreAsyncJob(
        id=diagnosis_id,
        gym_id=gym_id,
        related_entity_type="lead",
        related_entity_id=lead_id,
        job_type=CORE_ASYNC_JOB_TYPE_PUBLIC_DIAGNOSIS,
        status="pending",
        payload_json=payload_with_meta,
        payload_blob=encoded_csv,
        idempotency_key=f"public_diagnosis:{diagnosis_id}",
        max_attempts=len(_RETRY_DELAYS_MINUTES) + 1,
    )
    db.add(job)
    db.flush()
    return job


def enqueue_lead_proposal_dispatch_job(
    db: Session,
    *,
    gym_id: UUID,
    lead_id: UUID,
    requested_by_user_id: UUID | None,
) -> tuple[CoreAsyncJob, bool]:
    idempotency_key = f"lead_proposal_dispatch:{lead_id}"
    existing = db.scalar(
        select(CoreAsyncJob)
        .where(
            CoreAsyncJob.gym_id == gym_id,
            CoreAsyncJob.job_type == CORE_ASYNC_JOB_TYPE_LEAD_PROPOSAL_DISPATCH,
            CoreAsyncJob.idempotency_key == idempotency_key,
            CoreAsyncJob.status.in_(("pending", "processing", "retry_scheduled")),
        )
        .order_by(CoreAsyncJob.created_at.asc())
        .limit(1)
    )
    if existing:
        return existing, False

    job = CoreAsyncJob(
        gym_id=gym_id,
        requested_by_user_id=requested_by_user_id,
        related_entity_type="lead",
        related_entity_id=lead_id,
        job_type=CORE_ASYNC_JOB_TYPE_LEAD_PROPOSAL_DISPATCH,
        status="pending",
        payload_json={"lead_id": str(lead_id)},
        idempotency_key=idempotency_key,
        max_attempts=len(_RETRY_DELAYS_MINUTES) + 1,
    )
    db.add(job)
    db.flush()
    return job, True


def enqueue_nps_dispatch_job(
    db: Session,
    *,
    gym_id: UUID,
    requested_by_user_id: UUID | None,
) -> tuple[CoreAsyncJob, bool]:
    idempotency_key = f"nps_dispatch:{gym_id}"
    existing = db.scalar(
        select(CoreAsyncJob)
        .where(
            CoreAsyncJob.gym_id == gym_id,
            CoreAsyncJob.job_type == CORE_ASYNC_JOB_TYPE_NPS_DISPATCH,
            CoreAsyncJob.idempotency_key == idempotency_key,
            CoreAsyncJob.status.in_(("pending", "processing", "retry_scheduled")),
        )
        .order_by(CoreAsyncJob.created_at.asc())
        .limit(1)
    )
    if existing:
        return existing, False

    job = CoreAsyncJob(
        gym_id=gym_id,
        requested_by_user_id=requested_by_user_id,
        related_entity_type="gym",
        related_entity_id=gym_id,
        job_type=CORE_ASYNC_JOB_TYPE_NPS_DISPATCH,
        status="pending",
        payload_json={"gym_id": str(gym_id)},
        idempotency_key=idempotency_key,
        max_attempts=len(_RETRY_DELAYS_MINUTES) + 1,
    )
    db.add(job)
    db.flush()
    return job, True


def enqueue_monthly_reports_dispatch_job(
    db: Session,
    *,
    gym_id: UUID,
    requested_by_user_id: UUID | None,
) -> tuple[CoreAsyncJob, bool]:
    idempotency_key = f"monthly_reports_dispatch:{gym_id}"
    existing = db.scalar(
        select(CoreAsyncJob)
        .where(
            CoreAsyncJob.gym_id == gym_id,
            CoreAsyncJob.job_type == CORE_ASYNC_JOB_TYPE_MONTHLY_REPORTS_DISPATCH,
            CoreAsyncJob.idempotency_key == idempotency_key,
            CoreAsyncJob.status.in_(("pending", "processing", "retry_scheduled")),
        )
        .order_by(CoreAsyncJob.created_at.asc())
        .limit(1)
    )
    if existing:
        return existing, False

    job = CoreAsyncJob(
        gym_id=gym_id,
        requested_by_user_id=requested_by_user_id,
        related_entity_type="gym",
        related_entity_id=gym_id,
        job_type=CORE_ASYNC_JOB_TYPE_MONTHLY_REPORTS_DISPATCH,
        status="pending",
        payload_json={"gym_id": str(gym_id)},
        idempotency_key=idempotency_key,
        max_attempts=len(_RETRY_DELAYS_MINUTES) + 1,
    )
    db.add(job)
    db.flush()
    return job, True


def enqueue_whatsapp_webhook_setup_job(
    db: Session,
    *,
    gym_id: UUID,
    requested_by_user_id: UUID | None,
    instance: str,
    webhook_url: str,
    webhook_headers: dict[str, str] | None,
) -> tuple[CoreAsyncJob, bool]:
    idempotency_key = f"whatsapp_webhook_setup:{gym_id}:{instance}"
    existing = db.scalar(
        select(CoreAsyncJob)
        .where(
            CoreAsyncJob.gym_id == gym_id,
            CoreAsyncJob.job_type == CORE_ASYNC_JOB_TYPE_WHATSAPP_WEBHOOK_SETUP,
            CoreAsyncJob.idempotency_key == idempotency_key,
            CoreAsyncJob.status.in_(("pending", "processing", "retry_scheduled")),
        )
        .order_by(CoreAsyncJob.created_at.asc())
        .limit(1)
    )
    if existing:
        return existing, False

    job = CoreAsyncJob(
        gym_id=gym_id,
        requested_by_user_id=requested_by_user_id,
        related_entity_type="gym",
        related_entity_id=gym_id,
        job_type=CORE_ASYNC_JOB_TYPE_WHATSAPP_WEBHOOK_SETUP,
        status="pending",
        payload_json={
            "instance": instance,
            "webhook_url": webhook_url,
            "webhook_headers": webhook_headers or {},
        },
        idempotency_key=idempotency_key,
        max_attempts=len(_RETRY_DELAYS_MINUTES) + 1,
    )
    db.add(job)
    db.flush()
    return job, True


def get_core_async_job(db: Session, *, job_id: UUID, gym_id: UUID) -> CoreAsyncJob | None:
    return db.scalar(
        select(CoreAsyncJob).where(
            CoreAsyncJob.id == job_id,
            CoreAsyncJob.gym_id == gym_id,
        )
    )


def get_public_diagnosis_job(
    db: Session,
    *,
    diagnosis_id: UUID,
    lead_id: UUID,
    gym_id: UUID,
) -> CoreAsyncJob | None:
    return db.scalar(
        select(CoreAsyncJob).where(
            CoreAsyncJob.id == diagnosis_id,
            CoreAsyncJob.gym_id == gym_id,
            CoreAsyncJob.related_entity_type == "lead",
            CoreAsyncJob.related_entity_id == lead_id,
            CoreAsyncJob.job_type == CORE_ASYNC_JOB_TYPE_PUBLIC_DIAGNOSIS,
        )
    )


def _claim_next_job(db: Session, *, worker_id: str) -> CoreAsyncJob | None:
    now = _utcnow()
    stale_before = now - _STALE_LOCK_AFTER
    job = db.scalar(
        include_all_tenants(
            select(CoreAsyncJob)
            .where(
                or_(
                    CoreAsyncJob.status == "pending",
                    and_(CoreAsyncJob.status == "retry_scheduled", CoreAsyncJob.next_retry_at.is_not(None), CoreAsyncJob.next_retry_at <= now),
                    and_(CoreAsyncJob.status == "processing", CoreAsyncJob.locked_at.is_not(None), CoreAsyncJob.locked_at < stale_before),
                )
            )
            .order_by(
                case((CoreAsyncJob.status == "pending", 0), else_=1),
                CoreAsyncJob.created_at.asc(),
            )
            .with_for_update(skip_locked=True)
            .limit(1),
            reason="core_async_jobs.claim_next_job",
        )
    )
    if job is None:
        return None

    job.status = "processing"
    job.started_at = job.started_at or now
    job.completed_at = None
    job.locked_at = now
    job.locked_by = worker_id
    job.error_code = None
    job.error_message_redacted = None
    job.next_retry_at = None
    job.attempt_count += 1
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Core async job claimed.", extra=_job_log_extra(job, event="core_async_job_claimed", status="processing"))
    return job


def _mark_job_completed(db: Session, job: CoreAsyncJob, *, result: dict[str, Any] | None) -> None:
    job.status = "completed"
    job.completed_at = _utcnow()
    job.locked_at = None
    job.locked_by = None
    job.error_code = None
    job.error_message_redacted = None
    job.result_json = result
    db.add(job)
    db.commit()
    logger.info("Core async job completed.", extra=_job_log_extra(job, event="core_async_job_completed", status="completed"))


def _mark_job_retry(db: Session, job: CoreAsyncJob, *, error_code: str, error_message: str) -> None:
    delay_index = max(job.attempt_count - 1, 0)
    if job.attempt_count >= job.max_attempts or delay_index >= len(_RETRY_DELAYS_MINUTES):
        _mark_job_failed(db, job, error_code=error_code, error_message=error_message)
        return
    job.status = "retry_scheduled"
    job.completed_at = None
    job.locked_at = None
    job.locked_by = None
    job.error_code = error_code[:80]
    job.error_message_redacted = error_message[:1000]
    job.next_retry_at = _utcnow() + timedelta(minutes=_RETRY_DELAYS_MINUTES[delay_index])
    db.add(job)
    db.commit()
    logger.warning(
        "Core async job scheduled for retry.",
        extra=_job_log_extra(
            job,
            event="core_async_job_retry_scheduled",
            status="retry_scheduled",
            error_code=job.error_code,
            next_retry_at=job.next_retry_at.isoformat() if job.next_retry_at else None,
        ),
    )


def _mark_job_failed(db: Session, job: CoreAsyncJob, *, error_code: str, error_message: str) -> None:
    if job.job_type == CORE_ASYNC_JOB_TYPE_PUBLIC_DIAGNOSIS:
        _record_public_diagnosis_terminal_failure(db, job, error_message=error_message)
    job.status = "failed"
    job.completed_at = _utcnow()
    job.locked_at = None
    job.locked_by = None
    job.error_code = error_code[:80]
    job.error_message_redacted = error_message[:1000]
    db.add(job)
    db.commit()
    logger.warning(
        "Core async job failed terminally.",
        extra=_job_log_extra(
            job,
            event="core_async_job_failed_terminal",
            status="failed",
            error_code=job.error_code,
        ),
    )


def process_pending_core_async_jobs(*, batch_size: int = 5) -> int:
    processed_count = 0
    worker_id = _worker_id()

    while processed_count < batch_size:
        db = SessionLocal()
        job: CoreAsyncJob | None = None
        try:
            job = _claim_next_job(db, worker_id=worker_id)
            if job is None:
                break

            set_current_gym_id(job.gym_id)
            result = _dispatch_core_async_job(db, job)
            _mark_job_completed(db, job, result=result)
            processed_count += 1
        except CoreAsyncJobNonRetryableError as exc:
            logger.warning(
                "Core async job failed without retry.",
                extra={"extra_fields": {"event": "core_async_job_failed_non_retryable", "job_id": str(job.id) if job else None, "job_type": job.job_type if job else None, "error_code": exc.code}},
            )
            db.rollback()
            if job is not None:
                _mark_job_failed(db, job, error_code=exc.code, error_message=exc.message)
        except Exception as exc:
            logger.exception(
                "Core async job failed with retry scheduling.",
                extra={"extra_fields": {"event": "core_async_job_failed_retryable", "job_id": str(job.id) if job else None, "job_type": job.job_type if job else None}},
            )
            db.rollback()
            if job is not None:
                _mark_job_retry(db, job, error_code="unexpected_error", error_message=str(exc))
        finally:
            clear_current_gym_id()
            db.close()

    return processed_count


def _dispatch_core_async_job(db: Session, job: CoreAsyncJob) -> dict[str, Any]:
    if job.job_type == CORE_ASYNC_JOB_TYPE_PUBLIC_DIAGNOSIS:
        return _execute_public_diagnosis_job(db, job)
    if job.job_type == CORE_ASYNC_JOB_TYPE_LEAD_PROPOSAL_DISPATCH:
        return _execute_lead_proposal_dispatch_job(db, job)
    if job.job_type == CORE_ASYNC_JOB_TYPE_NPS_DISPATCH:
        return _execute_nps_dispatch_job(db, job)
    if job.job_type == CORE_ASYNC_JOB_TYPE_MONTHLY_REPORTS_DISPATCH:
        return _execute_monthly_reports_dispatch_job(db, job)
    if job.job_type == CORE_ASYNC_JOB_TYPE_WHATSAPP_WEBHOOK_SETUP:
        return _execute_whatsapp_webhook_setup_job(db, job)
    raise CoreAsyncJobNonRetryableError("unsupported_job_type", f"Tipo de job nao suportado: {job.job_type}")


def _execute_public_diagnosis_job(db: Session, job: CoreAsyncJob) -> dict[str, Any]:
    from app.services.diagnosis_service import execute_public_diagnosis_job

    if not job.related_entity_id:
        raise CoreAsyncJobNonRetryableError("missing_lead", "Job de diagnostico sem lead associado")
    if not job.payload_blob:
        raise CoreAsyncJobNonRetryableError("missing_csv_payload", "Job de diagnostico sem CSV persistido")
    payload = dict(job.payload_json or {})
    request_meta = payload.pop("__request_meta", {}) if isinstance(payload.get("__request_meta"), dict) else {}
    try:
        csv_content = base64.b64decode(job.payload_blob.encode("ascii"))
    except Exception as exc:
        raise CoreAsyncJobNonRetryableError("invalid_csv_payload", "Payload CSV do diagnostico esta corrompido") from exc
    result = execute_public_diagnosis_job(
        db,
        diagnosis_id=job.id,
        lead_id=job.related_entity_id,
        payload=payload,
        csv_content=csv_content,
        requester_ip=request_meta.get("requester_ip"),
        user_agent=request_meta.get("user_agent"),
    )
    return result


def _execute_lead_proposal_dispatch_job(db: Session, job: CoreAsyncJob) -> dict[str, Any]:
    from app.services.call_script_service import execute_lead_proposal_dispatch_job

    lead_id_raw = (job.payload_json or {}).get("lead_id")
    lead_id = job.related_entity_id
    if lead_id is None and isinstance(lead_id_raw, str):
        lead_id = UUID(lead_id_raw)
    if lead_id is None:
        raise CoreAsyncJobNonRetryableError("missing_lead", "Job de proposta sem lead associado")
    return execute_lead_proposal_dispatch_job(db, lead_id=lead_id, job_id=job.id)


def _execute_nps_dispatch_job(db: Session, job: CoreAsyncJob) -> dict[str, Any]:
    from app.services.nps_service import execute_nps_dispatch_job

    return execute_nps_dispatch_job(
        db,
        gym_id=job.gym_id,
        job_id=job.id,
        requested_by_user_id=job.requested_by_user_id,
    )


def _execute_monthly_reports_dispatch_job(db: Session, job: CoreAsyncJob) -> dict[str, Any]:
    from app.services.report_service import execute_monthly_reports_dispatch_job

    return execute_monthly_reports_dispatch_job(
        db,
        gym_id=job.gym_id,
        job_id=job.id,
        requested_by_user_id=job.requested_by_user_id,
    )


def _execute_whatsapp_webhook_setup_job(db: Session, job: CoreAsyncJob) -> dict[str, Any]:
    from app.services.evolution_service import configure_webhook

    payload = job.payload_json or {}
    instance = str(payload.get("instance") or "").strip()
    webhook_url = str(payload.get("webhook_url") or "").strip()
    webhook_headers = payload.get("webhook_headers")

    if not instance or not webhook_url:
        raise CoreAsyncJobNonRetryableError(
            "missing_whatsapp_webhook_payload",
            "Job de configuracao do webhook do WhatsApp sem payload obrigatorio",
        )

    configured = configure_webhook(
        instance,
        webhook_url,
        webhook_headers if isinstance(webhook_headers, dict) else None,
    )
    if not configured:
        raise RuntimeError("Falha ao configurar webhook do WhatsApp na Evolution API")

    return {
        "configured": True,
        "instance": instance,
        "webhook_url": webhook_url,
    }


def _record_public_diagnosis_terminal_failure(db: Session, job: CoreAsyncJob, *, error_message: str) -> None:
    from app.services.diagnosis_service import record_public_diagnosis_failure

    if not job.related_entity_id:
        return
    payload = dict(job.payload_json or {})
    request_meta = payload.pop("__request_meta", {}) if isinstance(payload.get("__request_meta"), dict) else {}
    record_public_diagnosis_failure(
        db,
        diagnosis_id=job.id,
        lead_id=job.related_entity_id,
        payload=payload,
        error_message=error_message,
        traceback_snippet="durable-job-terminal-failure",
        requester_ip=request_meta.get("requester_ip"),
        user_agent=request_meta.get("user_agent"),
    )
