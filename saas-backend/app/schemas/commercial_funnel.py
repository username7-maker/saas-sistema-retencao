"""Schemas do funil semanal esforço→resultado (spec 053 / slot M1/funnel-api)."""
from datetime import datetime

from pydantic import BaseModel


class FunnelStage(BaseModel):
    key: str
    label: str
    value: int
    previous_value: int


class ConversionBreakdown(BaseModel):
    leads_won: int
    members_joined: int
    risk_recovered: int


class WeeklyFunnelResponse(BaseModel):
    week_start: datetime
    week_end: datetime
    week_offset: int
    contacts: FunnelStage
    responses: FunnelStage
    conversions: FunnelStage
    conversion_breakdown: ConversionBreakdown
