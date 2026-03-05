from apscheduler.schedulers.background import BackgroundScheduler

from app.background_jobs.jobs import (
    daily_automations_job,
    daily_crm_followup_job,
    daily_loyalty_update_job,
    daily_nps_dispatch_job,
    daily_risk_job,
    monthly_reports_job,
    refresh_dashboard_views_job,
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
    # Automations run after risk scoring so rules using risk_level have fresh data
    scheduler.add_job(daily_automations_job, trigger="cron", hour=2, minute=30, id="automations_daily", **_CRON_DEFAULTS)
    scheduler.add_job(daily_nps_dispatch_job, trigger="cron", hour=9, minute=0, id="nps_daily", **_CRON_DEFAULTS)
    scheduler.add_job(daily_crm_followup_job, trigger="cron", hour=8, minute=0, id="crm_followup_daily", **_CRON_DEFAULTS)
    scheduler.add_job(monthly_reports_job, trigger="cron", day=1, hour=6, minute=0, id="monthly_reports", **_CRON_DEFAULTS)
    scheduler.add_job(refresh_dashboard_views_job, trigger="cron", minute="*/30", id="refresh_dashboard_views", coalesce=True)
    scheduler.add_job(daily_loyalty_update_job, trigger="cron", hour=3, minute=0, id="loyalty_update_daily", **_CRON_DEFAULTS)
    return scheduler
