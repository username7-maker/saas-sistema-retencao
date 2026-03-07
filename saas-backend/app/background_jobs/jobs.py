from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import select

from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import Gym
from app.models.member import Member
from app.models.enums import MemberStatus
from app.services.analytics_view_service import refresh_member_kpis_materialized_view
from app.services.automation_engine import run_automation_rules
from app.services.booking_service import process_booking_reminders
from app.services.call_script_service import process_proposal_followups
from app.services.crm_service import run_followup_automation
from app.services.nurturing_service import run_nurturing_followup
from app.services.nps_service import run_nps_dispatch
from app.services.report_service import send_monthly_reports
from app.services.risk import run_daily_risk_processing
from app.services.weekly_briefing_service import generate_and_send_weekly_briefing


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


def daily_automations_job() -> None:
    """Executa todas as regras de automacao ativas para cada academia. Roda apos daily_risk_job."""
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            run_automation_rules(db)
    finally:
        clear_current_gym_id()
        db.close()


def daily_loyalty_update_job() -> None:
    """Recalcula loyalty_months para todos os membros ativos de todas as academias."""
    today = date.today()
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            members = db.scalars(
                select(Member).where(
                    Member.gym_id == gym.id,
                    Member.deleted_at.is_(None),
                    Member.status == MemberStatus.ACTIVE,
                )
            ).all()
            for member in members:
                delta = relativedelta(today, member.join_date)
                member.loyalty_months = max(0, delta.years * 12 + delta.months)
        db.commit()
    finally:
        clear_current_gym_id()
        db.close()


def sunday_briefing_job() -> None:
    """Envia briefing semanal por WhatsApp para owners/managers de cada academia."""
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            generate_and_send_weekly_briefing(db, gym.id)
    finally:
        clear_current_gym_id()
        db.close()


def nurturing_followup_job() -> None:
    """Executa a regua de nutricao pendente a cada hora."""
    db = SessionLocal()
    try:
        run_nurturing_followup(db)
    finally:
        clear_current_gym_id()
        db.close()


def booking_reminder_job() -> None:
    """Envia lembretes duraveis para calls confirmadas 1h antes, com varredura a cada 10 minutos."""
    db = SessionLocal()
    try:
        process_booking_reminders(db)
    finally:
        clear_current_gym_id()
        db.close()


def proposal_followup_job() -> None:
    """Cria follow-up manual 24h apos proposta enviada sem conversao."""
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            process_proposal_followups(db)
    finally:
        clear_current_gym_id()
        db.close()


def _active_gyms(db):
    return db.scalars(select(Gym).where(Gym.is_active.is_(True))).all()
