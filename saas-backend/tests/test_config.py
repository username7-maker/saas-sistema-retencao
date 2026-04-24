from app.core.config import Settings
import pytest
from pydantic import ValidationError


VALID_JWT_SECRET = "x" * 32
VALID_ENCRYPTION_KEY = "0" * 64


def test_parse_cors_origins_accepts_json_list():
    raw = '["https://app.aigymos.com","https://admin.aigymos.com"]'
    parsed = Settings.parse_cors_origins(raw)  # type: ignore[arg-type]
    assert parsed == ["https://app.aigymos.com", "https://admin.aigymos.com"]


def test_parse_cors_origins_accepts_csv():
    raw = "https://app.aigymos.com, https://admin.aigymos.com"
    parsed = Settings.parse_cors_origins(raw)  # type: ignore[arg-type]
    assert parsed == ["https://app.aigymos.com", "https://admin.aigymos.com"]


def test_api_docs_enabled_by_default_outside_production():
    settings = Settings(environment="development")
    assert settings.api_docs_enabled is True


def test_api_docs_disabled_by_default_in_production():
    settings = Settings(
        environment="production",
        jwt_secret_key=VALID_JWT_SECRET,
        cpf_encryption_key=VALID_ENCRYPTION_KEY,
    )
    assert settings.api_docs_enabled is False


def test_api_docs_can_be_explicitly_enabled_for_controlled_environments():
    settings = Settings(
        environment="production",
        enable_api_docs=True,
        jwt_secret_key=VALID_JWT_SECRET,
        cpf_encryption_key=VALID_ENCRYPTION_KEY,
    )
    assert settings.api_docs_enabled is True


def test_production_rejects_cors_wildcard():
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret_key=VALID_JWT_SECRET,
            cpf_encryption_key=VALID_ENCRYPTION_KEY,
            cors_origins=["*"],
        )


def test_production_rejects_non_key_encryption_secret():
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret_key=VALID_JWT_SECRET,
            cpf_encryption_key="this-is-long-but-not-a-real-aes-key",
        )
