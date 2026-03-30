from types import SimpleNamespace
from unittest.mock import patch

from app.services.kommo_settings_service import serialize_kommo_settings


def _gym(**overrides):
    payload = {
        "kommo_enabled": True,
        "kommo_base_url": None,
        "kommo_access_token_encrypted": None,
        "kommo_default_pipeline_id": None,
        "kommo_default_stage_id": None,
        "kommo_default_responsible_user_id": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_serialize_kommo_settings_reports_ready_when_configured():
    gym = _gym(
        kommo_enabled=True,
        kommo_base_url="crm.kommo.example",
        kommo_access_token_encrypted="secret-token",
        kommo_default_pipeline_id="111",
        kommo_default_stage_id="222",
    )

    payload = serialize_kommo_settings(gym)

    assert payload.kommo_enabled is True
    assert payload.kommo_base_url == "https://crm.kommo.example"
    assert payload.kommo_has_access_token is True
    assert payload.automatic_handoff_ready is True
    assert payload.kommo_default_pipeline_id == "111"
    assert payload.kommo_default_stage_id == "222"


def test_serialize_kommo_settings_reports_not_ready_without_token():
    gym = _gym(kommo_enabled=True, kommo_base_url="https://crm.kommo.example", kommo_access_token_encrypted=None)

    payload = serialize_kommo_settings(gym)

    assert payload.kommo_has_access_token is False
    assert payload.automatic_handoff_ready is False
