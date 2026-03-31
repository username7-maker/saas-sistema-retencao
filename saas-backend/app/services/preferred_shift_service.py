from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Checkin, Member

PREFERRED_SHIFT_LOOKBACK_DAYS = 120
_SHIFT_KEYS = ("morning", "afternoon", "evening")


def normalize_preferred_shift(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if normalized in {"morning", "manha", "matutino"}:
        return "morning"
    if normalized in {"afternoon", "tarde", "vespertino"}:
        return "afternoon"
    if normalized in {"evening", "night", "noite", "noturno"}:
        return "evening"
    return None


def derive_preferred_shift_from_counts(counts: dict[str, int] | None) -> str | None:
    bucket_counts = {key: int((counts or {}).get(key) or 0) for key in _SHIFT_KEYS}
    total = sum(bucket_counts.values())
    if total < 2:
        return None

    ranked = sorted(bucket_counts.items(), key=lambda item: item[1], reverse=True)
    winner, winner_count = ranked[0]
    runner_up_count = ranked[1][1]

    if winner_count <= 0 or winner_count == runner_up_count:
        return None
    if total == 2:
        return winner if winner_count == 2 else None
    if total == 3:
        return winner if winner_count >= 2 else None
    if (winner_count / total) < 0.5:
        return None
    return winner


def sync_preferred_shifts_from_checkins(
    db: Session,
    *,
    gym_id: UUID | None = None,
    member_ids: Iterable[UUID] | None = None,
    commit: bool = True,
    flush: bool = True,
) -> int:
    target_member_ids = {member_id for member_id in (member_ids or []) if member_id is not None}
    filters = [Member.deleted_at.is_(None)]
    if gym_id is not None:
        filters.append(Member.gym_id == gym_id)
    if target_member_ids:
        filters.append(Member.id.in_(target_member_ids))

    members = list(db.scalars(select(Member).where(and_(*filters))).all())
    if not members:
        return 0

    member_id_set = {member.id for member in members}
    recent_cutoff = datetime.now(tz=timezone.utc) - timedelta(days=PREFERRED_SHIFT_LOOKBACK_DAYS)
    shift_expr = case(
        (Checkin.hour_bucket < 12, "morning"),
        (Checkin.hour_bucket < 18, "afternoon"),
        else_="evening",
    )
    rows = db.execute(
        select(
            Checkin.member_id.label("member_id"),
            shift_expr.label("shift_key"),
            func.count(Checkin.id).label("total"),
        )
        .where(
            Checkin.member_id.in_(member_id_set),
            Checkin.checkin_at >= recent_cutoff,
        )
        .group_by(Checkin.member_id, shift_expr)
    ).all()

    counts_by_member: dict[UUID, dict[str, int]] = defaultdict(dict)
    for row in rows:
        counts_by_member[row.member_id][row.shift_key] = int(row.total or 0)

    updated = 0
    for member in members:
        derived_shift = derive_preferred_shift_from_counts(counts_by_member.get(member.id))
        fallback_shift = normalize_preferred_shift(member.preferred_shift)
        resolved_shift = derived_shift or fallback_shift
        if member.preferred_shift != resolved_shift:
            member.preferred_shift = resolved_shift
            db.add(member)
            updated += 1

    if updated:
        invalidate_dashboard_cache("members")
        if commit:
            db.commit()
        elif flush:
            db.flush()
    return updated
