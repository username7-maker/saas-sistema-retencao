"""Schemas do cockpit comercial diário (spec 053 / slot M1/cockpit-api)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CockpitLeadFollowup(BaseModel):
    lead_id: UUID
    full_name: str
    phone: str | None
    stage: str
    days_since_contact: int | None
    reason: str
    href: str


class CockpitMemberAttention(BaseModel):
    member_id: UUID
    full_name: str
    risk_level: str
    retention_stage: str | None
    days_without_checkin: int | None
    reason: str
    href: str


class CockpitActionToday(BaseModel):
    task_id: UUID
    title: str
    priority: str
    due_date: datetime | None
    overdue: bool
    target_name: str | None
    href: str


class CockpitCounts(BaseModel):
    leads_followup: int
    members_attention: int
    actions_today: int


class DailyCockpitResponse(BaseModel):
    generated_at: datetime
    leads_followup: list[CockpitLeadFollowup]
    members_attention: list[CockpitMemberAttention]
    actions_today: list[CockpitActionToday]
    triage_pending_count: int
    counts: CockpitCounts
