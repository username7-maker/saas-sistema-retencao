from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


MethodPillar = Literal["acquisition", "sales", "post_sale"]
ClientStatus = Literal["prospect", "onboarding", "active", "paused", "churned"]
PersonType = Literal["lead", "customer", "inactive_customer", "prospect"]
EventSource = Literal["manual", "import", "integration", "automation", "ai"]
MethodTaskPriority = Literal["low", "medium", "high", "critical"]
MethodTaskStatus = Literal["open", "in_progress", "done", "dismissed", "expired"]
HumanActionType = Literal["whatsapp", "call", "email", "in_person", "internal_note", "other"]
HumanActionResult = Literal[
    "no_response",
    "responded",
    "scheduled",
    "bought",
    "returned",
    "renewed",
    "lost",
    "dismissed",
    "other",
]
MethodReportType = Literal["weekly", "monthly", "pilot", "internal"]
MethodImportType = Literal["people", "events"]


class SegmentOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    default_entry_pillar: MethodPillar
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SegmentPlaybookOut(BaseModel):
    id: UUID
    segment_id: UUID
    channels: list[str] = Field(default_factory=list)
    qualification_questions: list[str] = Field(default_factory=list)
    risk_opportunity_signals: list[str] = Field(default_factory=list)
    message_templates: dict[str, str] = Field(default_factory=dict)
    success_metrics: list[str] = Field(default_factory=list)
    segment: SegmentOut | None = None


class CordexClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    segment_id: UUID | None = None
    status: ClientStatus | None = None
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=40)
    main_contact_name: str | None = Field(default=None, max_length=160)
    main_contact_phone: str | None = Field(default=None, max_length=40)
    main_contact_email: str | None = Field(default=None, max_length=255)


class CordexClientOut(BaseModel):
    cordex_client_id: UUID
    name: str
    slug: str
    is_active: bool
    segment_id: UUID | None = None
    status: str
    city: str | None = None
    state: str | None = None
    main_contact_name: str | None = None
    main_contact_phone: str | None = None
    main_contact_email: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ClientMethodConfigUpdate(BaseModel):
    segment_id: UUID | None = None
    active_pillars: dict[MethodPillar, bool] | None = None
    entry_pillar: MethodPillar | None = None
    toolkit: dict[str, Any] | None = None
    baseline: dict[str, Any] | None = None
    success_criteria: dict[str, Any] | None = None
    cadence: dict[str, Any] | None = None


class ClientMethodConfigOut(BaseModel):
    id: UUID
    cordex_client_id: UUID
    segment_id: UUID | None = None
    active_pillars: dict[str, bool] = Field(default_factory=dict)
    entry_pillar: MethodPillar
    toolkit: dict[str, Any] = Field(default_factory=dict)
    baseline: dict[str, Any] = Field(default_factory=dict)
    success_criteria: dict[str, Any] = Field(default_factory=dict)
    cadence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MethodClientProfileOut(BaseModel):
    client: CordexClientOut
    config: ClientMethodConfigOut
    segment: SegmentOut | None = None
    playbook: SegmentPlaybookOut | None = None


class PersonCreate(BaseModel):
    external_id: str | None = Field(default=None, max_length=120)
    name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=255)
    person_type: PersonType = "lead"
    status: str = Field(default="active", max_length=80)
    source_channel: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonOut(BaseModel):
    id: UUID
    cordex_client_id: UUID
    external_id: str | None = None
    name: str
    phone: str | None = None
    email: str | None = None
    person_type: str
    status: str
    source_channel: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OperationalEventCreate(BaseModel):
    person_id: UUID | None = None
    pillar: MethodPillar
    event_type: str = Field(min_length=2, max_length=80)
    event_source: EventSource = "manual"
    event_payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class OperationalEventOut(BaseModel):
    id: UUID
    cordex_client_id: UUID
    person_id: UUID | None = None
    person_name: str | None = None
    pillar: str
    event_type: str
    event_source: str
    event_payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime
    created_at: datetime


class OperationalTaskMessageUpdate(BaseModel):
    suggested_message: str | None = Field(default=None, max_length=2000)


class OperationalTaskOut(BaseModel):
    id: UUID
    cordex_client_id: UUID
    person_id: UUID | None = None
    person_name: str | None = None
    person_phone: str | None = None
    event_id: UUID | None = None
    pillar: str
    task_type: str
    title: str
    description: str | None = None
    assigned_role: str
    assigned_to: str | None = None
    priority: str
    status: str
    due_date: datetime | None = None
    suggested_message: str | None = None
    wa_me_link: str | None = None
    dismissal_reason: str | None = None
    completed_at: datetime | None = None
    dismissed_at: datetime | None = None
    requires_human_approval: bool = True
    ai_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class HumanActionCreate(BaseModel):
    action_type: HumanActionType
    action_summary: str = Field(min_length=2, max_length=1000)
    result: HumanActionResult
    notes: str | None = Field(default=None, max_length=1500)
    mark_task_status: Literal["done", "dismissed"] | None = None
    dismissal_reason: str | None = Field(default=None, max_length=500)


class HumanActionOut(BaseModel):
    id: UUID
    cordex_client_id: UUID
    person_id: UUID | None = None
    task_id: UUID
    action_type: str
    action_summary: str
    result: str
    notes: str | None = None
    created_by: str
    created_at: datetime


class OutcomeCreate(BaseModel):
    person_id: UUID | None = None
    task_id: UUID | None = None
    action_id: UUID | None = None
    outcome_type: str = Field(min_length=2, max_length=80)
    value_numeric: float | None = None
    value_text: str | None = Field(default=None, max_length=1000)
    measured_at: datetime | None = None


class OutcomeOut(BaseModel):
    id: UUID
    cordex_client_id: UUID
    person_id: UUID | None = None
    task_id: UUID | None = None
    action_id: UUID | None = None
    outcome_type: str
    value_numeric: float | None = None
    value_text: str | None = None
    measured_at: datetime
    created_at: datetime


class MethodDashboardOut(BaseModel):
    cordex_client_id: UUID
    generated_at: datetime
    open_tasks: int = 0
    overdue_tasks: int = 0
    completed_7d: int = 0
    people_total: int = 0
    leads_total: int = 0
    customers_total: int = 0
    opportunities: int = 0
    closed_sales: int = 0
    risk_customers: int = 0
    recovered_customers: int = 0
    by_pillar: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)
    bottlenecks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class MethodInternalDashboardOut(BaseModel):
    generated_at: datetime
    clients_total: int = 1
    current_client: CordexClientOut
    client_summary: MethodDashboardOut


class MethodWeeklyReportRequest(BaseModel):
    period_start: datetime | None = None
    period_end: datetime | None = None


class MethodWeeklyReportOut(BaseModel):
    report_id: UUID | None = None
    cordex_client_id: UUID
    report_type: MethodReportType = "weekly"
    period_start: datetime
    period_end: datetime
    summary: str
    markdown: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    bottlenecks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    requires_human_review: bool = True


class MethodImportPreviewInput(BaseModel):
    import_type: MethodImportType
    filename: str = Field(min_length=1, max_length=255)
    csv_content: str = Field(min_length=1)
    column_mapping: dict[str, str] = Field(default_factory=dict)
    ignored_columns: list[str] = Field(default_factory=list)


class MethodImportPreviewOut(BaseModel):
    import_type: MethodImportType
    total_rows: int
    valid_rows: int
    recognized_columns: list[str] = Field(default_factory=list)
    unrecognized_columns: list[str] = Field(default_factory=list)
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    can_confirm: bool = True


class MethodImportSummaryOut(BaseModel):
    import_type: MethodImportType
    imported: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
    batch_id: UUID | None = None
