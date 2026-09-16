from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class RetentionExclusionCreate(BaseModel):
    scope: Literal["member", "plan"]
    member_id: UUID | None = None
    plan_name: str | None = Field(default=None, max_length=100)
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_target(self):
        if self.scope == "member" and self.member_id is None:
            raise ValueError("member_id e obrigatorio para exclusao individual")
        if self.scope == "plan" and not (self.plan_name or "").strip():
            raise ValueError("plan_name e obrigatorio para exclusao por plano")
        return self


class RetentionExclusionOut(BaseModel):
    id: UUID
    scope: Literal["member", "plan"]
    member_id: UUID | None = None
    member_name: str | None = None
    plan_name: str | None = None
    reason: str | None = None
    created_by_name: str
    created_at: datetime


class RetentionExclusionListOut(BaseModel):
    items: list[RetentionExclusionOut]
    total: int
