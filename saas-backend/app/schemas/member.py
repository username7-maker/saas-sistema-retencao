from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import MemberStatus, RiskLevel
from app.schemas.assistant import AIAssistantPayload


class MemberCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=14)
    birthdate: date | None = None
    plan_name: str = "Plano Base"
    monthly_fee: Decimal = Decimal("0")
    join_date: date = Field(default_factory=date.today)
    preferred_shift: str | None = None
    assigned_user_id: UUID | None = None
    loyalty_months: int = 0
    extra_data: dict = Field(default_factory=dict)


class MemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    cpf: str | None = Field(default=None, min_length=11, max_length=14)
    birthdate: date | None = None
    status: MemberStatus | None = None
    plan_name: str | None = None
    monthly_fee: Decimal | None = None
    preferred_shift: str | None = None
    assigned_user_id: UUID | None = None
    loyalty_months: int | None = None
    nps_last_score: int | None = Field(default=None, ge=0, le=10)
    extra_data: dict | None = None


class MemberOut(BaseModel):
    id: UUID
    full_name: str
    email: str | None
    phone: str | None
    birthdate: date | None = None
    status: MemberStatus
    plan_name: str
    monthly_fee: Decimal
    join_date: date
    preferred_shift: str | None
    nps_last_score: int
    loyalty_months: int
    risk_score: int
    risk_level: RiskLevel
    last_checkin_at: datetime | None
    extra_data: dict = Field(default_factory=dict)
    suggested_action: str | None = None
    onboarding_score: int = 0
    onboarding_status: str = "active"
    churn_type: str | None = None
    is_vip: bool = False
    retention_stage: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberRiskOut(BaseModel):
    member_id: UUID
    score: int
    level: RiskLevel
    reasons: dict


class OnboardingScoreOut(BaseModel):
    score: int
    status: str
    factors: dict[str, int]
    days_since_join: int
    checkin_count: int
    completed_tasks: int
    total_tasks: int
    assistant: AIAssistantPayload | None = None


class MemberBulkUpdateChanges(BaseModel):
    status: MemberStatus | None = None
    plan_name: str | None = Field(default=None, min_length=1, max_length=100)
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    preferred_shift: str | None = Field(default=None, max_length=24)

    @model_validator(mode="after")
    def validate_has_changes(self) -> "MemberBulkUpdateChanges":
        if not self.model_dump(exclude_none=True):
            raise ValueError("Informe ao menos um campo para atualizar em massa.")
        return self


class MemberBulkUpdateFilters(BaseModel):
    search: str | None = None
    risk_level: RiskLevel | None = None
    status: MemberStatus | None = None
    plan_cycle: Literal["monthly", "semiannual", "annual"] | None = None
    min_days_without_checkin: int | None = Field(default=None, ge=0)
    provisional_only: bool | None = None


class MemberBulkUpdatePreviewInput(BaseModel):
    target_mode: Literal["selected", "filtered"]
    selected_member_ids: list[UUID] = Field(default_factory=list)
    filters: MemberBulkUpdateFilters = Field(default_factory=MemberBulkUpdateFilters)
    changes: MemberBulkUpdateChanges

    @model_validator(mode="after")
    def validate_target(self) -> "MemberBulkUpdatePreviewInput":
        if self.target_mode == "selected" and not self.selected_member_ids:
            raise ValueError("Selecione ao menos um membro para usar o alvo por selecao.")
        return self


class MemberBulkUpdatePreviewMember(BaseModel):
    id: UUID
    full_name: str
    email: str | None = None
    current_values: dict[str, object | None]
    next_values: dict[str, object | None]


class MemberBulkUpdatePreviewOut(BaseModel):
    target_mode: Literal["selected", "filtered"]
    target_description: str
    total_candidates: int
    would_update: int
    unchanged: int
    changed_fields: list[str]
    sample_members: list[MemberBulkUpdatePreviewMember]


class MemberBulkUpdateCommitInput(MemberBulkUpdatePreviewInput):
    pass


class MemberBulkUpdateResultOut(BaseModel):
    target_mode: Literal["selected", "filtered"]
    target_description: str
    updated: int
    unchanged: int
    changed_fields: list[str]
