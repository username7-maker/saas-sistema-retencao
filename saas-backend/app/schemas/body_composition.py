from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BodyCompositionEvaluationCreate(BaseModel):
    evaluation_date: date
    weight_kg: float | None = Field(default=None, gt=0)
    body_fat_percent: float | None = Field(default=None, ge=0, le=100)
    lean_mass_kg: float | None = Field(default=None, gt=0)
    muscle_mass_kg: float | None = Field(default=None, gt=0)
    body_water_percent: float | None = Field(default=None, ge=0, le=100)
    visceral_fat_level: float | None = Field(default=None, ge=0)
    bmi: float | None = Field(default=None, gt=0)
    basal_metabolic_rate_kcal: float | None = Field(default=None, gt=0)
    source: Literal["tezewa", "manual"] = "tezewa"
    notes: str | None = None
    report_file_url: str | None = None


class BodyCompositionEvaluationRead(BodyCompositionEvaluationCreate):
    id: UUID
    gym_id: UUID
    member_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
