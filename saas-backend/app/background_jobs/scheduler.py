from apscheduler.schedulers.background import BackgroundScheduler

from app.background_jobs.jobs import (
    daily_crm_followup_job,
    daily_nps_dispatch_job,
    daily_risk_job,
    monthly_reports_job,
    refresh_dashboard_views_job,
)


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(daily_risk_job, trigger="cron", hour=2, minute=0, id="risk_daily")
    scheduler.add_job(daily_nps_dispatch_job, trigger="cron", hour=9, minute=0, id="nps_daily")
    scheduler.add_job(daily_crm_followup_job, trigger="cron", hour=8, minute=0, id="crm_followup_daily")
    scheduler.add_job(monthly_reports_job, trigger="cron", day=1, hour=6, minute=0, id="monthly_reports")
    scheduler.add_job(refresh_dashboard_views_job, trigger="cron", minute="*/30", id="refresh_dashboard_views")
    return scheduler
