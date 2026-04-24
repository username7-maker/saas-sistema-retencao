import logging
from datetime import date
from typing import Any

from dateutil.relativedelta import relativedelta
from sqlalchemy import select

from app.core.config import settings
from app.core.distributed_lock import with_distributed_lock
from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id, unscoped_tenant_access
from app.models import Gym
from app.models.member import Member
from app.models.enums import MemberStatus
from app.services.analytics_view_service import refresh_member_kpis_materialized_view
from app.services.automation_engine import run_automation_rules
from app.services.booking_service import process_booking_reminders
from app.services.body_composition_actuar_sync_service import process_pending_actuar_sync_jobs
from app.services.call_script_service import process_proposal_followups
from app.services.core_async_job_service import (
    enqueue_monthly_reports_dispatch_job,
    enqueue_nps_dispatch_job,
    process_pending_core_async_jobs,
)
from app.services.crm_service import run_followup_automation
from app.services.nurturing_service import run_nurturing_followup
from app.services.onboarding_score_service import run_daily_onboarding_score
from app.services.preferred_shift_service import sync_preferred_shifts_from_checkins
from app.services.retention_intelligence_service import run_daily_retention_intelligence
from app.services.risk import run_daily_risk_processing
from app.services.risk_recalculation_service import process_pending_risk_recalculation_requests
from app.services.weekly_briefing_service import generate_and_send_weekly_briefing

logger = logging.getLogger(__name__)


def _critical_lock_fail_open() -> bool:
    return settings.scheduler_critical_lock_fail_open


def _extract_safe_metrics(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        metrics: dict[str, Any] = {}
        for key, value in result.items():
            if isinstance(value, (bool, int, float)):
                metrics[key] = value
        return metrics
    return {}


def _extract_rule_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    rule_ids = sorted({str(item["rule_id"]) for item in results if isinstance(item, dict) and item.get("rule_id")})
    metrics: dict[str, Any] = {"processed_count": len(results)}
    if rule_ids:
        metrics["rule_count"] = len(rule_ids)
        metrics["rule_ids"] = rule_ids[:10]
    return metrics


def _log_job_metrics(job_name: str, *, gym_id: Any = None, result: Any = None, **extra_metrics: Any) -> None:
    extra_fields: dict[str, Any] = {
        "event": "job_iteration_completed",
        "job_name": job_name,
        "status": "completed",
    }
    if gym_id is not None:
        extra_fields["gym_id"] = str(gym_id)
    extra_fields.update(_extract_safe_metrics(result))
    extra_fields.update({key: value for key, value in extra_metrics.items() if value is not None})
    logger.info("Scheduler job iteration completed.", extra={"extra_fields": extra_fields})


def _log_job_failure(job_name: str, *, gym_id: Any = None) -> None:
    extra_fields: dict[str, Any] = {
        "event": "job_iteration_failed",
        "job_name": job_name,
        "status": "failed",
    }
    if gym_id is not None:
        extra_fields["gym_id"] = str(gym_id)
    logger.exception("Scheduler job iteration failed.", extra={"extra_fields": extra_fields})


def _iter_active_members_for_loyalty(db, gym_id, *, batch_size: int):
    offset = 0
    while True:
        members = db.scalars(
            select(Member).where(
                Member.gym_id == gym_id,
                Member.deleted_at.is_(None),
                Member.status == MemberStatus.ACTIVE,
            ).order_by(Member.id.asc()).offset(offset).limit(batch_size)
        ).all()
        if not members:
            break
        yield members
        offset += len(members)
        if len(members) < batch_size:
            break


@with_distributed_lock("daily_risk", ttl_seconds=1800, fail_open=_critical_lock_fail_open)
def daily_risk_job() -> None:
    job_name = "daily_risk"
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                result = run_daily_risk_processing(db)
                _log_job_metrics(job_name, gym_id=gym.id, result=result)
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("daily_nps_dispatch", ttl_seconds=1800, fail_open=_critical_lock_fail_open)
def daily_nps_dispatch_job() -> None:
    job_name = "daily_nps_dispatch"
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                job, created = enqueue_nps_dispatch_job(
                    db,
                    gym_id=gym.id,
                    requested_by_user_id=None,
                )
                db.commit()
                _log_job_metrics(
                    job_name,
                    gym_id=gym.id,
                    queued_job_id=str(job.id),
                    created=int(created),
                    enqueued_count=1 if created else 0,
                    deduped_count=0 if created else 1,
                )
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("daily_crm_followup", ttl_seconds=1800, fail_open=_critical_lock_fail_open)
def daily_crm_followup_job() -> None:
    job_name = "daily_crm_followup"
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                processed_count = run_followup_automation(db)
                db.commit()
                _log_job_metrics(job_name, gym_id=gym.id, processed_count=processed_count)
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("monthly_reports", ttl_seconds=3600, fail_open=_critical_lock_fail_open)
def monthly_reports_job() -> None:
    job_name = "monthly_reports"
    if not settings.monthly_reports_dispatch_enabled:
        logger.info(
            "Monthly reports dispatch disabled by configuration.",
            extra={"extra_fields": {"event": "job_skipped_disabled", "job_name": job_name, "status": "disabled"}},
        )
        return
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                job, created = enqueue_monthly_reports_dispatch_job(
                    db,
                    gym_id=gym.id,
                    requested_by_user_id=None,
                )
                db.commit()
                _log_job_metrics(
                    job_name,
                    gym_id=gym.id,
                    queued_job_id=str(job.id),
                    created=int(created),
                    enqueued_count=1 if created else 0,
                    deduped_count=0 if created else 1,
                )
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("refresh_dashboard_views", ttl_seconds=600)
def refresh_dashboard_views_job() -> None:
    job_name = "refresh_dashboard_views"
    db = SessionLocal()
    try:
        refreshed = refresh_member_kpis_materialized_view(db)
        _log_job_metrics(job_name, refreshed=refreshed)
    finally:
        db.close()


@with_distributed_lock("daily_automations", ttl_seconds=1800, fail_open=_critical_lock_fail_open)
def daily_automations_job() -> None:
    """Executa todas as regras de automacao ativas para cada academia. Roda apos daily_risk_job."""
    job_name = "daily_automations"
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                results = run_automation_rules(db)
                db.commit()
                _log_job_metrics(job_name, gym_id=gym.id, **_extract_rule_metrics(results))
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("daily_loyalty_update", ttl_seconds=1800, fail_open=_critical_lock_fail_open)
def daily_loyalty_update_job() -> None:
    """Recalcula loyalty_months para todos os membros ativos de todas as academias."""
    job_name = "daily_loyalty_update"
    today = date.today()
    batch_size = max(int(settings.loyalty_update_batch_size), 1)
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                processed_count = 0
                for members in _iter_active_members_for_loyalty(db, gym.id, batch_size=batch_size):
                    for member in members:
                        delta = relativedelta(today, member.join_date)
                        member.loyalty_months = max(0, delta.years * 12 + delta.months)
                    processed_count += len(members)
                    db.flush()
                db.commit()
                _log_job_metrics(job_name, gym_id=gym.id, processed_count=processed_count)
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("daily_preferred_shift_sync", ttl_seconds=1800, fail_open=_critical_lock_fail_open)
def daily_preferred_shift_sync_job() -> None:
    """Recalcula preferred_shift dos membros com base no horario dominante dos check-ins recentes."""
    job_name = "daily_preferred_shift_sync"
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                updated_count = sync_preferred_shifts_from_checkins(db, gym_id=gym.id, commit=False, flush=False)
                db.commit()
                _log_job_metrics(job_name, gym_id=gym.id, updated_count=updated_count)
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("sunday_briefing", ttl_seconds=1800, fail_open=_critical_lock_fail_open)
def sunday_briefing_job() -> None:
    """Envia briefing semanal por WhatsApp para owners/managers de cada academia."""
    job_name = "sunday_briefing"
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                result = generate_and_send_weekly_briefing(db, gym.id)
                db.commit()
                _log_job_metrics(job_name, gym_id=gym.id, result=result)
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("nurturing_followup", ttl_seconds=900, fail_open=_critical_lock_fail_open)
def nurturing_followup_job() -> None:
    """Executa a regua de nutricao pendente a cada hora."""
    job_name = "nurturing_followup"
    db = SessionLocal()
    try:
        with unscoped_tenant_access("jobs.nurturing_followup_job"):
            result = run_nurturing_followup(db)
        _log_job_metrics(job_name, result=result)
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("booking_reminder", ttl_seconds=300, fail_open=_critical_lock_fail_open)
def booking_reminder_job() -> None:
    """Envia lembretes duraveis para calls confirmadas 1h antes, com varredura a cada 10 minutos."""
    job_name = "booking_reminder"
    db = SessionLocal()
    try:
        with unscoped_tenant_access("jobs.booking_reminder_job"):
            result = process_booking_reminders(db)
        _log_job_metrics(job_name, result=result)
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("proposal_followup", ttl_seconds=900, fail_open=_critical_lock_fail_open)
def proposal_followup_job() -> None:
    """Cria follow-up manual 24h apos proposta enviada sem conversao."""
    job_name = "proposal_followup"
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                result = process_proposal_followups(db)
                db.commit()
                _log_job_metrics(job_name, gym_id=gym.id, result=result)
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("actuar_sync_queue", ttl_seconds=300, fail_open=_critical_lock_fail_open)
def actuar_sync_queue_job() -> None:
    job_name = "actuar_sync_queue"
    processed_count = process_pending_actuar_sync_jobs(batch_size=3)
    _log_job_metrics(job_name, processed_count=processed_count)


@with_distributed_lock("risk_recalculation_queue", ttl_seconds=300, fail_open=_critical_lock_fail_open)
def risk_recalculation_queue_job() -> None:
    job_name = "risk_recalculation_queue"
    processed_count = process_pending_risk_recalculation_requests(batch_size=3)
    _log_job_metrics(job_name, processed_count=processed_count)


@with_distributed_lock("core_async_jobs_queue", ttl_seconds=300, fail_open=_critical_lock_fail_open)
def core_async_jobs_queue_job() -> None:
    job_name = "core_async_jobs_queue"
    processed_count = process_pending_core_async_jobs(batch_size=5)
    _log_job_metrics(job_name, processed_count=processed_count)


@with_distributed_lock("daily_onboarding_score", ttl_seconds=900, fail_open=_critical_lock_fail_open)
def daily_onboarding_score_job() -> None:
    """Recalcula onboarding score para membros nos primeiros 30 dias."""
    job_name = "daily_onboarding_score"
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                result = run_daily_onboarding_score(db)
                _log_job_metrics(job_name, gym_id=gym.id, result=result)
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("daily_retention_intelligence", ttl_seconds=1800, fail_open=_critical_lock_fail_open)
def daily_retention_intelligence_job() -> None:
    """Classifica churn e materializa playbooks de retencao. Roda apos daily_risk_job."""
    job_name = "daily_retention_intelligence"
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                result = run_daily_retention_intelligence(db)
                _log_job_metrics(job_name, gym_id=gym.id, result=result)
            except Exception:
                _log_job_failure(job_name, gym_id=gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


def _active_gyms(db) -> list[Gym]:
    return db.scalars(select(Gym).where(Gym.is_active.is_(True))).all()
