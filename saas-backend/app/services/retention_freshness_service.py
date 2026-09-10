from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Checkin
from app.schemas.dashboard import RetentionDataFreshness


def get_retention_freshness(db: Session, gym_id) -> RetentionDataFreshness | None:
    if gym_id is None:
        return None
    latest = db.scalar(select(func.max(Checkin.checkin_at)).where(Checkin.gym_id == gym_id))
    audit = db.scalar(
        select(AuditLog).where(
            AuditLog.gym_id == gym_id,
            AuditLog.action == "import_checkins_csv",
            AuditLog.entity == "checkins",
        ).order_by(AuditLog.created_at.desc()).limit(1)
    )
    codes = (audit.details or {}).get("coverage_warning_codes", []) if audit else []
    return RetentionDataFreshness(
        last_import_at=audit.created_at if audit else None,
        latest_checkin_at=latest,
        coverage_verified=False,
        warning_codes=[code for code in codes if code in {"possible_access_gap"}],
    )
