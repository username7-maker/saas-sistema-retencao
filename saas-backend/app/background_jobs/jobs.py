from sqlalchemy import select

from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import Gym
from app.services.analytics_view_service import refresh_member_kpis_materialized_view
from app.services.crm_service import run_followup_automation
from app.services.nps_service import run_nps_dispatch
from app.services.report_service import send_monthly_reports
from app.services.risk import run_daily_risk_processing


def daily_risk_job() -> None:
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            run_daily_risk_processing(db)
    finally:
        clear_current_gym_id()
        db.close()


def daily_nps_dispatch_job() -> None:
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            run_nps_dispatch(db)
    finally:
        clear_current_gym_id()
        db.close()


def daily_crm_followup_job() -> None:
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            run_followup_automation(db)
    finally:
        clear_current_gym_id()
        db.close()


def monthly_reports_job() -> None:
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            send_monthly_reports(db)
    finally:
        clear_current_gym_id()
        db.close()


def refresh_dashboard_views_job() -> None:
    db = SessionLocal()
    try:
        refresh_member_kpis_materialized_view(db)
    finally:
        db.close()


def _active_gyms(db):
    return db.scalars(select(Gym).where(Gym.is_active.is_(True))).all()
