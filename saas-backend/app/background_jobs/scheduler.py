from apscheduler.schedulers.background import BackgroundScheduler

from app.background_jobs.jobs import (
    booking_reminder_job,
    daily_automations_job,
    daily_crm_followup_job,
    daily_loyalty_update_job,
    daily_nps_dispatch_job,
    daily_onboarding_score_job,
    daily_retention_intelligence_job,
    daily_risk_job,
    monthly_reports_job,
    nurturing_followup_job,
    proposal_followup_job,
    refresh_dashboard_views_job,
    sunday_briefing_job,
)

# IMPORTANTE: Em ambientes multi-worker (ex: Gunicorn com varios workers), apenas UMA
# instancia deve iniciar o scheduler para evitar execucao duplicada dos jobs.
# Configure ENABLE_SCHEDULER=false em todos os workers API e use um processo
# dedicado (worker.py) para rodar o scheduler. Ex: Railway usa dois servicos separados.


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    # coalesce=True: if a job was missed (e.g. container restart), run it ONCE instead of catching up
    # misfire_grace_time=3600: ignore misfires older than 1h (prevents stale duplicate runs)
    _CRON_DEFAULTS = {"coalesce": True, "misfire_grace_time": 3600}
    scheduler.add_job(daily_risk_job, trigger="cron", hour=2, minute=0, id="risk_daily", **_CRON_DEFAULTS)
    # Retention intelligence runs after risk, before automations
    scheduler.add_job(daily_retention_intelligence_job, trigger="cron", hour=2, minute=15, id="retention_intelligence_daily", **_CRON_DEFAULTS)
    # Automations run after risk scoring so rules using risk_level have fresh data
    scheduler.add_job(daily_automations_job, trigger="cron", hour=2, minute=30, id="automations_daily", **_CRON_DEFAULTS)
    # Onboarding score runs in the early morning
    scheduler.add_job(daily_onboarding_score_job, trigger="cron", hour=1, minute=30, id="onboarding_score_daily", **_CRON_DEFAULTS)
    scheduler.add_job(daily_nps_dispatch_job, trigger="cron", hour=9, minute=0, id="nps_daily", **_CRON_DEFAULTS)
    scheduler.add_job(daily_crm_followup_job, trigger="cron", hour=8, minute=0, id="crm_followup_daily", **_CRON_DEFAULTS)
    scheduler.add_job(monthly_reports_job, trigger="cron", day=1, hour=6, minute=0, id="monthly_reports", **_CRON_DEFAULTS)
    scheduler.add_job(refresh_dashboard_views_job, trigger="cron", minute="*/30", id="refresh_dashboard_views", coalesce=True)
    scheduler.add_job(daily_loyalty_update_job, trigger="cron", hour=3, minute=0, id="loyalty_update_daily", **_CRON_DEFAULTS)
    scheduler.add_job(sunday_briefing_job, trigger="cron", day_of_week="sun", hour=8, minute=0, id="sunday_briefing", **_CRON_DEFAULTS)
    scheduler.add_job(nurturing_followup_job, trigger="cron", minute=0, id="nurturing_followup_hourly", **_CRON_DEFAULTS)
    scheduler.add_job(booking_reminder_job, trigger="cron", minute="*/10", id="booking_reminder", **_CRON_DEFAULTS)
    scheduler.add_job(proposal_followup_job, trigger="cron", minute=15, id="proposal_followup_hourly", **_CRON_DEFAULTS)
    return scheduler
