import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.models import FinancialEntry
from app.schemas.finance import FinancialEntryCreate
from app.services import finance_service


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


class FakeExecuteResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, scalar_returns=None, execute_rows=None):
        self.added = []
        self.committed = False
        self.flushed = 0
        self.scalar_returns = list(scalar_returns or [])
        self.execute_rows = execute_rows or []

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushed += 1
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(tz=timezone.utc)
            if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
                obj.updated_at = datetime.now(tz=timezone.utc)

    def refresh(self, _obj):
        return None

    def commit(self):
        self.committed = True

    def scalar(self, _stmt):
        if not self.scalar_returns:
            return Decimal("0")
        return self.scalar_returns.pop(0)

    def execute(self, _stmt):
        return FakeExecuteResult(self.execute_rows)


def test_create_financial_entry_normalizes_paid_entry(monkeypatch):
    monkeypatch.setattr(finance_service, "ensure_optional_member_in_gym", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(finance_service, "ensure_optional_lead_in_gym", lambda *_args, **_kwargs: None)
    db = FakeSession()
    payload = FinancialEntryCreate(
        entry_type="receivable",
        status="paid",
        amount=Decimal("199.90"),
        category="mensalidade",
        member_id=MEMBER_ID,
        due_date=date.today(),
    )

    entry = finance_service.create_financial_entry(db, payload, gym_id=GYM_ID, actor_user_id=USER_ID, commit=False)

    assert isinstance(entry, FinancialEntry)
    assert entry.gym_id == GYM_ID
    assert entry.created_by_user_id == USER_ID
    assert entry.paid_at is not None
    assert entry.occurred_at is not None
    assert db.committed is False


def test_create_financial_entry_marks_past_open_receivable_as_overdue(monkeypatch):
    monkeypatch.setattr(finance_service, "ensure_optional_member_in_gym", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(finance_service, "ensure_optional_lead_in_gym", lambda *_args, **_kwargs: None)
    db = FakeSession()
    payload = FinancialEntryCreate(
        entry_type="receivable",
        status="open",
        amount=Decimal("149.90"),
        category="mensalidade",
        due_date=date.today() - timedelta(days=3),
    )

    entry = finance_service.create_financial_entry(db, payload, gym_id=GYM_ID, actor_user_id=None, commit=False)

    assert entry.status == "overdue"


def test_finance_summary_calculates_cash_dre_and_flags():
    db = FakeSession(
        scalar_returns=[
            Decimal("500.00"),  # daily cash in
            Decimal("120.00"),  # daily cash out
            Decimal("900.00"),  # open receivables
            Decimal("300.00"),  # open payables
            Decimal("250.00"),  # overdue receivables
            Decimal("50.00"),  # overdue payables
            Decimal("3000.00"),  # month revenue
            Decimal("1000.00"),  # month expenses
            10,  # active members
            1,  # legacy delinquent flag count
            Decimal("800.00"),  # revenue at risk
            5,  # financial entry count
        ],
        execute_rows=[(MEMBER_ID,)],
    )

    summary = finance_service.get_finance_foundation_summary(db, gym_id=GYM_ID)

    assert summary.daily_net_cash == 380.0
    assert summary.open_receivables == 900.0
    assert summary.overdue_receivables == 250.0
    assert summary.delinquency_rate == 20.0
    assert summary.dre_basic.net_result == 2000.0
    assert summary.dre_basic.margin_pct == 66.67
    assert summary.revenue_at_risk == 800.0
