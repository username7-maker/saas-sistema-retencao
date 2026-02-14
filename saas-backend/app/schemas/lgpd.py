from datetime import date
from uuid import UUID

from pydantic import BaseModel


class MemberLGPDExport(BaseModel):
    member_id: UUID
    full_name: str
    email: str | None
    phone: str | None
    plan_name: str
    join_date: date
    status: str
    checkins_total: int
    nps_total: int
    risk_score: int
    risk_level: str
