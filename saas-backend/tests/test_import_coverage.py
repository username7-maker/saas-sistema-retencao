from datetime import date
import pytest
from fastapi import HTTPException
from app.services.import_coverage_service import pending_dates, require_coverage_acknowledgement
from app.services.import_coverage_service import coverage_preview
from unittest.mock import MagicMock
from uuid import uuid4


def test_missing_previous_day_survives_later_import_and_is_repaired():
    assert pending_dates(date(2026, 10, 11), {date(2026, 10, 11)}, {date(2026, 10, 13)}) == ["2026-10-12"]
    assert pending_dates(date(2026, 10, 11), {date(2026, 10, 11), date(2026, 10, 13)}, {date(2026, 10, 14)}) == ["2026-10-12"]
    assert pending_dates(date(2026, 10, 11), {date(2026, 10, 11), date(2026, 10, 13)}, {date(2026, 10, 12)}) == []


def test_overlap_internal_gap_first_file_and_old_file():
    assert pending_dates(None, set(), {date(2026, 10, 11), date(2026, 10, 13)}) == ["2026-10-12"]
    assert pending_dates(None, set(), {date(2026, 10, 13)}) == []
    assert pending_dates(date(2026, 10, 11), {date(2026, 10, 11)}, {date(2026, 10, 10)}) == []


def test_acknowledgement_must_match_current_gaps():
    require_coverage_acknowledgement([], None)
    require_coverage_acknowledgement(["2026-10-12"], '["2026-10-12"]')
    for value in (None, 'true', '["2026-10-11"]'):
        with pytest.raises(HTTPException) as exc:
            require_coverage_acknowledgement(["2026-10-12"], value)
        assert exc.value.status_code == 409


def test_coverage_is_tenant_scoped_and_partial_import_is_not_complete(monkeypatch):
    gym_id = uuid4()
    monkeypatch.setattr("app.services.import_coverage_service.get_current_gym_id", lambda: gym_id)
    db = MagicMock()
    db.execute.return_value.all.return_value = [({"daily_coverage": {
        "start": "2026-10-11", "baseline": "2026-10-11",
        "observed_dates": ["2026-10-12"], "completed_dates": [],
    }},)]
    start, missing, baseline = coverage_preview(db, {date(2026, 10, 13)}, None)
    assert (start, missing, baseline) == ("2026-10-11", ["2026-10-12"], "2026-10-11")
    statement = db.execute.call_args.args[0]
    assert gym_id in statement.compile().params.values()
