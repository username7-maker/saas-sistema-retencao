from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


ALLOWED_METRICS = {"mrr", "new_members", "churn_rate", "nps_avg", "active_members"}
ALLOWED_COMPARATORS = {"gte", "lte"}


class GoalCreate(BaseModel):
    name: str = Field(min_length=3, max_length=140)
    metric_type: str = Field(min_length=3, max_length=40)
    comparator: str = Field(default="gte", min_length=3, max_length=3)
    target_value: float = Field(ge=0)
    period_start: date
    period_end: date
    alert_threshold_pct: int = Field(default=80, ge=1, le=100)
    is_active: bool = True
    notes: str | None = None

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_METRICS:
            raise ValueError(f"metric_type invalido. Use: {', '.join(sorted(ALLOWED_METRICS))}")
        return normalized

    @field_validator("comparator")
    @classmethod
    def validate_comparator(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_COMPARATORS:
            raise ValueError("comparator invalido. Use 'gte' ou 'lte'")
        return normalized


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=140)
    metric_type: str | None = Field(default=None, min_length=3, max_length=40)
    comparator: str | None = Field(default=None, min_length=3, max_length=3)
    target_value: float | None = Field(default=None, ge=0)
    period_start: date | None = None
    period_end: date | None = None
    alert_threshold_pct: int | None = Field(default=None, ge=1, le=100)
    is_active: bool | None = None
    notes: str | None = None

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ALLOWED_METRICS:
            raise ValueError(f"metric_type invalido. Use: {', '.join(sorted(ALLOWED_METRICS))}")
        return normalized

    @field_validator("comparator")
    @classmethod
    def validate_comparator(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ALLOWED_COMPARATORS:
            raise ValueError("comparator invalido. Use 'gte' ou 'lte'")
        return normalized


class GoalOut(BaseModel):
    id: UUID
    gym_id: UUID
    name: str
    metric_type: str
    comparator: str
    target_value: float
    period_start: date
    period_end: date
    alert_threshold_pct: int
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalProgressOut(BaseModel):
    goal: GoalOut
    current_value: float
    progress_pct: float
    status: str
    status_message: str
