from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OnboardingCockpitSummaryOut(BaseModel):
    active_total: int = 0
    at_risk_total: int = 0
    critical_total: int = 0
    due_today_total: int = 0
    overdue_total: int = 0
    unassigned_total: int = 0


class OnboardingCockpitMemberOut(BaseModel):
    member_id: UUID
    full_name: str
    plan_name: str | None = None
    preferred_shift: str | None = None
    days_since_join: int
    score: int
    status: str
    phase_label: str
    next_action: str
    responsible_role: str
    current_stage_offset: int | None = None


class OnboardingCockpitTaskStageOut(BaseModel):
    stage_key: str
    label: str
    day_offset: int | None = None
    total: int = 0
    due_now_total: int = 0
    future_total: int = 0


class OnboardingCockpitMetricsOut(BaseModel):
    first_week_two_checkins_rate: float | None = None
    first_assessment_rate: float | None = None
    d30_ready_total: int = 0
    generated_at: datetime


class OnboardingCockpitOut(BaseModel):
    summary: OnboardingCockpitSummaryOut
    members: list[OnboardingCockpitMemberOut] = Field(default_factory=list)
    critical_members: list[OnboardingCockpitMemberOut] = Field(default_factory=list)
    tasks_by_stage: list[OnboardingCockpitTaskStageOut] = Field(default_factory=list)
    score_distribution: dict[str, int] = Field(default_factory=dict)
    metrics: OnboardingCockpitMetricsOut
    generated_at: datetime
