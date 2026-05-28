from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable, Literal, TypedDict
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Checkin, Member

# Short window so new students quickly land in the correct operational queue.
PREFERRED_SHIFT_LOOKBACK_DAYS = 30
_SHIFT_KEYS = ("overnight", "morning", "afternoon", "evening")
_SHIFT_LABELS = {
    "overnight": "Madrugada",
    "morning": "Manha",
    "afternoon": "Tarde",
    "evening": "Noite",
}

_SHIFT_ALIASES = {
    "overnight": {"overnight", "madrugada", "noturno_madrugada", "plantao_madrugada"},
    "morning": {"morning", "manha", "matutino"},
    "afternoon": {"afternoon", "tarde", "vespertino"},
    "evening": {"evening", "night", "noite", "noturno"},
}


PreferredShiftDiagnosticStatus = Literal["resolved_from_checkins", "manual_or_cached", "tie", "no_recent_checkins"]


class PreferredShiftDiagnostic(TypedDict):
    status: PreferredShiftDiagnosticStatus
    reason: str
    counts: dict[str, int]
    lookback_days: int


def normalize_preferred_shift(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    for canonical, aliases in _SHIFT_ALIASES.items():
        if normalized in aliases:
            return canonical
    return None


def normalize_preferred_shift_scope(values: Iterable[str | None] | None, *, fallback: str | None = None) -> list[str]:
    normalized_scope: list[str] = []
    for value in values or []:
        normalized = normalize_preferred_shift(value)
        if normalized and normalized not in normalized_scope:
            normalized_scope.append(normalized)

    fallback_shift = normalize_preferred_shift(fallback)
    if fallback_shift and fallback_shift not in normalized_scope:
        normalized_scope.insert(0, fallback_shift)

    return normalized_scope


def preferred_shift_filter_condition(column, preferred_shift: str | None):
    normalized = normalize_preferred_shift(preferred_shift)
    if normalized is None:
        return None
    return func.lower(func.coalesce(column, "")).in_(tuple(_SHIFT_ALIASES[normalized]))


def checkin_shift_case():
    return case(
        (Checkin.hour_bucket < 6, "overnight"),
        (Checkin.hour_bucket < 12, "morning"),
        (Checkin.hour_bucket < 18, "afternoon"),
        else_="evening",
    )


def derive_preferred_shift_from_counts(counts: dict[str, int] | None) -> str | None:
    bucket_counts = {key: int((counts or {}).get(key) or 0) for key in _SHIFT_KEYS}
    total = sum(bucket_counts.values())
    if total <= 0:
        return None

    ranked = sorted(bucket_counts.items(), key=lambda item: item[1], reverse=True)
    winner, winner_count = ranked[0]
    runner_up_count = ranked[1][1]

    if winner_count <= 0 or winner_count == runner_up_count:
        return None
    return winner


def _has_recent_checkin_signal(counts: dict[str, int] | None) -> bool:
    return sum(int((counts or {}).get(key) or 0) for key in _SHIFT_KEYS) > 0


def _normalized_shift_counts(counts: dict[str, int] | None) -> dict[str, int]:
    return {key: int((counts or {}).get(key) or 0) for key in _SHIFT_KEYS}


def _format_shift_counts(counts: dict[str, int], *, only_top_ties: bool = False) -> str:
    positive_counts = [(key, total) for key, total in counts.items() if total > 0]
    if only_top_ties and positive_counts:
        top = max(total for _, total in positive_counts)
        positive_counts = [(key, total) for key, total in positive_counts if total == top]
    return ", ".join(f"{_SHIFT_LABELS.get(key, key)} {total}" for key, total in positive_counts)


def build_preferred_shift_diagnostic(
    counts: dict[str, int] | None,
    *,
    preferred_shift: str | None = None,
) -> PreferredShiftDiagnostic:
    bucket_counts = _normalized_shift_counts(counts)
    derived_shift = derive_preferred_shift_from_counts(bucket_counts)
    manual_shift = normalize_preferred_shift(preferred_shift)

    if derived_shift:
        return {
            "status": "resolved_from_checkins",
            "reason": (
                f"Turno inferido pelos check-ins dos ultimos {PREFERRED_SHIFT_LOOKBACK_DAYS} dias: "
                f"{_SHIFT_LABELS.get(derived_shift, derived_shift)}."
            ),
            "counts": bucket_counts,
            "lookback_days": PREFERRED_SHIFT_LOOKBACK_DAYS,
        }

    if _has_recent_checkin_signal(bucket_counts):
        count_summary = _format_shift_counts(bucket_counts, only_top_ties=True)
        suffix = f": {count_summary}" if count_summary else "."
        return {
            "status": "tie",
            "reason": f"Empate nos ultimos {PREFERRED_SHIFT_LOOKBACK_DAYS} dias{suffix}",
            "counts": bucket_counts,
            "lookback_days": PREFERRED_SHIFT_LOOKBACK_DAYS,
        }

    if manual_shift:
        return {
            "status": "manual_or_cached",
            "reason": f"Turno definido no cadastro: {_SHIFT_LABELS.get(manual_shift, manual_shift)}.",
            "counts": bucket_counts,
            "lookback_days": PREFERRED_SHIFT_LOOKBACK_DAYS,
        }

    return {
        "status": "no_recent_checkins",
        "reason": f"Sem check-in recente/importado nos ultimos {PREFERRED_SHIFT_LOOKBACK_DAYS} dias.",
        "counts": bucket_counts,
        "lookback_days": PREFERRED_SHIFT_LOOKBACK_DAYS,
    }


def _recent_checkin_counts_by_member(db: Session, member_ids: Iterable[UUID]) -> dict[UUID, dict[str, int]]:
    member_id_set = {member_id for member_id in member_ids if member_id is not None}
    if not member_id_set:
        return {}

    recent_cutoff = datetime.now(tz=timezone.utc) - timedelta(days=PREFERRED_SHIFT_LOOKBACK_DAYS)
    shift_expr = checkin_shift_case()
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
    return counts_by_member


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

    counts_by_member = _recent_checkin_counts_by_member(db, [member.id for member in members])
    updated = 0
    for member in members:
        member_counts = counts_by_member.get(member.id)
        derived_shift = derive_preferred_shift_from_counts(member_counts)
        fallback_shift = normalize_preferred_shift(member.preferred_shift)
        resolved_shift = derived_shift if _has_recent_checkin_signal(member_counts) else fallback_shift
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


def preferred_shift_diagnostics_from_checkins(db: Session, members: Iterable[Member]) -> dict[UUID, PreferredShiftDiagnostic]:
    """Hydrate response shifts and explain why a member is still without one."""
    member_list = [
        member
        for member in members
        if member is not None and normalize_preferred_shift(getattr(member, "preferred_shift", None)) is None
    ]
    if not member_list:
        return {}

    counts_by_member = _recent_checkin_counts_by_member(db, [member.id for member in member_list])
    diagnostics: dict[UUID, PreferredShiftDiagnostic] = {}
    for member in member_list:
        member_counts = counts_by_member.get(member.id)
        diagnostic = build_preferred_shift_diagnostic(member_counts, preferred_shift=getattr(member, "preferred_shift", None))
        diagnostics[member.id] = diagnostic
        derived_shift = derive_preferred_shift_from_counts(member_counts)
        if derived_shift:
            member.preferred_shift = derived_shift
    return diagnostics


def hydrate_missing_preferred_shifts_from_checkins(db: Session, members: Iterable[Member]) -> int:
    """Fill preferred_shift in response objects without requiring the daily sync job."""
    member_list = [
        member
        for member in members
        if member is not None and normalize_preferred_shift(getattr(member, "preferred_shift", None)) is None
    ]
    if not member_list:
        return 0

    preferred_shift_diagnostics_from_checkins(db, member_list)
    return sum(1 for member in member_list if normalize_preferred_shift(getattr(member, "preferred_shift", None)) is not None)
