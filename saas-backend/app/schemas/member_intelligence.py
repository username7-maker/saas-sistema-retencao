from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


SignalSeverity = Literal["neutral", "info", "success", "warning", "danger"]


class MemberIntelligenceSignalOut(BaseModel):
    key: str
    label: str
    value: str | int | float | bool | None = None
    severity: SignalSeverity = "neutral"
    source: str
    observed_at: datetime | None = None


class MemberIntelligenceSnapshotOut(BaseModel):
    member_id: UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    status: str
    plan_name: str | None = None
    monthly_fee: float | None = None
    join_date: date | None = None
    preferred_shift: str | None = None
    assigned_user_id: UUID | None = None
    is_vip: bool = False


class LeadIntelligenceContextOut(BaseModel):
    lead_id: UUID | None = None
    source: str | None = None
    stage: str | None = None
    owner_id: UUID | None = None
    last_contact_at: datetime | None = None
    estimated_value: float | None = None
    acquisition_cost: float | None = None
    converted: bool = False
    notes_count: int = 0


class ConsentIntelligenceContextOut(BaseModel):
    lgpd: bool | None = None
    communication: bool | None = None
    image: bool | None = None
    contract: bool | None = None
    source: str = "member.extra_data"
    missing: list[str] = Field(default_factory=list)


class LifecycleIntelligenceContextOut(BaseModel):
    onboarding_status: str | None = None
    onboarding_score: int | None = None
    retention_stage: str | None = None
    churn_type: str | None = None
    loyalty_months: int | None = None


class ActivityIntelligenceContextOut(BaseModel):
    last_checkin_at: datetime | None = None
    days_without_checkin: int | None = None
    checkins_30d: int = 0
    checkins_90d: int = 0
    preferred_shift: str | None = None


class AssessmentIntelligenceContextOut(BaseModel):
    assessments_total: int = 0
    latest_assessment_at: datetime | None = None
    body_composition_total: int = 0
    latest_body_composition_at: datetime | None = None
    latest_body_fat_percent: float | None = None
    latest_muscle_mass_kg: float | None = None
    latest_weight_kg: float | None = None


class OperationsIntelligenceContextOut(BaseModel):
    open_tasks_total: int = 0
    overdue_tasks_total: int = 0
    next_task_due_at: datetime | None = None
    latest_completed_task_at: datetime | None = None


class RiskIntelligenceContextOut(BaseModel):
    risk_level: str | None = None
    risk_score: int | None = None
    open_alerts_total: int = 0
    nps_last_score: int | None = None


class LeadToMemberIntelligenceContextOut(BaseModel):
    version: str = "lead-member-context-v1"
    generated_at: datetime
    member: MemberIntelligenceSnapshotOut
    lead: LeadIntelligenceContextOut | None = None
    consent: ConsentIntelligenceContextOut
    lifecycle: LifecycleIntelligenceContextOut
    activity: ActivityIntelligenceContextOut
    assessment: AssessmentIntelligenceContextOut
    operations: OperationsIntelligenceContextOut
    risk: RiskIntelligenceContextOut
    signals: list[MemberIntelligenceSignalOut] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)
