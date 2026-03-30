from pydantic import BaseModel, ConfigDict, Field


class ActuarSettingsRead(BaseModel):
    actuar_enabled: bool
    actuar_auto_sync_body_composition: bool
    actuar_base_url: str | None = None
    actuar_username: str | None = None
    actuar_has_password: bool
    environment_enabled: bool
    environment_sync_mode: str
    effective_sync_mode: str
    automatic_sync_ready: bool


class ActuarSettingsUpdate(BaseModel):
    actuar_enabled: bool
    actuar_auto_sync_body_composition: bool
    actuar_base_url: str | None = Field(default=None, max_length=255)
    actuar_username: str | None = Field(default=None, max_length=120)
    actuar_password: str | None = Field(default=None, max_length=255)
    clear_password: bool = False


class ActuarConnectionTestResult(BaseModel):
    success: bool
    provider: str
    effective_sync_mode: str
    automatic_sync_ready: bool
    message: str
    detail: str | None = None


class ActuarSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    settings: ActuarSettingsRead
    last_connection_test: ActuarConnectionTestResult | None = None


class KommoSettingsRead(BaseModel):
    kommo_enabled: bool
    kommo_base_url: str | None = None
    kommo_has_access_token: bool
    kommo_default_pipeline_id: str | None = None
    kommo_default_stage_id: str | None = None
    kommo_default_responsible_user_id: str | None = None
    automatic_handoff_ready: bool


class KommoSettingsUpdate(BaseModel):
    kommo_enabled: bool
    kommo_base_url: str | None = Field(default=None, max_length=255)
    kommo_access_token: str | None = Field(default=None, max_length=1024)
    kommo_default_pipeline_id: str | None = Field(default=None, max_length=40)
    kommo_default_stage_id: str | None = Field(default=None, max_length=40)
    kommo_default_responsible_user_id: str | None = Field(default=None, max_length=40)
    clear_access_token: bool = False


class KommoConnectionTestResult(BaseModel):
    success: bool
    automatic_handoff_ready: bool
    message: str
    detail: str | None = None
    base_url: str | None = None
