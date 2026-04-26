from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


FinancialEntryType = Literal["receivable", "payable", "cash_in", "cash_out"]
FinancialEntryStatus = Literal["open", "paid", "overdue", "cancelled"]


class FinancialEntryCreate(BaseModel):
    entry_type: FinancialEntryType
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    category: str = Field(default="geral", min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    status: FinancialEntryStatus = "open"
    due_date: date | None = None
    occurred_at: datetime | None = None
    paid_at: datetime | None = None
    member_id: UUID | None = None
    lead_id: UUID | None = None
    source: str = Field(default="manual", min_length=2, max_length=40)
    external_ref: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)
    extra_data: dict = Field(default_factory=dict)


class FinancialEntryUpdate(BaseModel):
    entry_type: FinancialEntryType | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    status: FinancialEntryStatus | None = None
    due_date: date | None = None
    occurred_at: datetime | None = None
    paid_at: datetime | None = None
    member_id: UUID | None = None
    lead_id: UUID | None = None
    source: str | None = Field(default=None, min_length=2, max_length=40)
    external_ref: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)
    extra_data: dict | None = None


class FinancialEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gym_id: UUID
    member_id: UUID | None
    lead_id: UUID | None
    created_by_user_id: UUID | None
    entry_type: str
    status: str
    category: str
    description: str | None
    amount: Decimal
    due_date: date | None
    occurred_at: datetime | None
    paid_at: datetime | None
    source: str
    external_ref: str | None
    notes: str | None
    extra_data: dict
    created_at: datetime
    updated_at: datetime


class DREBasicOut(BaseModel):
    revenue: float
    expenses: float
    net_result: float
    margin_pct: float | None = None


class FinanceFoundationSummaryOut(BaseModel):
    daily_cash_in: float
    daily_cash_out: float
    daily_net_cash: float
    open_receivables: float
    open_payables: float
    overdue_receivables: float
    overdue_payables: float
    delinquency_rate: float
    revenue_at_risk: float
    dre_basic: DREBasicOut
    data_quality_flags: list[str] = Field(default_factory=list)
