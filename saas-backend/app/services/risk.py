from dataclasses import dataclass
from datetime import datetime, timezone

from app.models import Member, RiskLevel


@dataclass(frozen=True)
class RiskResult:
    """Immutable result of risk calculation."""

    score: int
    level: RiskLevel


def calculate_risk_score(member: Member) -> RiskResult:
    """
    Calculate churn risk score for a gym member.

    Rules:
    - 7-13 days without check-in: +15 points
    - 14-20 days without check-in: +30 points
    - 21+ days without check-in: +40 points

    Risk levels:
    - green: score 0-29
    - yellow: score 30-59
    - red: score 60-100

    Args:
        member: The gym member to evaluate

    Returns:
        RiskResult with score (0-100) and risk level
    """
    score = 0

    if member.last_checkin is None:
        days_since_checkin = _days_since(member.join_date)
    else:
        days_since_checkin = _days_since(member.last_checkin)

    if days_since_checkin >= 21:
        score += 40
    elif days_since_checkin >= 14:
        score += 30
    elif days_since_checkin >= 7:
        score += 15

    score = min(score, 100)

    level = _determine_level(score)

    return RiskResult(score=score, level=level)


def _days_since(dt: datetime) -> int:
    """Calculate days since a given datetime."""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    return delta.days


def _determine_level(score: int) -> RiskLevel:
    """Determine risk level based on score."""
    if score >= 60:
        return RiskLevel.RED
    if score >= 30:
        return RiskLevel.YELLOW
    return RiskLevel.GREEN
