import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.database import SessionLocal, clear_current_gym_id, include_all_tenants, set_current_gym_id
from app.models import CoreAsyncJob, Gym, Lead, RoleEnum, User
from app.models.enums import LeadStage
from app.schemas import LeadCreate
from app.services.core_async_job_service import (
    CORE_ASYNC_JOB_TYPE_LEAD_PROPOSAL_DISPATCH,
    CORE_ASYNC_JOB_TYPE_MONTHLY_REPORTS_DISPATCH,
    CORE_ASYNC_JOB_TYPE_NPS_DISPATCH,
    CORE_ASYNC_JOB_TYPE_WHATSAPP_WEBHOOK_SETUP,
    CoreAsyncJobNonRetryableError,
    _dispatch_core_async_job,
    _mark_job_completed,
    _mark_job_failed,
    _mark_job_retry,
    enqueue_lead_proposal_dispatch_job,
    enqueue_monthly_reports_dispatch_job,
    enqueue_nps_dispatch_job,
    enqueue_whatsapp_webhook_setup_job,
)
from app.services.crm_service import create_lead
from app.services.evolution_service import ensure_instance


SCRIPT_WORKER_ID = "script:pilot-gate-samples"


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _get_gym_by_slug(db, slug: str) -> Gym:
    gym = db.scalar(select(Gym).where(Gym.slug == slug))
    if gym is None:
        raise SystemExit(f"Academia nao encontrada para slug: {slug}")
    return gym


def _get_requesting_user_id(db, gym_id):
    user = db.scalar(
        select(User)
        .where(
            User.gym_id == gym_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            User.role.in_([RoleEnum.OWNER, RoleEnum.MANAGER]),
        )
        .order_by(User.created_at.asc())
        .limit(1)
    )
    return user.id if user else None


def _get_requesting_user(db, gym_id):
    return db.scalar(
        select(User)
        .where(
            User.gym_id == gym_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            User.role.in_([RoleEnum.OWNER, RoleEnum.MANAGER]),
        )
        .order_by(User.created_at.asc())
        .limit(1)
    )


def _set_job_processing(job: CoreAsyncJob) -> None:
    now = _utcnow()
    job.status = "processing"
    job.started_at = job.started_at or now
    job.completed_at = None
    job.locked_at = now
    job.locked_by = SCRIPT_WORKER_ID
    job.error_code = None
    job.error_message_redacted = None
    job.next_retry_at = None
    job.attempt_count += 1


def _execute_job_by_id(job_id) -> dict:
    db = SessionLocal()
    try:
        job = db.scalar(
            include_all_tenants(
                select(CoreAsyncJob).where(CoreAsyncJob.id == job_id).limit(1),
                reason="core_async_jobs.pilot_gate_samples.load_job",
            )
        )
        if job is None:
            raise SystemExit(f"Job nao encontrado: {job_id}")

        _set_job_processing(job)
        db.add(job)
        db.commit()
        db.refresh(job)

        try:
            set_current_gym_id(job.gym_id)
            result = _dispatch_core_async_job(db, job)
            _mark_job_completed(db, job, result=result)
            db.refresh(job)
            return {
                "job_id": str(job.id),
                "job_type": job.job_type,
                "status": job.status,
                "error_code": job.error_code,
                "result": job.result_json,
            }
        except CoreAsyncJobNonRetryableError as exc:
            db.rollback()
            _mark_job_failed(db, job, error_code=exc.code, error_message=exc.message)
            db.refresh(job)
            return {
                "job_id": str(job.id),
                "job_type": job.job_type,
                "status": job.status,
                "error_code": job.error_code,
                "result": job.result_json,
            }
        except Exception as exc:  # pragma: no cover - operational path
            db.rollback()
            _mark_job_retry(db, job, error_code="unexpected_error", error_message=str(exc))
            db.refresh(job)
            return {
                "job_id": str(job.id),
                "job_type": job.job_type,
                "status": job.status,
                "error_code": job.error_code,
                "result": job.result_json,
            }
        finally:
            clear_current_gym_id()
    finally:
        db.close()


def _enqueue_monthly_reports_sample(db, *, gym: Gym, requested_by_user_id):
    job, created = enqueue_monthly_reports_dispatch_job(
        db,
        gym_id=gym.id,
        requested_by_user_id=requested_by_user_id,
    )
    db.commit()
    return {
        "job_id": str(job.id),
        "job_type": CORE_ASYNC_JOB_TYPE_MONTHLY_REPORTS_DISPATCH,
        "created": created,
    }


def _enqueue_nps_sample(db, *, gym: Gym, requested_by_user_id):
    job, created = enqueue_nps_dispatch_job(
        db,
        gym_id=gym.id,
        requested_by_user_id=requested_by_user_id,
    )
    db.commit()
    return {
        "job_id": str(job.id),
        "job_type": CORE_ASYNC_JOB_TYPE_NPS_DISPATCH,
        "created": created,
    }


def _enqueue_whatsapp_sample(db, *, gym: Gym, requested_by_user_id):
    instance = (gym.whatsapp_instance or "").strip() or ensure_instance(str(gym.id))
    webhook_url = f"{settings.public_backend_url.rstrip('/')}/api/v1/whatsapp/webhook"
    job, created = enqueue_whatsapp_webhook_setup_job(
        db,
        gym_id=gym.id,
        requested_by_user_id=requested_by_user_id,
        instance=instance,
        webhook_url=webhook_url,
        webhook_headers={"X-Webhook-Token": settings.whatsapp_webhook_token},
    )
    gym.whatsapp_instance = instance
    gym.whatsapp_status = "connecting"
    db.add(gym)
    db.commit()
    return {
        "job_id": str(job.id),
        "job_type": CORE_ASYNC_JOB_TYPE_WHATSAPP_WEBHOOK_SETUP,
        "created": created,
        "instance": instance,
    }


def _enqueue_lead_proposal_sample(db, *, gym: Gym, requested_by_user):
    target_email = (requested_by_user.email or "").strip() or settings.sendgrid_sender
    lead = create_lead(
        db,
        LeadCreate(
            full_name="Pilot Gate Sample Lead",
            email=target_email,
            phone=None,
            source="pilot_gate_sample",
            stage=LeadStage.PROPOSAL,
            estimated_value=Decimal("2500"),
            acquisition_cost=Decimal("0"),
            owner_id=requested_by_user.id if requested_by_user else None,
            notes=[{"type": "pilot_gate_sample", "created_at": _utcnow().isoformat()}],
        ),
        commit=False,
    )
    db.flush()
    job, created = enqueue_lead_proposal_dispatch_job(
        db,
        gym_id=gym.id,
        lead_id=lead.id,
        requested_by_user_id=requested_by_user.id if requested_by_user else None,
    )
    db.commit()
    return {
        "job_id": str(job.id),
        "job_type": CORE_ASYNC_JOB_TYPE_LEAD_PROPOSAL_DISPATCH,
        "created": created,
        "lead_id": str(lead.id),
        "lead_email": target_email,
        "cleanup_required": True,
    }


def _cleanup_generated_lead(lead_id: str) -> None:
    db = SessionLocal()
    try:
        lead_uuid = UUID(str(lead_id))
        lead = db.scalar(
            include_all_tenants(
                select(Lead).where(Lead.id == lead_uuid).limit(1),
                reason="core_async_jobs.pilot_gate_samples.cleanup_generated_lead",
            )
        )
        if lead is None:
            return
        lead.deleted_at = _utcnow()
        db.add(lead)
        db.commit()
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate controlled pilot samples for 4.3 gate validation.")
    parser.add_argument("--gym-slug", required=True, help="Pilot gym slug.")
    parser.add_argument("--skip-nps", action="store_true", help="Do not create the NPS dispatch sample.")
    parser.add_argument("--skip-monthly", action="store_true", help="Do not create the monthly reports sample.")
    parser.add_argument("--skip-whatsapp", action="store_true", help="Do not create the whatsapp webhook setup sample.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        gym = _get_gym_by_slug(db, args.gym_slug.strip())
        set_current_gym_id(gym.id)
        requested_by_user = _get_requesting_user(db, gym.id)
        requested_by_user_id = requested_by_user.id if requested_by_user else None

        enqueued: list[dict] = []
        if not args.skip_nps:
            enqueued.append(_enqueue_nps_sample(db, gym=gym, requested_by_user_id=requested_by_user_id))
        if not args.skip_monthly and settings.monthly_reports_dispatch_enabled:
            enqueued.append(_enqueue_monthly_reports_sample(db, gym=gym, requested_by_user_id=requested_by_user_id))
        if not args.skip_whatsapp:
            try:
                enqueued.append(_enqueue_whatsapp_sample(db, gym=gym, requested_by_user_id=requested_by_user_id))
            except Exception as exc:
                fallback_item = {
                    "job_id": None,
                    "job_type": CORE_ASYNC_JOB_TYPE_WHATSAPP_WEBHOOK_SETUP,
                    "created": False,
                    "fallback_reason": str(exc),
                }
                enqueued.append(fallback_item)
                if settings.public_proposal_enabled or settings.public_proposal_email_enabled:
                    enqueued.append(_enqueue_lead_proposal_sample(db, gym=gym, requested_by_user=requested_by_user))
    finally:
        clear_current_gym_id()
        db.close()

    executed = [_execute_job_by_id(item["job_id"]) for item in enqueued if item.get("job_id")]
    for item in enqueued:
        if item.get("cleanup_required") and item.get("lead_id"):
            _cleanup_generated_lead(item["lead_id"])
    print(
        json.dumps(
            {
                "gym_slug": args.gym_slug,
                "enqueued": enqueued,
                "executed": executed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
