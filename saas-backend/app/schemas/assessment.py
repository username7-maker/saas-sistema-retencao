from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import RiskLevel
from app.schemas.assistant import AIAssistantPayload


class AssessmentCreate(BaseModel):
    assessment_date: datetime | None = None
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    body_fat_pct: float | None = Field(default=None, ge=0, le=100)
    lean_mass_kg: float | None = Field(default=None, ge=0)
    waist_cm: float | None = Field(default=None, gt=0)
    hip_cm: float | None = Field(default=None, gt=0)
    chest_cm: float | None = Field(default=None, gt=0)
    arm_cm: float | None = Field(default=None, gt=0)
    thigh_cm: float | None = Field(default=None, gt=0)
    resting_hr: int | None = Field(default=None, ge=20, le=250)
    blood_pressure_systolic: int | None = Field(default=None, ge=50, le=300)
    blood_pressure_diastolic: int | None = Field(default=None, ge=30, le=220)
    vo2_estimated: float | None = Field(default=None, ge=0)
    strength_score: int | None = Field(default=None, ge=0, le=100)
    flexibility_score: int | None = Field(default=None, ge=0, le=100)
    cardio_score: int | None = Field(default=None, ge=0, le=100)
    observations: str | None = None
    extra_data: dict = Field(default_factory=dict)


class MemberConstraintsUpsert(BaseModel):
    medical_conditions: str | None = None
    injuries: str | None = None
    medications: str | None = None
    contraindications: str | None = None
    preferred_training_times: str | None = None
    restrictions: dict = Field(default_factory=dict)
    notes: str | None = None


class MemberGoalCreate(BaseModel):
    assessment_id: UUID | None = None
    title: str = Field(min_length=2, max_length=140)
    description: str | None = None
    category: str = Field(default="general", min_length=2, max_length=60)
    target_value: float | None = Field(default=None, ge=0)
    current_value: float = Field(default=0, ge=0)
    unit: str | None = Field(default=None, max_length=32)
    target_date: date | None = None
    status: str = Field(default="active", max_length=20)
    progress_pct: int = Field(default=0, ge=0, le=100)
    achieved: bool = False
    notes: str | None = None
    extra_data: dict = Field(default_factory=dict)


class TrainingPlanCreate(BaseModel):
    assessment_id: UUID | None = None
    name: str = Field(min_length=3, max_length=160)
    objective: str | None = None
    sessions_per_week: int = Field(default=3, ge=1, le=14)
    split_type: str | None = Field(default=None, max_length=60)
    start_date: date = Field(default_factory=date.today)
    end_date: date | None = None
    is_active: bool = True
    plan_data: dict = Field(default_factory=dict)
    notes: str | None = None
    extra_data: dict = Field(default_factory=dict)


class AssessmentOut(BaseModel):
    id: UUID
    gym_id: UUID
    member_id: UUID
    evaluator_id: UUID | None
    assessment_number: int
    assessment_date: datetime
    next_assessment_due: date | None
    height_cm: float | None
    weight_kg: float | None
    bmi: float | None
    body_fat_pct: float | None
    lean_mass_kg: float | None
    waist_cm: float | None
    hip_cm: float | None
    chest_cm: float | None
    arm_cm: float | None
    thigh_cm: float | None
    resting_hr: int | None
    blood_pressure_systolic: int | None
    blood_pressure_diastolic: int | None
    vo2_estimated: float | None
    strength_score: int | None
    flexibility_score: int | None
    cardio_score: int | None
    observations: str | None
    ai_analysis: str | None
    ai_recommendations: str | None
    ai_risk_flags: str | None
    extra_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentMiniOut(BaseModel):
    id: UUID
    assessment_number: int
    assessment_date: datetime
    next_assessment_due: date | None
    weight_kg: float | None
    bmi: float | None
    body_fat_pct: float | None
    strength_score: int | None
    flexibility_score: int | None
    cardio_score: int | None
    ai_analysis: str | None

    model_config = ConfigDict(from_attributes=True)


class MemberGoalOut(BaseModel):
    id: UUID
    gym_id: UUID
    member_id: UUID
    assessment_id: UUID | None
    title: str
    description: str | None
    category: str
    target_value: float | None
    current_value: float
    unit: str | None
    target_date: date | None
    status: str
    progress_pct: int
    achieved: bool
    achieved_at: datetime | None
    notes: str | None
    extra_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingPlanOut(BaseModel):
    id: UUID
    gym_id: UUID
    member_id: UUID
    assessment_id: UUID | None
    created_by_user_id: UUID | None
    name: str
    objective: str | None
    sessions_per_week: int
    split_type: str | None
    start_date: date
    end_date: date | None
    is_active: bool
    plan_data: dict
    notes: str | None
    extra_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberConstraintsOut(BaseModel):
    id: UUID
    gym_id: UUID
    member_id: UUID
    medical_conditions: str | None
    injuries: str | None
    medications: str | None
    contraindications: str | None
    preferred_training_times: str | None
    restrictions: dict
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberMiniOut(BaseModel):
    id: UUID
    full_name: str
    plan_name: str
    risk_level: RiskLevel
    risk_score: int
    email: str | None = None
    preferred_shift: str | None = None
    last_checkin_at: datetime | None = None
    extra_data: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class AssessmentQueueItemOut(BaseModel):
    id: UUID
    full_name: str
    email: str | None = None
    plan_name: str
    preferred_shift: str | None = None
    risk_level: RiskLevel
    risk_score: int
    last_checkin_at: datetime | None = None
    next_assessment_due: date | None = None
    queue_bucket: str
    coverage_label: str
    due_label: str
    urgency_score: int
    queue_resolution_status: str = Field(default="active")
    queue_resolution_label: str | None = None
    queue_resolution_note: str | None = None


class AssessmentQueueResolutionUpdate(BaseModel):
    status: Literal["active", "scheduled", "dismissed"]
    note: str | None = Field(default=None, max_length=280)


class AssessmentQueueResolutionOut(BaseModel):
    member_id: UUID
    status: Literal["active", "scheduled", "dismissed"]
    label: str
    note: str | None = None
    updated_at: datetime | None = None


class Profile360Out(BaseModel):
    member: MemberMiniOut
    latest_assessment: AssessmentMiniOut | None
    constraints: MemberConstraintsOut | None
    goals: list[MemberGoalOut]
    active_training_plan: TrainingPlanOut | None
    insight_summary: str | None = None


class EvolutionOut(BaseModel):
    labels: list[str]
    weight: list[float | None]
    body_fat: list[float | None]
    lean_mass: list[float | None]
    bmi: list[float | None]
    strength: list[int | None]
    flexibility: list[int | None]
    cardio: list[int | None]
    checkins_labels: list[str] = Field(default_factory=list)
    checkins_per_month: list[int] = Field(default_factory=list)
    main_lift_load: list[float | None] = Field(default_factory=list)
    main_lift_label: str | None = None
    deltas: dict[str, float | int | None]


class AssessmentDashboardOut(BaseModel):
    total_members: int
    assessed_last_90_days: int
    overdue_assessments: int
    never_assessed: int
    upcoming_7_days: int
    historical_backlog_total: int = 0
    historical_never_assessed: int = 0
    historical_overdue_assessments: int = 0
    attention_now: list[AssessmentQueueItemOut] = Field(default_factory=list)
    total_members_items: list[MemberMiniOut] = Field(default_factory=list)
    assessed_members: list[MemberMiniOut] = Field(default_factory=list)
    overdue_members: list[MemberMiniOut]
    never_assessed_members: list[MemberMiniOut] = Field(default_factory=list)
    upcoming_members: list[MemberMiniOut] = Field(default_factory=list)

class AssessmentFactorOut(BaseModel):
    key: str
    label: str
    score: int
    reason: str


class AssessmentDiagnosisOut(BaseModel):
    primary_bottleneck: str
    primary_bottleneck_label: str
    secondary_bottleneck: str
    secondary_bottleneck_label: str
    explanation: str
    evolution_factors: list[str] = Field(default_factory=list)
    stagnation_factors: list[str] = Field(default_factory=list)
    frustration_risk: int = Field(ge=0, le=100)
    confidence: str
    factors: list[AssessmentFactorOut] = Field(default_factory=list)


class AssessmentForecastOut(BaseModel):
    goal_type: str
    probability_30d: int = Field(ge=0, le=100)
    probability_60d: int = Field(ge=0, le=100)
    probability_90d: int = Field(ge=0, le=100)
    corrected_probability_90d: int = Field(ge=0, le=100)
    likely_days_to_goal: int | None = None
    current_summary: str
    corrected_summary: str
    consistency_score: int = Field(ge=0, le=100)
    progress_score: int = Field(ge=0, le=100)
    adherence_score: int = Field(ge=0, le=100)
    recovery_score: int = Field(ge=0, le=100)
    overall_score: int = Field(ge=0, le=100)
    blocked: bool
    confidence: str


class AssessmentBenchmarkOut(BaseModel):
    cohort_label: str
    sample_size: int
    percentile: int = Field(ge=0, le=100)
    expected_curve_status: str
    explanation: str
    position_label: str
    peer_average_score: float | None = None


class AssessmentNarrativesOut(BaseModel):
    coach_summary: str
    member_summary: str
    retention_summary: str


class AssessmentActionOut(BaseModel):
    key: str
    title: str
    owner_role: str
    priority: str
    reason: str
    due_in_days: int
    suggested_message: str


class AssessmentSummary360Out(BaseModel):
    member: MemberMiniOut
    latest_assessment: AssessmentMiniOut | None = None
    goal_type: str
    status: str
    days_since_last_checkin: int | None = None
    recent_weekly_checkins: float
    target_frequency_per_week: int
    forecast: AssessmentForecastOut
    diagnosis: AssessmentDiagnosisOut
    benchmark: AssessmentBenchmarkOut
    narratives: AssessmentNarrativesOut
    next_best_action: AssessmentActionOut
    actions: list[AssessmentActionOut] = Field(default_factory=list)
    assistant: AIAssistantPayload | None = None
