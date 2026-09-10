from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.retention_freshness_service import get_retention_freshness


def test_no_tenant_never_reads_cross_gym_data():
    db = MagicMock()
    assert get_retention_freshness(db, None) is None
    db.scalar.assert_not_called()


def test_import_and_checkin_dates_are_distinct_and_coverage_is_not_assumed():
    gym_id = uuid4()
    db = MagicMock()
    access = datetime(2026, 9, 4, tzinfo=timezone.utc)
    imported = datetime(2026, 9, 9, tzinfo=timezone.utc)
    db.scalar.side_effect = [access, SimpleNamespace(created_at=imported, details={
        "coverage_warning_codes": ["possible_access_gap", "untrusted_text"],
    })]
    result = get_retention_freshness(db, gym_id)
    assert result.latest_checkin_at == access
    assert result.last_import_at == imported
    assert result.coverage_verified is False
    assert result.warning_codes == ["possible_access_gap"]
    for call in db.scalar.call_args_list:
        assert gym_id in call.args[0].compile().params.values()


def test_missing_import_history_is_explicit():
    db = MagicMock()
    db.scalar.side_effect = [None, None]
    result = get_retention_freshness(db, uuid4())
    assert result.last_import_at is None
    assert result.latest_checkin_at is None
    assert result.coverage_verified is False
