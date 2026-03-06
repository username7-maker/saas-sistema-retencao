from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class PublicDiagnosisQueuedResponse(BaseModel):
    message: str
    diagnosis_id: UUID
    lead_id: UUID


class PublicObjectionRequest(BaseModel):
    message_text: str = Field(min_length=2, max_length=3000)
    lead_id: UUID | None = None
    context: dict | None = None


class PublicObjectionResponse(BaseModel):
    matched: bool
    objection_id: UUID | None = None
    response_text: str
    source: str


class PublicProposalRequest(BaseModel):
    lead_id: UUID | None = None
    prospect_name: str = Field(min_length=2, max_length=120)
    gym_name: str = Field(min_length=2, max_length=120)
    total_members: int = Field(ge=1, le=20000)
    avg_monthly_fee: Decimal = Field(ge=0)
    diagnosed_red: int = Field(ge=0)
    diagnosed_yellow: int = Field(ge=0)
    email: EmailStr | None = None
