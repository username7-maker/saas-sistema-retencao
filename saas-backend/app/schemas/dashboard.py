from datetime import datetime

from pydantic import BaseModel

from app.models import RiskLevel
from app.schemas.assistant import AIAssistantPayload

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
    pitch_pipeline: dict[str, int] = {}
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
    churn_distribution: dict[str, int] = {}
    last_contact_map: dict[str, str] = {}  # member_id → ISO datetime do último contato


class RetentionPlaybookStep(BaseModel):
    action: str
    priority: str
    title: str
    message: str
    due_days: int
    owner: str


class RetentionQueueItem(BaseModel):
    alert_id: str
    member_id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    plan_name: str
    risk_level: RiskLevel
    risk_score: int
    nps_last_score: int = 0
    days_without_checkin: int | None = None
    last_checkin_at: datetime | None = None
    last_contact_at: datetime | None = None
    churn_type: str | None = None
    automation_stage: str | None = None
    created_at: datetime
    forecast_60d: int | None = None
    signals_summary: str
    next_action: str | None = None
    reasons: dict = {}
    action_history: list[dict] = []
    playbook_steps: list[RetentionPlaybookStep] = []
    assistant: AIAssistantPayload | None = None


class ActionCenterItem(BaseModel):
    id: str
    source: str
    source_label: str
    severity: str
    severity_rank: int
    title: str
    subtitle: str
    member_id: str | None = None
    lead_id: str | None = None
    task_id: str | None = None
    risk_alert_id: str | None = None
    status: str | None = None
    channel: str | None = None
    owner_label: str | None = None
    value_amount: float = 0.0
    stale_days: int = 0
    due_at: datetime | None = None
    last_contact_at: datetime | None = None
    last_checkin_at: datetime | None = None
    cta_label: str
    cta_target: str
    metadata: dict = {}


class ActionCenterSummary(BaseModel):
    total: int
    by_source: dict[str, int] = {}
    by_severity: dict[str, int] = {}


class ActionCenterResponse(BaseModel):
    items: list[ActionCenterItem]
    total: int
    page: int
    page_size: int
    summary: ActionCenterSummary
