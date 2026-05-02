from datetime import datetime, timezone

from app.services.retention_stage_service import (
    RETENTION_STAGE_ATTENTION,
    RETENTION_STAGE_COLD_BASE,
    RETENTION_STAGE_MANAGER_ESCALATION,
    RETENTION_STAGE_MONITORING,
    RETENTION_STAGE_REACTIVATION,
    RETENTION_STAGE_RECOVERY,
    calculate_retention_stage,
    days_without_checkin_from_dates,
    normalize_retention_stage,
    retention_stage_payload,
)


def test_calculates_retention_stage_by_inactivity_windows():
    assert calculate_retention_stage(5) == RETENTION_STAGE_MONITORING
    assert calculate_retention_stage(10) == RETENTION_STAGE_ATTENTION
    assert calculate_retention_stage(20) == RETENTION_STAGE_RECOVERY
    assert calculate_retention_stage(35) == RETENTION_STAGE_REACTIVATION
    assert calculate_retention_stage(50) == RETENTION_STAGE_MANAGER_ESCALATION
    assert calculate_retention_stage(65) == RETENTION_STAGE_COLD_BASE


def test_normalizes_legacy_retention_stage_values():
    assert normalize_retention_stage("intervening") is None
    assert normalize_retention_stage("recovering") is None
    assert normalize_retention_stage("manager_escalation") == RETENTION_STAGE_MANAGER_ESCALATION
    assert normalize_retention_stage("unknown") is None


def test_days_without_checkin_uses_last_checkin_before_join_date():
    now = datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc)
    last_checkin = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)
    joined = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    assert days_without_checkin_from_dates(last_checkin_at=last_checkin, join_date=joined, now=now) == 10
    assert days_without_checkin_from_dates(last_checkin_at=None, join_date=joined, now=now) == 121


def test_retention_stage_payload_contains_operational_lane_and_owner():
    payload = retention_stage_payload(RETENTION_STAGE_REACTIVATION)

    assert payload["retention_stage"] == RETENTION_STAGE_REACTIVATION
    assert payload["retention_stage_label"] == "Reativar 30+ dias"
    assert payload["recommended_owner_role"] == "trainer"
    assert payload["operational_lane"] == "reactivation"
    assert payload["retention_stage_priority"] > 0
