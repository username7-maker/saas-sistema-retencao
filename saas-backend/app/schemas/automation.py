from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AutomationRuleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    trigger_type: str = Field(min_length=2, max_length=40)
    trigger_config: dict = Field(default_factory=dict)
    action_type: str = Field(min_length=2, max_length=40)
    action_config: dict = Field(default_factory=dict)
    is_active: bool = True


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
    automation_rule_id: UUID | None
    channel: str
    recipient: str
    template_name: str | None
    content: str
    status: str
    error_detail: str | None
    extra_data: dict
    created_at: datetime


class AutomationExecutionResult(BaseModel):
    rule_id: UUID
    rule_name: str
    members_affected: int
    actions_executed: int
    errors: list[str] = Field(default_factory=list)
