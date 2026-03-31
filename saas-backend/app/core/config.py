import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    app_name: str = "AI GYM OS"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = False
    enable_scheduler: bool = False
    enable_scheduler_in_api: bool = False
    scheduler_critical_lock_fail_open: bool = False

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/aigymos"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_cookie_name: str = "ai_gym_refresh_token"
    refresh_cookie_domain: str = ""
    refresh_cookie_path: str = "/api/v1/auth"
    refresh_cookie_samesite: str = "lax"
    refresh_cookie_secure: bool = False
    bcrypt_rounds: int = 12

    cpf_encryption_key: str = "change-me-with-64-hex"

    sendgrid_api_key: str = ""
    sendgrid_sender: str = "noreply@aigymos.local"

    claude_api_key: str = ""
    claude_model: str = "claude-3-5-haiku-latest"
    claude_max_tokens: int = 250
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_vision_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: int = 20
    body_composition_image_ai_enabled: bool = False
    claude_vision_model: str = "claude-3-5-sonnet-latest"
    body_composition_image_ai_timeout_seconds: int = 20

    whatsapp_api_url: str = ""
    whatsapp_api_token: str = ""
    public_backend_url: str = ""
    whatsapp_instance: str = "default"
    whatsapp_allow_global_fallback: bool = False
    whatsapp_rate_limit_per_hour: int = 6
    whatsapp_webhook_token: str = ""

    sentry_dsn: str = ""

    redis_url: str = ""
    dashboard_cache_ttl_seconds: int = 300
    dashboard_cache_maxsize: int = 512
    risk_processing_statement_timeout_ms: int = 30000
    risk_processing_batch_size: int = 250
    loyalty_update_batch_size: int = 500
    actuar_enabled: bool = False
    actuar_sync_mode: str = "disabled"
    actuar_base_url: str = ""
    actuar_api_key: str = ""
    actuar_username: str = ""
    actuar_password: str = ""
    actuar_timeout_seconds: int = 15
    actuar_sync_enabled: bool = True
    actuar_browser_headless: bool = True
    actuar_sync_max_retries: int = 3
    actuar_sync_screenshot_on_success: bool = False
    actuar_sync_screenshot_on_failure: bool = True
    actuar_sync_timeout_seconds: int = 60
    actuar_sync_required_for_training: bool = True
    actuar_sync_evidence_dir: str = "data/actuar-sync-evidence"
    actuar_ignore_https_errors: bool = False
    actuar_bridge_poll_seconds: int = 15
    actuar_bridge_device_stale_seconds: int = 90
    actuar_bridge_pairing_code_ttl_minutes: int = 10

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: DEFAULT_CORS_ORIGINS.copy())
    frontend_url: str = "http://localhost:5173"
    public_diag_gym_id: str = ""
    admin_gym_id: str = ""
    public_booking_url: str = "https://cal.com/aigymos"
    public_diag_rate_limit: str = "5/hour"
    public_booking_rate_limit: str = "10/hour"
    public_whatsapp_webhook_rate_limit: str = "30/minute"
    public_objection_response_rate_limit: str = "5/hour"
    public_proposal_rate_limit: str = "5/hour"
    public_diagnosis_enabled: bool = False
    public_booking_confirm_enabled: bool = False
    public_booking_confirm_token: str = ""
    public_objection_response_enabled: bool = False
    public_proposal_enabled: bool = False
    public_proposal_email_enabled: bool = False
    monthly_reports_dispatch_enabled: bool = False
    booking_reminder_minutes_before: int = 60
    proposal_followup_delay_hours: int = 24

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return DEFAULT_CORS_ORIGINS.copy()
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if str(origin).strip()]
                except json.JSONDecodeError:
                    trimmed = raw.removeprefix("[").removesuffix("]").strip()
                    if trimmed:
                        return [
                            origin.strip().strip("'\"")
                            for origin in trimmed.split(",")
                            if origin.strip().strip("'\"")
                        ]
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return DEFAULT_CORS_ORIGINS.copy()

    @field_validator(
        "debug",
        "enable_scheduler",
        "enable_scheduler_in_api",
        "scheduler_critical_lock_fail_open",
        "actuar_enabled",
        "actuar_sync_enabled",
        "actuar_browser_headless",
        "body_composition_image_ai_enabled",
        "actuar_sync_screenshot_on_success",
        "actuar_sync_screenshot_on_failure",
        "actuar_sync_required_for_training",
        "actuar_ignore_https_errors",
        "public_diagnosis_enabled",
        "public_booking_confirm_enabled",
        "public_objection_response_enabled",
        "public_proposal_enabled",
        "public_proposal_email_enabled",
        "monthly_reports_dispatch_enabled",
        "whatsapp_allow_global_fallback",
        mode="before",
    )
    @classmethod
    def parse_bool_flags(cls, value: bool | str | int | None) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "t", "yes", "y", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "f", "no", "n", "off", "release", "prod", "production"}:
                return False
        return False

    @field_validator("refresh_cookie_samesite", mode="before")
    @classmethod
    def normalize_refresh_cookie_samesite(cls, value: str | None) -> str:
        normalized = (value or "lax").strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            return "lax"
        return normalized

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment.lower() != "production":
            return self

        if _unsafe_secret(self.jwt_secret_key, {"change-me", "change-this-super-secret"}):
            raise ValueError("JWT_SECRET_KEY insegura para ambiente de producao")
        if _unsafe_secret(self.cpf_encryption_key, {"change-me-with-64-hex", "change-me"}):
            raise ValueError("CPF_ENCRYPTION_KEY insegura para ambiente de producao")
        if _is_local_url(self.frontend_url):
            raise ValueError("FRONTEND_URL nao pode apontar para localhost em producao")
        if any(_is_local_url(origin) for origin in self.cors_origins):
            raise ValueError("CORS_ORIGINS nao pode usar localhost em producao")
        if self.enable_scheduler_in_api:
            raise ValueError("ENABLE_SCHEDULER_IN_API deve permanecer false em producao; use worker dedicado")
        if self.enable_scheduler and not self.redis_url.strip():
            raise ValueError("REDIS_URL obrigatorio quando ENABLE_SCHEDULER=true em producao")
        if self.scheduler_critical_lock_fail_open:
            raise ValueError("scheduler_critical_lock_fail_open deve permanecer false em producao")
        if self.public_booking_confirm_enabled and not self.public_booking_confirm_token.strip():
            raise ValueError("PUBLIC_BOOKING_CONFIRM_TOKEN obrigatorio quando booking publico estiver habilitado")
        if self.public_diagnosis_enabled and not self.public_diag_gym_id.strip():
            raise ValueError("PUBLIC_DIAG_GYM_ID obrigatorio quando diagnostico publico estiver habilitado")
        if self.public_proposal_email_enabled:
            if not self.sendgrid_api_key.strip():
                raise ValueError("SENDGRID_API_KEY obrigatoria quando proposal email publico estiver habilitado")
            if self.sendgrid_sender.endswith(".local"):
                raise ValueError("SENDGRID_SENDER invalido para producao")
        if bool(self.whatsapp_api_url.strip()) != bool(self.whatsapp_api_token.strip()):
            raise ValueError("WHATSAPP_API_URL e WHATSAPP_API_TOKEN devem ser configurados juntos em producao")
        return self

    @property
    def resolved_refresh_cookie_secure(self) -> bool:
        if self.environment.lower() == "production":
            return True
        return self.refresh_cookie_secure

    @property
    def resolved_refresh_cookie_samesite(self) -> str:
        if self.environment.lower() == "production":
            return "none"
        return self.refresh_cookie_samesite


def _unsafe_secret(value: str, blocked_values: set[str]) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return True
    if normalized in blocked_values:
        return True
    return len(normalized) < 32


def _is_local_url(value: str) -> bool:
    normalized = (value or "").strip().lower()
    return normalized.startswith("http://localhost") or normalized.startswith("http://127.0.0.1")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
