import logging
from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from time import perf_counter

from apscheduler.schedulers.background import BackgroundScheduler

from app.background_jobs.jobs import (
    actuar_sync_queue_job,
    booking_reminder_job,
    core_async_jobs_queue_job,
    daily_automations_job,
    daily_crm_followup_job,
    daily_loyalty_update_job,
    daily_nps_dispatch_job,
    daily_onboarding_score_job,
    daily_preferred_shift_sync_job,
    daily_retention_intelligence_job,
    daily_risk_job,
    monthly_reports_job,
    nurturing_followup_job,
    proposal_followup_job,
    refresh_dashboard_views_job,
    risk_recalculation_queue_job,
    sunday_briefing_job,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# IMPORTANTE: Em ambientes multi-worker (ex: Gunicorn com varios workers), apenas UMA
# instancia deve iniciar o scheduler para evitar execucao duplicada dos jobs.
# Configure ENABLE_SCHEDULER=false em todos os workers API e use um processo
# dedicado (worker.py) para rodar o scheduler. Ex: Railway usa dois servicos separados.


def instrument_scheduler_job(job_name: str, func: Callable[..., object]) -> Callable[..., object]:
    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        started_at = datetime.now(timezone.utc)
        started_at_iso = started_at.isoformat()
        started_perf = perf_counter()
        logger.info(
            "Scheduler job started.",
            extra={
                "extra_fields": {
                    "event": "job_started",
                    "job_name": job_name,
                    "status": "started",
                    "started_at": started_at_iso,
                }
            },
        )
        try:
            result = func(*args, **kwargs)
        except Exception:
            finished_at = datetime.now(timezone.utc)
            logger.exception(
                "Scheduler job failed.",
                extra={
                    "extra_fields": {
                        "event": "job_failed",
                        "job_name": job_name,
                        "status": "failed",
                        "started_at": started_at_iso,
                        "finished_at": finished_at.isoformat(),
                        "duration_ms": int((perf_counter() - started_perf) * 1000),
                    }
                },
            )
            raise

        finished_at = datetime.now(timezone.utc)
        logger.info(
            "Scheduler job completed.",
            extra={
                "extra_fields": {
                    "event": "job_completed",
                    "job_name": job_name,
                    "status": "completed",
                    "started_at": started_at_iso,
                    "finished_at": finished_at.isoformat(),
                    "duration_ms": int((perf_counter() - started_perf) * 1000),
                }
            },
        )
        return result

    return wrapper


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    # coalesce=True: if a job was missed (e.g. container restart), run it ONCE instead of catching up
    # misfire_grace_time=3600: ignore misfires older than 1h (prevents stale duplicate runs)
    _CRON_DEFAULTS = {"coalesce": True, "misfire_grace_time": 3600}
    scheduler.add_job(
        instrument_scheduler_job("daily_risk", daily_risk_job),
        trigger="cron",
        hour=2,
        minute=0,
        id="risk_daily",
        **_CRON_DEFAULTS,
    )
    # Retention intelligence runs after risk, before automations
    scheduler.add_job(
        instrument_scheduler_job("daily_retention_intelligence", daily_retention_intelligence_job),
        trigger="cron",
        hour=2,
        minute=15,
        id="retention_intelligence_daily",
        **_CRON_DEFAULTS,
    )
    # Automations run after risk scoring so rules using risk_level have fresh data
    scheduler.add_job(
        instrument_scheduler_job("daily_automations", daily_automations_job),
        trigger="cron",
        hour=2,
        minute=30,
        id="automations_daily",
        **_CRON_DEFAULTS,
    )
    # Onboarding score runs in the early morning
    scheduler.add_job(
        instrument_scheduler_job("daily_onboarding_score", daily_onboarding_score_job),
        trigger="cron",
        hour=1,
        minute=30,
        id="onboarding_score_daily",
        **_CRON_DEFAULTS,
    )
    scheduler.add_job(
        instrument_scheduler_job("daily_nps_dispatch", daily_nps_dispatch_job),
        trigger="cron",
        hour=9,
        minute=0,
        id="nps_daily",
        **_CRON_DEFAULTS,
    )
    scheduler.add_job(
        instrument_scheduler_job("daily_crm_followup", daily_crm_followup_job),
        trigger="cron",
        hour=8,
        minute=0,
        id="crm_followup_daily",
        **_CRON_DEFAULTS,
    )
    scheduler.add_job(
        instrument_scheduler_job("monthly_reports", monthly_reports_job),
        trigger="cron",
        day=1,
        hour=6,
        minute=0,
        id="monthly_reports",
        **_CRON_DEFAULTS,
    )
    scheduler.add_job(
        instrument_scheduler_job("refresh_dashboard_views", refresh_dashboard_views_job),
        trigger="cron",
        minute="*/30",
        id="refresh_dashboard_views",
        coalesce=True,
    )
    scheduler.add_job(
        instrument_scheduler_job("daily_loyalty_update", daily_loyalty_update_job),
        trigger="cron",
        hour=3,
        minute=0,
        id="loyalty_update_daily",
        **_CRON_DEFAULTS,
    )
    scheduler.add_job(
        instrument_scheduler_job("daily_preferred_shift_sync", daily_preferred_shift_sync_job),
        trigger="cron",
        hour=3,
        minute=20,
        id="preferred_shift_sync_daily",
        **_CRON_DEFAULTS,
    )
    scheduler.add_job(
        instrument_scheduler_job("sunday_briefing", sunday_briefing_job),
        trigger="cron",
        day_of_week="sun",
        hour=8,
        minute=0,
        id="sunday_briefing",
        **_CRON_DEFAULTS,
    )
    scheduler.add_job(
        instrument_scheduler_job("nurturing_followup", nurturing_followup_job),
        trigger="cron",
        minute=0,
        id="nurturing_followup_hourly",
        **_CRON_DEFAULTS,
    )
    scheduler.add_job(
        instrument_scheduler_job("actuar_sync_queue", actuar_sync_queue_job),
        trigger="cron",
        minute="*/1",
        id="actuar_sync_queue",
        coalesce=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        instrument_scheduler_job("risk_recalculation_queue", risk_recalculation_queue_job),
        trigger="cron",
        minute="*/1",
        id="risk_recalculation_queue",
        coalesce=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        instrument_scheduler_job("core_async_jobs_queue", core_async_jobs_queue_job),
        trigger="cron",
        minute="*/1",
        id="core_async_jobs_queue",
        coalesce=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        instrument_scheduler_job("booking_reminder", booking_reminder_job),
        trigger="cron",
        minute="*/10",
        id="booking_reminder",
        **_CRON_DEFAULTS,
    )
    scheduler.add_job(
        instrument_scheduler_job("proposal_followup", proposal_followup_job),
        trigger="cron",
        minute=15,
        id="proposal_followup_hourly",
        **_CRON_DEFAULTS,
    )
    return scheduler


def should_start_scheduler_in_api() -> bool:
    return settings.enable_scheduler and settings.enable_scheduler_in_api


def should_start_scheduler_in_worker() -> bool:
    return settings.enable_scheduler
