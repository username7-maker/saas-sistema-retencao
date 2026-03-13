from pydantic import BaseModel

from app.schemas.lead import LeadOut
from app.schemas.member import MemberOut
from app.schemas.nps import NPSEvolutionPoint


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


class OperationalDashboard(BaseModel):
    realtime_checkins: int
    heatmap: list[HeatmapPoint]
    inactive_7d_total: int
    inactive_7d_items: list[MemberOut]


class CommercialDashboard(BaseModel):
    pipeline: dict[str, int]
    conversion_by_source: list[ConversionBySource]
    cac: float
    stale_leads_total: int
    stale_leads: list[LeadOut]


class FinancialDashboard(BaseModel):
    monthly_revenue: list[RevenuePoint]
    delinquency_rate: float
    projections: list[ProjectionPoint]


class WeeklySummary(BaseModel):
    checkins_this_week: int
    checkins_last_week: int
    checkins_delta_pct: float
    new_registrations: int
    new_at_risk: int
    mrr_at_risk: float
    total_active: int


class RetentionBucket(BaseModel):
    total: int
    items: list[MemberOut]


class RetentionDashboard(BaseModel):
    red: RetentionBucket
    yellow: RetentionBucket
    nps_trend: list[NPSEvolutionPoint]
    mrr_at_risk: float = 0.0
    avg_red_score: float = 0.0
    avg_yellow_score: float = 0.0
    last_contact_map: dict[str, str] = {}  # member_id → ISO datetime do último contato
