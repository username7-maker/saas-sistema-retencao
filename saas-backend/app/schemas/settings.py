from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.actuar_bridge import ActuarBridgeDeviceRead


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
    bridge_device_count: int = 0
    bridge_online_device_count: int = 0
    bridge_devices: list[ActuarBridgeDeviceRead] = Field(default_factory=list)


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


class KommoDomainRouteRead(BaseModel):
    domain: str
    is_enabled: bool = True
    route_status: str = "missing"
    missing_fields: list[str] = Field(default_factory=list)
    ready_for_messages: bool = False
    ready_for_native_pdf: bool = False
    ready_for_link_pdf: bool = False
    pipeline_id: str | None = None
    stage_id: str | None = None
    salesbot_id: str | None = None
    channel_source_id: str | None = None
    responsible_user_id: str | None = None
    message_field_id: str | None = None
    pdf_url_field_id: str | None = None
    pdf_delivery_mode: str = "native_file_required"
    file_uuid_field_id: str | None = None
    file_name_field_id: str | None = None
    file_attachment_note_field_id: str | None = None
    source_type_field_id: str | None = None
    source_id_field_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class KommoDomainRouteUpdate(BaseModel):
    domain: str = Field(max_length=40)
    is_enabled: bool = True
    pipeline_id: str | None = Field(default=None, max_length=40)
    stage_id: str | None = Field(default=None, max_length=40)
    salesbot_id: str | None = Field(default=None, max_length=40)
    channel_source_id: str | None = Field(default=None, max_length=80)
    responsible_user_id: str | None = Field(default=None, max_length=40)
    message_field_id: str | None = Field(default=None, max_length=40)
    pdf_url_field_id: str | None = Field(default=None, max_length=40)
    pdf_delivery_mode: str | None = Field(default=None, pattern="^(native_file_required|native_file_preferred|link_only)$")
    file_uuid_field_id: str | None = Field(default=None, max_length=40)
    file_name_field_id: str | None = Field(default=None, max_length=40)
    file_attachment_note_field_id: str | None = Field(default=None, max_length=40)
    source_type_field_id: str | None = Field(default=None, max_length=40)
    source_id_field_id: str | None = Field(default=None, max_length=40)
    tags: list[str] = Field(default_factory=list)


class KommoTrainerRouteRead(BaseModel):
    trainer_user_id: UUID
    trainer_name: str | None = None
    is_enabled: bool = True
    route_status: str = "missing"
    missing_fields: list[str] = Field(default_factory=list)
    ready_for_messages: bool = False
    ready_for_native_pdf: bool = False
    ready_for_link_pdf: bool = False
    pipeline_id: str | None = None
    stage_id: str | None = None
    salesbot_id: str | None = None
    channel_source_id: str | None = None
    responsible_user_id: str | None = None
    message_field_id: str | None = None
    pdf_url_field_id: str | None = None
    pdf_delivery_mode: str = "native_file_required"
    file_uuid_field_id: str | None = None
    file_name_field_id: str | None = None
    file_attachment_note_field_id: str | None = None
    source_type_field_id: str | None = None
    source_id_field_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class KommoTrainerRouteUpdate(BaseModel):
    trainer_user_id: UUID
    is_enabled: bool = True
    pipeline_id: str | None = Field(default=None, max_length=40)
    stage_id: str | None = Field(default=None, max_length=40)
    salesbot_id: str | None = Field(default=None, max_length=40)
    channel_source_id: str | None = Field(default=None, max_length=80)
    responsible_user_id: str | None = Field(default=None, max_length=40)
    message_field_id: str | None = Field(default=None, max_length=40)
    pdf_url_field_id: str | None = Field(default=None, max_length=40)
    pdf_delivery_mode: str | None = Field(default=None, pattern="^(native_file_required|native_file_preferred|link_only)$")
    file_uuid_field_id: str | None = Field(default=None, max_length=40)
    file_name_field_id: str | None = Field(default=None, max_length=40)
    file_attachment_note_field_id: str | None = Field(default=None, max_length=40)
    source_type_field_id: str | None = Field(default=None, max_length=40)
    source_id_field_id: str | None = Field(default=None, max_length=40)
    tags: list[str] = Field(default_factory=list)


class KommoSettingsRead(BaseModel):
    kommo_enabled: bool
    kommo_base_url: str | None = None
    kommo_has_access_token: bool
    kommo_default_pipeline_id: str | None = None
    kommo_default_stage_id: str | None = None
    kommo_default_responsible_user_id: str | None = None
    automatic_handoff_ready: bool
    primary_message_channel: str = "whatsapp"
    kommo_operator_confirmed_send_enabled: bool = True
    kommo_auto_close_enabled: bool = True
    kommo_fallback_channel: str = "whatsapp"
    domain_routes: list[KommoDomainRouteRead] = Field(default_factory=list)
    trainer_routes: list[KommoTrainerRouteRead] = Field(default_factory=list)


class KommoSettingsUpdate(BaseModel):
    kommo_enabled: bool
    kommo_base_url: str | None = Field(default=None, max_length=255)
    kommo_access_token: str | None = Field(default=None, max_length=4096)
    kommo_default_pipeline_id: str | None = Field(default=None, max_length=40)
    kommo_default_stage_id: str | None = Field(default=None, max_length=40)
    kommo_default_responsible_user_id: str | None = Field(default=None, max_length=40)
    clear_access_token: bool = False
    primary_message_channel: str | None = Field(default=None, pattern="^(kommo|whatsapp|manual)$")
    kommo_operator_confirmed_send_enabled: bool | None = None
    kommo_auto_close_enabled: bool | None = None
    kommo_fallback_channel: str | None = Field(default=None, pattern="^(whatsapp|manual)$")
    domain_routes: list[KommoDomainRouteUpdate] | None = None
    trainer_routes: list[KommoTrainerRouteUpdate] | None = None


class KommoConnectionTestResult(BaseModel):
    success: bool
    automatic_handoff_ready: bool
    message: str
    detail: str | None = None
    base_url: str | None = None
