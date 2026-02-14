from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    app_name: str = "AI GYM OS"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = True

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

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
