from types import SimpleNamespace
from unittest.mock import patch

from app.services.actuar_settings_service import (
    has_actuar_credentials,
    resolve_effective_actuar_sync_mode,
    serialize_actuar_settings,
)


def _gym(**overrides):
    payload = {
        "actuar_enabled": True,
        "actuar_auto_sync_body_composition": True,
        "actuar_base_url": None,
        "actuar_username": None,
        "actuar_password_encrypted": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_has_actuar_credentials_requires_all_parts():
    assert has_actuar_credentials(_gym()) is False
    assert has_actuar_credentials(_gym(actuar_base_url="https://actuar.example")) is False
    assert has_actuar_credentials(_gym(actuar_base_url="https://actuar.example", actuar_username="owner")) is False
    assert (
        has_actuar_credentials(
            _gym(
                actuar_base_url="https://actuar.example",
                actuar_username="owner",
                actuar_password_encrypted="segredo",
            )
        )
        is True
    )


def test_resolve_effective_mode_promotes_csv_export_when_credentials_exist():
    gym = _gym(
        actuar_base_url="https://actuar.example",
        actuar_username="owner",
        actuar_password_encrypted="segredo",
    )
    with patch("app.services.actuar_settings_service.settings.actuar_sync_enabled", True), patch(
        "app.services.actuar_settings_service.settings.actuar_sync_mode",
        "csv_export",
    ):
        assert resolve_effective_actuar_sync_mode(gym) == "assisted_rpa"


def test_serialize_actuar_settings_reports_automatic_ready():
    gym = _gym(
        actuar_base_url="https://actuar.example",
        actuar_username="owner",
        actuar_password_encrypted="segredo",
    )
    with patch("app.services.actuar_settings_service.settings.actuar_enabled", True), patch(
        "app.services.actuar_settings_service.settings.actuar_sync_enabled",
        True,
    ), patch(
        "app.services.actuar_settings_service.settings.actuar_sync_mode",
        "csv_export",
    ):
        payload = serialize_actuar_settings(gym)

    assert payload.effective_sync_mode == "assisted_rpa"
    assert payload.automatic_sync_ready is True
    assert payload.actuar_has_password is True
