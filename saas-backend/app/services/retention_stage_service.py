from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any


RETENTION_STAGE_MONITORING = "monitoring"
RETENTION_STAGE_ATTENTION = "attention"
RETENTION_STAGE_RECOVERY = "recovery"
RETENTION_STAGE_REACTIVATION = "reactivation"
RETENTION_STAGE_MANAGER_ESCALATION = "manager_escalation"
RETENTION_STAGE_COLD_BASE = "cold_base"

RETENTION_STAGE_ORDER = (
    RETENTION_STAGE_MONITORING,
    RETENTION_STAGE_ATTENTION,
    RETENTION_STAGE_RECOVERY,
    RETENTION_STAGE_REACTIVATION,
    RETENTION_STAGE_MANAGER_ESCALATION,
    RETENTION_STAGE_COLD_BASE,
)

LEGACY_RETENTION_STAGES = {"intervening", "recovering"}


@dataclass(frozen=True)
class RetentionStageMeta:
    key: str
    label: str
    priority: int
    owner_role: str
    lane: str


RETENTION_STAGE_META: dict[str, RetentionStageMeta] = {
    RETENTION_STAGE_MONITORING: RetentionStageMeta(
        key=RETENTION_STAGE_MONITORING,
        label="Monitoramento",
        priority=10,
        owner_role="system",
        lane=RETENTION_STAGE_MONITORING,
    ),
    RETENTION_STAGE_ATTENTION: RetentionStageMeta(
        key=RETENTION_STAGE_ATTENTION,
        label="Atencao agora",
        priority=80,
        owner_role="receptionist",
        lane=RETENTION_STAGE_ATTENTION,
    ),
    RETENTION_STAGE_RECOVERY: RetentionStageMeta(
        key=RETENTION_STAGE_RECOVERY,
        label="Recuperar esta semana",
        priority=95,
        owner_role="receptionist",
        lane=RETENTION_STAGE_RECOVERY,
    ),
    RETENTION_STAGE_REACTIVATION: RetentionStageMeta(
        key=RETENTION_STAGE_REACTIVATION,
        label="Reativar 30+ dias",
        priority=70,
        owner_role="trainer",
        lane=RETENTION_STAGE_REACTIVATION,
    ),
    RETENTION_STAGE_MANAGER_ESCALATION: RetentionStageMeta(
        key=RETENTION_STAGE_MANAGER_ESCALATION,
        label="Escalar gerente",
        priority=90,
        owner_role="manager",
        lane=RETENTION_STAGE_MANAGER_ESCALATION,
    ),
    RETENTION_STAGE_COLD_BASE: RetentionStageMeta(
        key=RETENTION_STAGE_COLD_BASE,
        label="Base fria",
        priority=5,
        owner_role="manager",
        lane=RETENTION_STAGE_COLD_BASE,
    ),
}


def normalize_retention_stage(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if not normalized or normalized in LEGACY_RETENTION_STAGES:
        return None
    if normalized in RETENTION_STAGE_META:
        return normalized
    return None


def calculate_retention_stage(days_without_checkin: int | None) -> str:
    if days_without_checkin is None:
        return RETENTION_STAGE_MONITORING
    days = max(0, int(days_without_checkin))
    if days >= 60:
        return RETENTION_STAGE_COLD_BASE
    if days >= 45:
        return RETENTION_STAGE_MANAGER_ESCALATION
    if days >= 30:
        return RETENTION_STAGE_REACTIVATION
    if days >= 14:
        return RETENTION_STAGE_RECOVERY
    if days >= 7:
        return RETENTION_STAGE_ATTENTION
    return RETENTION_STAGE_MONITORING


def retention_stage_meta(stage: str | None) -> RetentionStageMeta:
    normalized = normalize_retention_stage(stage) or RETENTION_STAGE_MONITORING
    return RETENTION_STAGE_META[normalized]


def retention_stage_payload(stage: str | None) -> dict[str, Any]:
    meta = retention_stage_meta(stage)
    return {
        "retention_stage": meta.key,
        "retention_stage_label": meta.label,
        "retention_stage_priority": meta.priority,
        "recommended_owner_role": meta.owner_role,
        "operational_lane": meta.lane,
    }


def days_without_checkin_from_dates(
    *,
    last_checkin_at: datetime | None,
    join_date: date | None,
    now: datetime | None = None,
) -> int | None:
    current = now or datetime.now(tz=timezone.utc)
    reference = last_checkin_at
    if reference is None and join_date is not None:
        reference = datetime.combine(join_date, time.min, tzinfo=timezone.utc)
    if reference is None:
        return None
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return max(0, (current - reference).days)


def calculate_member_retention_stage(member: Any, *, now: datetime | None = None) -> tuple[str, int | None]:
    days = days_without_checkin_from_dates(
        last_checkin_at=getattr(member, "last_checkin_at", None),
        join_date=getattr(member, "join_date", None),
        now=now,
    )
    return calculate_retention_stage(days), days


def is_cold_base_stage(stage: str | None) -> bool:
    return normalize_retention_stage(stage) == RETENTION_STAGE_COLD_BASE
