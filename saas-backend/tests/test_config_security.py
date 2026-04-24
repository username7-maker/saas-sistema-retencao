import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _production_kwargs(**overrides):
    base = {
        "environment": "production",
        "jwt_secret_key": "x" * 32,
        "cpf_encryption_key": "a" * 64,
        "frontend_url": "https://pilot.aigymos.app",
        "cors_origins": ["https://pilot.aigymos.app"],
        "enable_scheduler": False,
        "enable_scheduler_in_api": False,
        "scheduler_critical_lock_fail_open": False,
        "redis_url": "redis://redis:6379/0",
        "sendgrid_sender": "noreply@aigymos.com",
        "whatsapp_api_url": "",
        "whatsapp_api_token": "",
    }
    base.update(overrides)
    return base


def test_production_rejects_local_frontend_url():
    with pytest.raises(ValidationError):
        Settings(**_production_kwargs(frontend_url="http://localhost:5173"))


def test_production_rejects_local_cors_origin():
    with pytest.raises(ValidationError):
        Settings(**_production_kwargs(cors_origins=["http://127.0.0.1:5173"]))


def test_production_rejects_wildcard_cors_origin():
    with pytest.raises(ValidationError):
        Settings(**_production_kwargs(cors_origins=["*"]))


def test_production_requires_frontend_url_to_be_present_in_cors_origins():
    with pytest.raises(ValidationError):
        Settings(
            **_production_kwargs(
                frontend_url="https://pilot.aigymos.app",
                cors_origins=["https://admin.aigymos.app"],
            )
        )


def test_production_rejects_scheduler_in_api():
    with pytest.raises(ValidationError):
        Settings(**_production_kwargs(enable_scheduler=True, enable_scheduler_in_api=True))


def test_production_requires_redis_for_scheduler():
    with pytest.raises(ValidationError):
        Settings(**_production_kwargs(enable_scheduler=True, redis_url=""))


def test_production_rejects_fail_open_scheduler():
    with pytest.raises(ValidationError):
        Settings(**_production_kwargs(scheduler_critical_lock_fail_open=True))


def test_production_requires_booking_confirm_token_when_enabled():
    with pytest.raises(ValidationError):
        Settings(**_production_kwargs(public_booking_confirm_enabled=True, public_booking_confirm_token=""))


def test_production_requires_public_diag_gym_for_public_diagnosis():
    with pytest.raises(ValidationError):
        Settings(**_production_kwargs(public_diagnosis_enabled=True, public_diag_gym_id=""))


def test_production_requires_sendgrid_when_public_proposal_email_enabled():
    with pytest.raises(ValidationError):
        Settings(**_production_kwargs(public_proposal_email_enabled=True, sendgrid_api_key=""))


def test_production_rejects_partial_whatsapp_config():
    with pytest.raises(ValidationError):
        Settings(**_production_kwargs(whatsapp_api_url="https://evolution.example.com", whatsapp_api_token=""))


def test_production_accepts_hardened_scheduler_worker_configuration():
    settings = Settings(**_production_kwargs(enable_scheduler=True))

    assert settings.enable_scheduler is True
    assert settings.enable_scheduler_in_api is False
    assert settings.redis_url == "redis://redis:6379/0"


def test_frontend_url_and_cors_origins_are_normalized_to_origin():
    settings = Settings(
        frontend_url="https://pilot.aigymos.app/dashboard",
        cors_origins=["https://pilot.aigymos.app/"],
    )

    assert settings.frontend_url == "https://pilot.aigymos.app"
    assert settings.cors_origins == ["https://pilot.aigymos.app"]
