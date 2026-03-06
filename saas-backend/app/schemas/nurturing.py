from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class NurturingSequenceOut(BaseModel):
    id: UUID
    gym_id: UUID | None
    lead_id: UUID | None
    prospect_email: EmailStr
    prospect_whatsapp: str
    prospect_name: str
    diagnosis_data: dict
    current_step: int
    next_send_at: datetime
    completed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
