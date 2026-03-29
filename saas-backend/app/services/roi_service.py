from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache, make_cache_key
from app.models import Checkin, Member, OperationalOutcome, User

_IGNORED_OUTCOME_STATUSES = {"failed", "ignored"}


def _normalize_group_key(value: str | None, fallback: str) -> str:
    normalized = (value or "").strip()
    return normalized or fallback


def get_roi_summary(db: Session, period_days: int = 30) -> dict:
    cache_key = make_cache_key("dashboard_roi", period_days)
    cached = dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=period_days)

    outcomes = db.scalars(
        select(OperationalOutcome).where(
            OperationalOutcome.occurred_at >= cutoff,
            OperationalOutcome.status.notin_(tuple(_IGNORED_OUTCOME_STATUSES)),
        )
    ).all()

    actions_executed = len(outcomes)
    total_automated = sum(1 for outcome in outcomes if outcome.actor == "automation")

    if not outcomes:
        result = {
            "period_days": period_days,
            "labeling": "estimativa_operacional",
            "actions_executed": 0,
            "total_automated": 0,
            "reengaged_count": 0,
            "reengagement_rate": 0.0,
            "preserved_revenue": 0.0,
            "recovery_rate": 0.0,
            "top_playbooks": [],
            "top_channels": [],
            "top_operators": [],
            "top_reengaged": [],
        }
        dashboard_cache.set(cache_key, result, ttl=600)
        return result

    actor_user_ids = sorted({outcome.actor_user_id for outcome in outcomes if outcome.actor_user_id})
    user_map = {
        user.id: user.full_name
        for user in db.scalars(select(User).where(User.id.in_(actor_user_ids))).all()
    } if actor_user_ids else {}

    actions_by_playbook: dict[str, int] = defaultdict(int)
    actions_by_channel: dict[str, int] = defaultdict(int)
    actions_by_operator: dict[str, int] = defaultdict(int)

    member_first_outcome: dict = {}
    for outcome in sorted(outcomes, key=lambda item: (item.occurred_at, str(item.id))):
        playbook_key = _normalize_group_key(outcome.playbook_key, "manual")
        channel_key = _normalize_group_key(outcome.channel, "manual")
        operator_key = str(outcome.actor_user_id) if outcome.actor_user_id else "system"

        actions_by_playbook[playbook_key] += 1
        actions_by_channel[channel_key] += 1
        actions_by_operator[operator_key] += 1

        if outcome.member_id and outcome.member_id not in member_first_outcome:
            member_first_outcome[outcome.member_id] = outcome

    member_ids = sorted(member_first_outcome.keys())
    member_map = {
        member.id: member
        for member in db.scalars(select(Member).where(Member.id.in_(member_ids))).all()
    } if member_ids else {}

    recovered_members: list[dict] = []
    recovered_by_playbook: dict[str, set[str]] = defaultdict(set)
    recovered_by_channel: dict[str, set[str]] = defaultdict(set)
    recovered_by_operator: dict[str, set[str]] = defaultdict(set)
    revenue_by_playbook: dict[str, float] = defaultdict(float)
    revenue_by_channel: dict[str, float] = defaultdict(float)
    revenue_by_operator: dict[str, float] = defaultdict(float)

    for member_id, first_outcome in member_first_outcome.items():
        member = member_map.get(member_id)
        if member is None:
            continue

        checkin_after = db.scalar(
            select(Checkin.id).where(
                Checkin.member_id == member_id,
                Checkin.checkin_at > first_outcome.occurred_at,
            ).limit(1)
        )
        if not checkin_after:
            continue

        monthly_fee = float(member.monthly_fee or 0)
        member_id_str = str(member_id)
        playbook_key = _normalize_group_key(first_outcome.playbook_key, "manual")
        channel_key = _normalize_group_key(first_outcome.channel, "manual")
        operator_key = str(first_outcome.actor_user_id) if first_outcome.actor_user_id else "system"

        recovered_members.append(
            {
                "member_id": member_id_str,
                "full_name": member.full_name,
                "monthly_fee": monthly_fee,
                "source": first_outcome.source,
                "channel": channel_key,
                "playbook_key": playbook_key,
            }
        )
        recovered_by_playbook[playbook_key].add(member_id_str)
        recovered_by_channel[channel_key].add(member_id_str)
        recovered_by_operator[operator_key].add(member_id_str)
        revenue_by_playbook[playbook_key] += monthly_fee
        revenue_by_channel[channel_key] += monthly_fee
        revenue_by_operator[operator_key] += monthly_fee

    reengaged_count = len(recovered_members)
    preserved_revenue = round(sum(item["monthly_fee"] for item in recovered_members), 2)
    distinct_members_targeted = len(member_first_outcome)
    recovery_rate = round((reengaged_count / max(1, distinct_members_targeted)) * 100, 1)

    top_playbooks = sorted(
        (
            {
                "playbook_key": key,
                "actions_executed": total_actions,
                "recovered_members": len(recovered_by_playbook.get(key, set())),
                "estimated_preserved_revenue": round(revenue_by_playbook.get(key, 0.0), 2),
            }
            for key, total_actions in actions_by_playbook.items()
        ),
        key=lambda item: (-item["estimated_preserved_revenue"], -item["actions_executed"], item["playbook_key"]),
    )[:5]

    top_channels = sorted(
        (
            {
                "channel": key,
                "actions_executed": total_actions,
                "recovered_members": len(recovered_by_channel.get(key, set())),
                "estimated_preserved_revenue": round(revenue_by_channel.get(key, 0.0), 2),
            }
            for key, total_actions in actions_by_channel.items()
        ),
        key=lambda item: (-item["estimated_preserved_revenue"], -item["actions_executed"], item["channel"]),
    )[:5]

    top_operators = sorted(
        (
            {
                "user_id": None if key == "system" else key,
                "label": user_map.get(key, "Sistema" if key == "system" else "Operador"),
                "actions_executed": total_actions,
                "recovered_members": len(recovered_by_operator.get(key, set())),
                "estimated_preserved_revenue": round(revenue_by_operator.get(key, 0.0), 2),
            }
            for key, total_actions in actions_by_operator.items()
        ),
        key=lambda item: (-item["estimated_preserved_revenue"], -item["actions_executed"], item["label"]),
    )[:5]

    result = {
        "period_days": period_days,
        "labeling": "estimativa_operacional",
        "actions_executed": actions_executed,
        "total_automated": total_automated,
        "reengaged_count": reengaged_count,
        "reengagement_rate": recovery_rate,
        "preserved_revenue": preserved_revenue,
        "recovery_rate": recovery_rate,
        "top_playbooks": top_playbooks,
        "top_channels": top_channels,
        "top_operators": top_operators,
        "top_reengaged": recovered_members[:10],
    }

    dashboard_cache.set(cache_key, result, ttl=600)
    return result
