from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.automation_rule import AutomationAction, AutomationTrigger


VALID_TRIGGERS = {
    AutomationTrigger.RISK_LEVEL_CHANGE,
    AutomationTrigger.INACTIVITY_DAYS,
    AutomationTrigger.NPS_SCORE,
    AutomationTrigger.LEAD_STALE,
    AutomationTrigger.BIRTHDAY,
    AutomationTrigger.CHECKIN_STREAK,
}
VALID_ACTIONS = {
    AutomationAction.CREATE_TASK,
    AutomationAction.SEND_WHATSAPP,
    AutomationAction.SEND_EMAIL,
    AutomationAction.NOTIFY,
    AutomationAction.SEND_TO_KOMMO,
}


class AutomationRuleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    trigger_type: str = Field(min_length=2, max_length=40)
    trigger_config: dict = Field(default_factory=dict)
    action_type: str = Field(min_length=2, max_length=40)
    action_config: dict = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("trigger_type")
    @classmethod
    def validate_trigger_type(cls, value: str) -> str:
        if value not in VALID_TRIGGERS:
            raise ValueError("Gatilho de automacao invalido")
        return value

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, value: str) -> str:
        if value not in VALID_ACTIONS:
            raise ValueError("Acao de automacao invalida")
        return value


class AutomationRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=160)
    description: str | None = None
    trigger_config: dict | None = None
    action_config: dict | None = None
    is_active: bool | None = None


class AutomationRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    trigger_type: str
    trigger_config: dict
    action_type: str
    action_config: dict
    is_active: bool
    executions_count: int
    last_executed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MessageLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID | None
    lead_id: UUID | None
    automation_rule_id: UUID | None
    channel: str
    recipient: str
    template_name: str | None
    content: str
    status: str
    direction: str | None
    event_type: str | None
    provider_message_id: str | None
    error_detail: str | None
    extra_data: dict
    created_at: datetime


class AutomationExecutionResult(BaseModel):
    rule_id: UUID
    rule_name: str
    members_affected: int
    actions_executed: int
    errors: list[str] = Field(default_factory=list)


class WhatsAppSendRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    message: str = Field(min_length=1, max_length=4096)
    member_id: UUID | None = None
    template_name: str | None = None
