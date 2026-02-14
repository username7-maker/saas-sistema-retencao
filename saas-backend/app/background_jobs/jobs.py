from app.database import SessionLocal
from app.services.crm_service import run_followup_automation
from app.services.nps_service import run_nps_dispatch
from app.services.risk import run_daily_risk_processing


def daily_risk_job() -> None:
    db = SessionLocal()
    try:
        run_daily_risk_processing(db)
    finally:
        db.close()


def daily_nps_dispatch_job() -> None:
    db = SessionLocal()
    try:
        run_nps_dispatch(db)
    finally:
        db.close()


def daily_crm_followup_job() -> None:
    db = SessionLocal()
    try:
        run_followup_automation(db)
    finally:
        db.close()
