from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.assistant import AIAssistantPayload


EvaluationSource = Literal["tezewa", "manual", "ocr_receipt", "device_import", "actuar_sync"]
ActuarSyncMode = Literal["disabled", "http_api", "csv_export", "assisted_rpa"]
ActuarSyncStatus = Literal[
    "draft",
    "saved",
    "sync_pending",
    "syncing",
    "synced_to_actuar",
    "sync_failed",
    "needs_review",
    "manual_sync_required",
]
ActuarSyncAttemptStatus = Literal["pending", "processing", "exported", "synced", "failed", "skipped", "disabled"]
ActuarSyncJobStatus = Literal["pending", "processing", "synced", "failed", "needs_review", "cancelled"]
ActuarSyncJobType = Literal["body_composition_push"]
ActuarSyncAttemptV2Status = Literal["started", "succeeded", "failed"]
ActuarFieldClassification = Literal["critical_direct", "critical_derived", "non_critical_direct", "unsupported", "text_note_only"]
OcrWarningSeverity = Literal["warning", "critical"]
BodyCompositionDeviceProfile = Literal["tezewa_receipt_v1"]
BodyCompositionOcrEngine = Literal["local", "ai_assisted", "ai_fallback", "hybrid"]


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
    member_id: UUID
    sync_mode: ActuarSyncMode
    sync_status: ActuarSyncStatus
    training_ready: bool
    sync_required_for_training: bool
    external_id: str | None
    last_synced_at: datetime | None
    last_attempt_at: datetime | None
    last_error_code: str | None
    last_error: str | None
    can_retry: bool
    critical_fields: list[dict]
    unsupported_fields: list["ActuarFieldMappingRead"] = Field(default_factory=list)
    fallback_manual_summary: dict
    current_job: "ActuarSyncJobRead | None"
    attempts: list["ActuarSyncAttemptRead"]
    member_link: "ActuarMemberLinkRead | None"


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
    sync_required_for_training: bool
    sync_last_attempt_at: datetime | None
    sync_last_success_at: datetime | None
    sync_last_error_code: str | None
    sync_last_error_message: str | None
    actuar_sync_job_id: UUID | None
    training_ready: bool
    created_at: datetime
    updated_at: datetime
    assistant: AIAssistantPayload | None = None

    model_config = ConfigDict(from_attributes=True)


class ActuarFieldMappingRead(BaseModel):
    field: str
    actuar_field: str | None = None
    value: str | float | int | bool | None = None
    classification: ActuarFieldClassification
    required: bool = False
    supported: bool = True


class ActuarMemberLinkRead(BaseModel):
    id: UUID
    member_id: UUID
    actuar_external_id: str | None
    actuar_search_name: str | None
    actuar_search_birthdate: date | None
    linked_at: datetime | None
    linked_by_user_id: UUID | None
    match_confidence: float | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ActuarMemberLinkUpsert(BaseModel):
    actuar_external_id: str | None = None
    actuar_search_name: str | None = None
    actuar_search_document: str | None = None
    actuar_search_birthdate: date | None = None
    match_confidence: float | None = None


class ActuarSyncJobRead(BaseModel):
    id: UUID
    gym_id: UUID
    member_id: UUID
    body_composition_evaluation_id: UUID
    job_type: ActuarSyncJobType
    status: ActuarSyncJobStatus
    error_code: str | None
    error_message: str | None
    retry_count: int
    max_retries: int
    next_retry_at: datetime | None
    locked_at: datetime | None
    locked_by: str | None
    synced_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActuarSyncAttemptRead(BaseModel):
    id: UUID
    gym_id: UUID
    sync_job_id: UUID
    started_at: datetime
    finished_at: datetime | None
    status: ActuarSyncAttemptV2Status
    action_log_json: list[dict] | list | None
    screenshot_path: str | None
    page_html_path: str | None
    error_code: str | None
    error_message: str | None
    worker_id: str | None

    model_config = ConfigDict(from_attributes=True)


class ActuarManualSyncConfirmInput(BaseModel):
    reason: str = Field(min_length=3, max_length=200)
    note: str | None = Field(default=None, max_length=500)


class BodyCompositionManualSyncSummaryRead(BaseModel):
    evaluation_id: UUID
    member_id: UUID
    sync_status: ActuarSyncStatus
    training_ready: bool
    critical_fields: list[ActuarFieldMappingRead]
    summary_text: str


class BodyCompositionWhatsAppDispatchRead(BaseModel):
    log_id: UUID
    member_id: UUID
    evaluation_id: UUID
    status: str
    recipient: str
    pdf_filename: str | None = None
    error_detail: str | None = None


class ActuarSyncQueueItemRead(BaseModel):
    evaluation_id: UUID
    member_id: UUID
    member_name: str
    evaluation_date: date
    sync_status: ActuarSyncStatus
    training_ready: bool
    error_code: str | None
    error_message: str | None
    next_retry_at: datetime | None
    current_job: ActuarSyncJobRead | None


BodyCompositionActuarSyncStatusRead.model_rebuild()
