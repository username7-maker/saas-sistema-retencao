from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import FinancialEntry, Member, MemberStatus, RiskLevel
from app.schemas import PaginatedResponse
from app.schemas.finance import (
    DREBasicOut,
    FinanceFoundationSummaryOut,
    FinancialEntryCreate,
    FinancialEntryOut,
    FinancialEntryUpdate,
)
from app.services.tenant_guard import ensure_optional_lead_in_gym, ensure_optional_member_in_gym


def list_financial_entries(
    db: Session,
    *,
    gym_id: UUID,
    page: int = 1,
    page_size: int = 50,
    entry_type: str | None = None,
    status_filter: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> PaginatedResponse[FinancialEntryOut]:
    filters = [FinancialEntry.gym_id == gym_id, FinancialEntry.deleted_at.is_(None)]
    if entry_type:
        filters.append(FinancialEntry.entry_type == entry_type)
    if status_filter:
        filters.append(FinancialEntry.status == status_filter)
    if from_date:
        filters.append(or_(FinancialEntry.due_date >= from_date, func.date(FinancialEntry.occurred_at) >= from_date))
    if to_date:
        filters.append(or_(FinancialEntry.due_date <= to_date, func.date(FinancialEntry.occurred_at) <= to_date))

    total = db.scalar(select(func.count()).select_from(FinancialEntry).where(and_(*filters))) or 0
    items = list(
        db.scalars(
            select(FinancialEntry)
            .where(and_(*filters))
            .order_by(FinancialEntry.due_date.asc().nullslast(), FinancialEntry.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return PaginatedResponse(
        items=[FinancialEntryOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_financial_entry(
    db: Session,
    payload: FinancialEntryCreate,
    *,
    gym_id: UUID,
    actor_user_id: UUID | None,
    commit: bool = True,
) -> FinancialEntry:
    ensure_optional_member_in_gym(db, payload.member_id, gym_id)
    ensure_optional_lead_in_gym(db, payload.lead_id, gym_id)
    entry = FinancialEntry(
        **payload.model_dump(),
        gym_id=gym_id,
        created_by_user_id=actor_user_id,
    )
    _normalize_entry_status(entry)
    db.add(entry)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(entry)
    _invalidate_finance_cache()
    return entry


def update_financial_entry(
    db: Session,
    entry_id: UUID,
    payload: FinancialEntryUpdate,
    *,
    gym_id: UUID,
    commit: bool = True,
) -> FinancialEntry:
    entry = _get_financial_entry(db, entry_id, gym_id=gym_id)
    data = payload.model_dump(exclude_unset=True)
    if "member_id" in data:
        ensure_optional_member_in_gym(db, data.get("member_id"), gym_id)
    if "lead_id" in data:
        ensure_optional_lead_in_gym(db, data.get("lead_id"), gym_id)
    for key, value in data.items():
        setattr(entry, key, value)
    _normalize_entry_status(entry)
    db.add(entry)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(entry)
    _invalidate_finance_cache()
    return entry


def delete_financial_entry(db: Session, entry_id: UUID, *, gym_id: UUID, commit: bool = True) -> None:
    entry = _get_financial_entry(db, entry_id, gym_id=gym_id)
    entry.deleted_at = datetime.now(tz=timezone.utc)
    db.add(entry)
    if commit:
        db.commit()
    else:
        db.flush()
    _invalidate_finance_cache()


def get_finance_foundation_summary(db: Session, *, gym_id: UUID) -> FinanceFoundationSummaryOut:
    today = datetime.now(tz=timezone.utc).date()
    month_start = today.replace(day=1)
    now_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    now_end = datetime.combine(today, time.max, tzinfo=timezone.utc)

    daily_cash_in = _sum_entries(
        db,
        gym_id=gym_id,
        entry_types=("cash_in", "receivable"),
        statuses=("paid",),
        occurred_from=now_start,
        occurred_to=now_end,
    )
    daily_cash_out = _sum_entries(
        db,
        gym_id=gym_id,
        entry_types=("cash_out", "payable"),
        statuses=("paid",),
        occurred_from=now_start,
        occurred_to=now_end,
    )
    open_receivables = _sum_entries(db, gym_id=gym_id, entry_types=("receivable",), statuses=("open", "overdue"))
    open_payables = _sum_entries(db, gym_id=gym_id, entry_types=("payable",), statuses=("open", "overdue"))
    overdue_receivables = _sum_entries(
        db,
        gym_id=gym_id,
        entry_types=("receivable",),
        statuses=("open", "overdue"),
        due_before=today,
    )
    overdue_payables = _sum_entries(
        db,
        gym_id=gym_id,
        entry_types=("payable",),
        statuses=("open", "overdue"),
        due_before=today,
    )
    month_revenue = _sum_entries(
        db,
        gym_id=gym_id,
        entry_types=("receivable", "cash_in"),
        statuses=("paid",),
        occurred_from=datetime.combine(month_start, time.min, tzinfo=timezone.utc),
        occurred_to=now_end,
    )
    month_expenses = _sum_entries(
        db,
        gym_id=gym_id,
        entry_types=("payable", "cash_out"),
        statuses=("paid",),
        occurred_from=datetime.combine(month_start, time.min, tzinfo=timezone.utc),
        occurred_to=now_end,
    )
    active_members = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.gym_id == gym_id,
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
        )
    ) or 0
    delinquent_members = _delinquent_members_count(db, gym_id=gym_id)
    delinquency_rate = (delinquent_members / max(1, active_members)) * 100
    revenue_at_risk = db.scalar(
        select(func.coalesce(func.sum(Member.monthly_fee), Decimal("0"))).where(
            Member.gym_id == gym_id,
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.risk_level == RiskLevel.RED,
        )
    ) or Decimal("0")
    net_result = month_revenue - month_expenses
    margin_pct = (net_result / month_revenue) * 100 if month_revenue > 0 else None
    data_quality_flags: list[str] = []
    if _financial_entry_count(db, gym_id=gym_id) == 0:
        data_quality_flags.append("missing_financial_entries")
    if active_members > 0 and open_receivables == 0 and overdue_receivables == 0:
        data_quality_flags.append("receivables_not_imported")
    if month_expenses == 0:
        data_quality_flags.append("expenses_not_imported")

    return FinanceFoundationSummaryOut(
        daily_cash_in=round(float(daily_cash_in), 2),
        daily_cash_out=round(float(daily_cash_out), 2),
        daily_net_cash=round(float(daily_cash_in - daily_cash_out), 2),
        open_receivables=round(float(open_receivables), 2),
        open_payables=round(float(open_payables), 2),
        overdue_receivables=round(float(overdue_receivables), 2),
        overdue_payables=round(float(overdue_payables), 2),
        delinquency_rate=round(delinquency_rate, 2),
        revenue_at_risk=round(float(revenue_at_risk), 2),
        dre_basic=DREBasicOut(
            revenue=round(float(month_revenue), 2),
            expenses=round(float(month_expenses), 2),
            net_result=round(float(net_result), 2),
            margin_pct=round(float(margin_pct), 2) if margin_pct is not None else None,
        ),
        data_quality_flags=data_quality_flags,
    )


def get_monthly_financial_entry_revenue(db: Session, *, gym_id: UUID, month_label: str) -> Decimal | None:
    month_start, month_end = _month_window(month_label)
    count = db.scalar(
        select(func.count()).select_from(FinancialEntry).where(
            FinancialEntry.gym_id == gym_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.status == "paid",
            FinancialEntry.entry_type.in_(["receivable", "cash_in"]),
            FinancialEntry.occurred_at >= month_start,
            FinancialEntry.occurred_at <= month_end,
        )
    ) or 0
    if count == 0:
        return None
    return db.scalar(
        select(func.coalesce(func.sum(FinancialEntry.amount), Decimal("0"))).where(
            FinancialEntry.gym_id == gym_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.status == "paid",
            FinancialEntry.entry_type.in_(["receivable", "cash_in"]),
            FinancialEntry.occurred_at >= month_start,
            FinancialEntry.occurred_at <= month_end,
        )
    ) or Decimal("0")


def _get_financial_entry(db: Session, entry_id: UUID, *, gym_id: UUID) -> FinancialEntry:
    entry = db.get(FinancialEntry, entry_id)
    if not entry or entry.deleted_at is not None or entry.gym_id != gym_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lancamento financeiro nao encontrado")
    return entry


def _normalize_entry_status(entry: FinancialEntry) -> None:
    if entry.status == "paid" and entry.paid_at is None:
        entry.paid_at = datetime.now(tz=timezone.utc)
    if entry.status == "paid" and entry.occurred_at is None:
        entry.occurred_at = entry.paid_at or datetime.now(tz=timezone.utc)
    if entry.status == "open" and entry.due_date and entry.due_date < datetime.now(tz=timezone.utc).date():
        entry.status = "overdue"


def _sum_entries(
    db: Session,
    *,
    gym_id: UUID,
    entry_types: tuple[str, ...],
    statuses: tuple[str, ...],
    due_before: date | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> Decimal:
    filters = [
        FinancialEntry.gym_id == gym_id,
        FinancialEntry.deleted_at.is_(None),
        FinancialEntry.entry_type.in_(entry_types),
        FinancialEntry.status.in_(statuses),
    ]
    if due_before:
        filters.append(FinancialEntry.due_date < due_before)
    if occurred_from:
        filters.append(FinancialEntry.occurred_at >= occurred_from)
    if occurred_to:
        filters.append(FinancialEntry.occurred_at <= occurred_to)
    return db.scalar(select(func.coalesce(func.sum(FinancialEntry.amount), Decimal("0"))).where(and_(*filters))) or Decimal("0")


def _delinquent_members_count(db: Session, *, gym_id: UUID) -> int:
    member_ids = {
        row[0]
        for row in db.execute(
            select(FinancialEntry.member_id)
            .where(
                FinancialEntry.gym_id == gym_id,
                FinancialEntry.deleted_at.is_(None),
                FinancialEntry.member_id.isnot(None),
                FinancialEntry.entry_type == "receivable",
                FinancialEntry.status.in_(["open", "overdue"]),
                FinancialEntry.due_date < datetime.now(tz=timezone.utc).date(),
            )
            .distinct()
        ).all()
    }
    extra_flag_count = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.gym_id == gym_id,
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.extra_data["delinquent"].astext == "true",
            ~Member.id.in_(member_ids) if member_ids else True,
        )
    ) or 0
    return len(member_ids) + int(extra_flag_count)


def _financial_entry_count(db: Session, *, gym_id: UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(FinancialEntry).where(
            FinancialEntry.gym_id == gym_id,
            FinancialEntry.deleted_at.is_(None),
        )
    ) or 0


def _month_window(month_label: str) -> tuple[datetime, datetime]:
    year, month = (int(value) for value in month_label.split("-"))
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


def _invalidate_finance_cache() -> None:
    invalidate_dashboard_cache("financial")
