import logging
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import select

from app.core.distributed_lock import with_distributed_lock
from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id, set_unscoped_access
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
from app.services.onboarding_score_service import run_daily_onboarding_score
from app.services.report_service import send_monthly_reports
from app.services.retention_intelligence_service import run_daily_retention_intelligence
from app.services.risk import run_daily_risk_processing
from app.services.weekly_briefing_service import generate_and_send_weekly_briefing

logger = logging.getLogger(__name__)


@with_distributed_lock("daily_risk", ttl_seconds=1800)
def daily_risk_job() -> None:
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                run_daily_risk_processing(db)
            except Exception:
                logger.exception("Risk processing failed for gym %s", gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("daily_nps_dispatch", ttl_seconds=1800)
def daily_nps_dispatch_job() -> None:
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            run_nps_dispatch(db)
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("daily_crm_followup", ttl_seconds=1800)
def daily_crm_followup_job() -> None:
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            run_followup_automation(db)
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("monthly_reports", ttl_seconds=3600)
def monthly_reports_job() -> None:
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            set_current_gym_id(gym.id)
            send_monthly_reports(db)
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("refresh_dashboard_views", ttl_seconds=600)
def refresh_dashboard_views_job() -> None:
    db = SessionLocal()
    try:
        refresh_member_kpis_materialized_view(db)
    finally:
        db.close()


@with_distributed_lock("daily_automations", ttl_seconds=1800)
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


@with_distributed_lock("daily_loyalty_update", ttl_seconds=1800)
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


@with_distributed_lock("sunday_briefing", ttl_seconds=1800)
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


@with_distributed_lock("nurturing_followup", ttl_seconds=900)
def nurturing_followup_job() -> None:
    """Executa a regua de nutricao pendente a cada hora."""
    db = SessionLocal()
    try:
        set_unscoped_access(True)  # Cross-gym: processes all pending sequences
        run_nurturing_followup(db)
    finally:
        set_unscoped_access(False)
        clear_current_gym_id()
        db.close()


@with_distributed_lock("booking_reminder", ttl_seconds=300)
def booking_reminder_job() -> None:
    """Envia lembretes duraveis para calls confirmadas 1h antes, com varredura a cada 10 minutos."""
    db = SessionLocal()
    try:
        set_unscoped_access(True)  # Cross-gym: processes bookings across all gyms
        process_booking_reminders(db)
    finally:
        set_unscoped_access(False)
        clear_current_gym_id()
        db.close()


@with_distributed_lock("proposal_followup", ttl_seconds=900)
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


@with_distributed_lock("daily_onboarding_score", ttl_seconds=900)
def daily_onboarding_score_job() -> None:
    """Recalcula onboarding score para membros nos primeiros 30 dias."""
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                run_daily_onboarding_score(db)
            except Exception:
                logger.exception("Onboarding score job failed for gym %s", gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


@with_distributed_lock("daily_retention_intelligence", ttl_seconds=1800)
def daily_retention_intelligence_job() -> None:
    """Classifica churn e materializa playbooks de retencao. Roda apos daily_risk_job."""
    db = SessionLocal()
    try:
        for gym in _active_gyms(db):
            try:
                set_current_gym_id(gym.id)
                run_daily_retention_intelligence(db)
            except Exception:
                logger.exception("Retention intelligence job failed for gym %s", gym.id)
                db.rollback()
    finally:
        clear_current_gym_id()
        db.close()


def _active_gyms(db):
    return db.scalars(select(Gym).where(Gym.is_active.is_(True))).all()
