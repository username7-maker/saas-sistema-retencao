from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AutopilotEventOut(BaseModel):
    id: UUID
    gym_id: UUID
    event_type: str
    source: str
    member_id: UUID | None
    lead_id: UUID | None
    task_id: UUID | None
    autopilot_action_id: UUID | None
    occurred_at: datetime
    received_at: datetime
    metadata_json: dict = Field(default_factory=dict)
    deduplication_key: str | None
    correlation_id: str | None
    created_by_system: bool
    raw_payload_hash: str | None
    processed_at: datetime | None
    processing_status: str
    processing_error: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AutopilotActionOut(BaseModel):
    id: UUID
    gym_id: UUID
    policy_key: str
    domain: str
    action_type: str
    status: str
    member_id: UUID | None
    lead_id: UUID | None
    related_task_id: UUID | None
    channel: str
    template_key: str | None
    message_body: str | None
    scheduled_for: datetime | None
    executed_at: datetime | None
    completed_at: datetime | None
    timeout_at: datetime | None
    attempt_number: int
    max_attempts: int
    cooldown_until: datetime | None
    outcome: str | None
    failure_reason: str | None
    escalation_reason: str | None
    idempotency_key: str | None
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AutopilotSettingsOut(BaseModel):
    autopilot_enabled: bool = False
    autopilot_auto_close_enabled: bool = True
    autopilot_auto_send_enabled: bool = False
    retention_enabled: bool = True
    finance_enabled: bool = True
    sales_enabled: bool = False
    onboarding_enabled: bool = True
    assessment_enabled: bool = True
    nps_enabled: bool = True
    business_hours_start: str = "08:00"
    business_hours_end: str = "20:00"
    max_auto_messages_per_member_per_week: int = 2
    max_auto_messages_per_lead_per_week: int = 3
    max_auto_actions_per_day: int = 100
    max_human_tasks_created_by_autopilot_per_day: int = 25
    default_timeout_hours: int = 48
    human_recent_activity_cooldown_hours: int = 24
    extra_data: dict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class AutopilotSettingsUpdate(BaseModel):
    autopilot_enabled: bool | None = None
    autopilot_auto_close_enabled: bool | None = None
    autopilot_auto_send_enabled: bool | None = None
    retention_enabled: bool | None = None
    finance_enabled: bool | None = None
    sales_enabled: bool | None = None
    onboarding_enabled: bool | None = None
    assessment_enabled: bool | None = None
    nps_enabled: bool | None = None
    business_hours_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    business_hours_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    max_auto_messages_per_member_per_week: int | None = Field(default=None, ge=0, le=20)
    max_auto_messages_per_lead_per_week: int | None = Field(default=None, ge=0, le=30)
    max_auto_actions_per_day: int | None = Field(default=None, ge=0, le=5000)
    max_human_tasks_created_by_autopilot_per_day: int | None = Field(default=None, ge=0, le=1000)
    default_timeout_hours: int | None = Field(default=None, ge=1, le=168)
    human_recent_activity_cooldown_hours: int | None = Field(default=None, ge=0, le=168)
    extra_data: dict | None = None


class AutopilotMetricRatesOut(BaseModel):
    autopilot_resolution_rate: float | None = None
    human_task_avoidance_rate: float | None = None


class AutopilotMetricsOut(BaseModel):
    period: dict
    automation_actions: dict
    tasks: dict
    rates: AutopilotMetricRatesOut
    by_domain: dict
    by_template: dict
    blocked_reasons: dict


class AutopilotTimelineItemOut(BaseModel):
    kind: str
    label: str
    detail: str | None = None
    occurred_at: datetime
    metadata: dict = Field(default_factory=dict)


class WorkQueueSendAndWaitInput(BaseModel):
    template_key: str | None = Field(default=None, max_length=100)
    message: str | None = Field(default=None, max_length=1000)
    operator_note: str | None = Field(default=None, max_length=280)
    channel: str | None = Field(default="auto", pattern="^(auto|kommo|whatsapp|manual)$")
