from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.assistant import AIAssistantPayload


EvaluationSource = Literal["tezewa", "manual", "ocr_receipt", "device_import", "actuar_sync"]
ActuarSyncMode = Literal["disabled", "http_api", "csv_export", "assisted_rpa"]
ActuarSyncStatus = Literal["disabled", "pending", "exported", "synced", "failed", "skipped"]
ActuarSyncAttemptStatus = Literal["pending", "processing", "exported", "synced", "failed", "skipped", "disabled"]
OcrWarningSeverity = Literal["warning", "critical"]
BodyCompositionDeviceProfile = Literal["tezewa_receipt_v1"]
BodyCompositionOcrEngine = Literal["local", "ai_fallback", "hybrid"]


class BodyCompositionRangeValue(BaseModel):
    min: float | None = None
    max: float | None = None


class BodyCompositionOcrWarning(BaseModel):
    field: str | None = None
    message: str
    severity: OcrWarningSeverity = "warning"


class BodyCompositionOcrValues(BaseModel):
    evaluation_date: str | None = None
    weight_kg: float | None = None
    body_fat_kg: float | None = None
    body_fat_percent: float | None = None
    waist_hip_ratio: float | None = None
    fat_free_mass_kg: float | None = None
    inorganic_salt_kg: float | None = None
    muscle_mass_kg: float | None = None
    protein_kg: float | None = None
    body_water_kg: float | None = None
    lean_mass_kg: float | None = None
    body_water_percent: float | None = None
    visceral_fat_level: float | None = None
    bmi: float | None = None
    basal_metabolic_rate_kcal: float | None = None
    skeletal_muscle_kg: float | None = None
    target_weight_kg: float | None = None
    weight_control_kg: float | None = None
    muscle_control_kg: float | None = None
    fat_control_kg: float | None = None
    total_energy_kcal: float | None = None
    physical_age: int | None = None
    health_score: int | None = None


class BodyCompositionImageOcrPayload(BaseModel):
    device_profile: BodyCompositionDeviceProfile = "tezewa_receipt_v1"
    device_model: str | None = None
    values: BodyCompositionOcrValues = Field(default_factory=BodyCompositionOcrValues)
    ranges: dict[str, BodyCompositionRangeValue] = Field(default_factory=dict)
    warnings: list[BodyCompositionOcrWarning] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
    raw_text: str = ""
    needs_review: bool = False


class BodyCompositionImageParseResultRead(BodyCompositionImageOcrPayload):
    engine: BodyCompositionOcrEngine
    fallback_used: bool = False


class BodyCompositionEvaluationBase(BaseModel):
    evaluation_date: date
    weight_kg: float | None = Field(default=None, gt=0)
    body_fat_kg: float | None = Field(default=None)
    body_fat_percent: float | None = Field(default=None, ge=0, le=100)
    waist_hip_ratio: float | None = Field(default=None, ge=0)
    fat_free_mass_kg: float | None = Field(default=None)
    inorganic_salt_kg: float | None = Field(default=None)
    protein_kg: float | None = Field(default=None)
    body_water_kg: float | None = Field(default=None)
    # Legacy compatibility field for older screens/data. fat_free_mass_kg is the canonical modern field.
    lean_mass_kg: float | None = Field(default=None)
    muscle_mass_kg: float | None = Field(default=None)
    skeletal_muscle_kg: float | None = Field(default=None)
    body_water_percent: float | None = Field(default=None, ge=0, le=100)
    visceral_fat_level: float | None = Field(default=None, ge=0)
    bmi: float | None = Field(default=None, gt=0)
    basal_metabolic_rate_kcal: float | None = Field(default=None)
    target_weight_kg: float | None = Field(default=None)
    weight_control_kg: float | None = Field(default=None)
    muscle_control_kg: float | None = Field(default=None)
    fat_control_kg: float | None = Field(default=None)
    total_energy_kcal: float | None = Field(default=None)
    physical_age: int | None = Field(default=None, ge=0)
    health_score: int | None = Field(default=None, ge=0)
    source: EvaluationSource = "manual"
    notes: str | None = None
    report_file_url: str | None = None
    raw_ocr_text: str | None = None
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    ocr_warnings_json: list[BodyCompositionOcrWarning] | None = None
    needs_review: bool = False
    reviewed_manually: bool = False
    device_model: str | None = None
    device_profile: str | None = None
    parsed_from_image: bool = False
    ocr_source_file_ref: str | None = None
    measured_ranges_json: dict[str, BodyCompositionRangeValue] | None = None


class BodyCompositionEvaluationCreate(BodyCompositionEvaluationBase):
    pass


class BodyCompositionEvaluationUpdate(BodyCompositionEvaluationBase):
    pass


class BodyCompositionSyncAttemptRead(BaseModel):
    id: UUID
    gym_id: UUID
    body_composition_evaluation_id: UUID
    sync_mode: ActuarSyncMode
    provider: str
    status: ActuarSyncAttemptStatus
    error: str | None
    payload_snapshot_json: dict | list | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BodyCompositionActuarSyncStatusRead(BaseModel):
    evaluation_id: UUID
    sync_mode: ActuarSyncMode
    sync_status: ActuarSyncStatus
    external_id: str | None
    last_synced_at: datetime | None
    last_error: str | None
    can_retry: bool
    attempts: list[BodyCompositionSyncAttemptRead]


class BodyCompositionEvaluationRead(BodyCompositionEvaluationBase):
    id: UUID
    gym_id: UUID
    member_id: UUID
    ai_coach_summary: str | None
    ai_member_friendly_summary: str | None
    ai_risk_flags_json: list[str] | None
    ai_training_focus_json: dict | None
    ai_generated_at: datetime | None
    actuar_sync_status: ActuarSyncStatus
    actuar_sync_mode: ActuarSyncMode
    actuar_external_id: str | None
    actuar_last_synced_at: datetime | None
    actuar_last_error: str | None
    created_at: datetime
    updated_at: datetime
    assistant: AIAssistantPayload | None = None

    model_config = ConfigDict(from_attributes=True)
