import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache, make_cache_key
from app.models import AuditLog, Checkin, Member

logger = logging.getLogger(__name__)

_AUTOMATION_ACTIONS = (
    "automation_3d",
    "automation_7d",
    "automation_10d",
    "automation_14d",
    "automation_21d",
    "automation_executed",
)


def get_roi_summary(db: Session, period_days: int = 30) -> dict:
    cache_key = make_cache_key("dashboard_roi", period_days)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=period_days)

    automated_members = db.execute(
        select(AuditLog.member_id, func.min(AuditLog.created_at).label("first_action"))
        .where(
            AuditLog.action.in_(_AUTOMATION_ACTIONS),
            AuditLog.created_at >= cutoff,
            AuditLog.member_id.is_not(None),
        )
        .group_by(AuditLog.member_id)
    ).all()

    total_automated = len(automated_members)
    reengaged_count = 0
    preserved_revenue = Decimal("0.00")
    reengaged_members: list[dict] = []

    for row in automated_members:
        member_id = row.member_id
        first_action_at = row.first_action

        checkin_after = db.scalar(
            select(Checkin.id).where(
                Checkin.member_id == member_id,
                Checkin.checkin_at > first_action_at,
            ).limit(1)
        )
        if checkin_after:
            reengaged_count += 1
            member = db.scalar(select(Member).where(Member.id == member_id))
            if member:
                preserved_revenue += member.monthly_fee or Decimal("0.00")
                reengaged_members.append({
                    "member_id": str(member.id),
                    "full_name": member.full_name,
                    "monthly_fee": float(member.monthly_fee or 0),
                })

    reengagement_rate = (reengaged_count / total_automated * 100) if total_automated > 0 else 0.0

    result = {
        "period_days": period_days,
        "total_automated": total_automated,
        "reengaged_count": reengaged_count,
        "reengagement_rate": round(reengagement_rate, 1),
        "preserved_revenue": float(preserved_revenue),
        "top_reengaged": reengaged_members[:10],
    }

    dashboard_cache.set(cache_key, result, ttl=600)
    return result
