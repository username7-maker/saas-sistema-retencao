import json
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    app_name: str = "AI GYM OS"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = True
    enable_scheduler: bool = True

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/aigymos"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    bcrypt_rounds: int = 12

    cpf_encryption_key: str = "change-me-with-64-hex"

    sendgrid_api_key: str = ""
    sendgrid_sender: str = "noreply@aigymos.local"

    claude_api_key: str = ""
    claude_model: str = "claude-3-5-haiku-latest"
    claude_max_tokens: int = 250

    whatsapp_api_url: str = ""
    whatsapp_api_token: str = ""
    whatsapp_instance: str = "default"
    whatsapp_rate_limit_per_hour: int = 6

    redis_url: str = ""
    dashboard_cache_ttl_seconds: int = 300
    dashboard_cache_maxsize: int = 512

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ["http://localhost:5173"]
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if str(origin).strip()]
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return ["http://localhost:5173"]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment.lower() != "production":
            return self

        if _unsafe_secret(self.jwt_secret_key, {"change-me", "change-this-super-secret"}):
            raise ValueError("JWT_SECRET_KEY insegura para ambiente de producao")
        if _unsafe_secret(self.cpf_encryption_key, {"change-me-with-64-hex", "change-me"}):
            raise ValueError("CPF_ENCRYPTION_KEY insegura para ambiente de producao")
        return self


def _unsafe_secret(value: str, blocked_values: set[str]) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return True
    if normalized in blocked_values:
        return True
    return len(normalized) < 32


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
