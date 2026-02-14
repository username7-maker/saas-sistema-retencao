from pydantic import BaseModel


class ExecutiveDashboard(BaseModel):
    total_members: int
    active_members: int
    mrr: float
    churn_rate: float
    nps_avg: float
    risk_distribution: dict[str, int]


class RevenuePoint(BaseModel):
    month: str
    value: float


class ChurnPoint(BaseModel):
    month: str
    churn_rate: float


class LTVPoint(BaseModel):
    month: str
    ltv: float


class GrowthPoint(BaseModel):
    month: str
    growth_mom: float


class HeatmapPoint(BaseModel):
    weekday: int
    hour_bucket: int
    total_checkins: int


class ConversionBySource(BaseModel):
    source: str
    total: int
    won: int
    conversion_rate: float


class ProjectionPoint(BaseModel):
    horizon_months: int
    projected_revenue: float
