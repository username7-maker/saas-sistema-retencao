from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from app.database import clear_current_gym_id, set_current_gym_id
from app.services import analytics_view_service


class _DummyResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _DummyDb:
    def __init__(self, *, rows=None, fail_execute=False):
        self.rows = rows or []
        self.fail_execute = fail_execute
        self.committed = False
        self.rolled_back = False

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    def execute(self, *_args, **_kwargs):
        if self.fail_execute:
            raise SQLAlchemyError("boom")
        return _DummyResult(self.rows)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_get_monthly_member_kpis_returns_empty_without_tenant():
    clear_current_gym_id()
    db = _DummyDb()
    payload = analytics_view_service.get_monthly_member_kpis(db, months=6)
    assert payload == {}


def test_get_monthly_member_kpis_returns_mapped_values():
    gym_id = uuid4()
    set_current_gym_id(gym_id)
    try:
        db = _DummyDb(
            rows=[
                {
                    "month_label": "2026-01",
                    "total_mrr": Decimal("12345.67"),
                    "cancelled_members": 5,
                    "active_members": 250,
                }
            ]
        )
        payload = analytics_view_service.get_monthly_member_kpis(db, months=1)
        assert payload["2026-01"]["mrr"] == 12345.67
        assert payload["2026-01"]["cancelled"] == 5
        assert payload["2026-01"]["active"] == 250
    finally:
        clear_current_gym_id()


def test_refresh_member_kpis_materialized_view_rolls_back_on_failure():
    db = _DummyDb(fail_execute=True)
    refreshed = analytics_view_service.refresh_member_kpis_materialized_view(db)
    assert refreshed is False
    assert db.rolled_back is True
