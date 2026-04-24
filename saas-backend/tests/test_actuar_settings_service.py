from unittest.mock import MagicMock

from types import SimpleNamespace
from unittest.mock import patch

from app.services.actuar_settings_service import (
    has_actuar_credentials,
    resolve_effective_actuar_sync_mode,
    serialize_actuar_settings,
    test_actuar_connection as run_actuar_connection_test,
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


def test_serialize_actuar_settings_reports_local_bridge_counts():
    gym = _gym()
    bridge_devices = [
        SimpleNamespace(
            id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            gym_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            device_name="Notebook",
            status="online",
            bridge_version="0.1.0",
            browser_name="Chrome",
            paired_at=None,
            last_seen_at=None,
            last_job_claimed_at=None,
            last_job_completed_at=None,
            last_error_code=None,
            last_error_message=None,
            revoked_at=None,
            created_at="2026-03-30T00:00:00Z",
            updated_at="2026-03-30T00:00:00Z",
        )
    ]
    with patch("app.services.actuar_settings_service.settings.actuar_enabled", True), patch(
        "app.services.actuar_settings_service.settings.actuar_sync_enabled",
        True,
    ), patch(
        "app.services.actuar_settings_service.settings.actuar_sync_mode",
        "local_bridge",
    ):
        payload = serialize_actuar_settings(gym, bridge_devices=bridge_devices)

    assert payload.effective_sync_mode == "local_bridge"
    assert payload.automatic_sync_ready is True
    assert payload.bridge_device_count == 1
    assert payload.bridge_online_device_count == 1


def test_test_actuar_connection_uses_assisted_rpa_provider():
    db = MagicMock()
    gym = _gym(
        id="gym-1",
        actuar_base_url="https://actuar.example",
        actuar_username="owner",
        actuar_password_encrypted="segredo",
    )
    provider = MagicMock()
    provider.test_connection.return_value = {
        "provider": "actuar_assisted_rpa",
        "supported": True,
        "mode": "assisted_rpa",
    }

    with patch("app.services.actuar_settings_service._get_gym_or_404", return_value=gym), patch(
        "app.services.actuar_settings_service.settings.actuar_enabled",
        True,
    ), patch(
        "app.services.actuar_settings_service.settings.actuar_sync_enabled",
        True,
    ), patch(
        "app.services.actuar_settings_service.settings.actuar_sync_mode",
        "assisted_rpa",
    ), patch(
        "app.services.actuar_settings_service.ActuarAssistedRpaProvider",
        return_value=provider,
    ):
        result = run_actuar_connection_test(db, gym_id=gym.id)

    assert result.success is True
    assert result.provider == "actuar_assisted_rpa"
    assert result.automatic_sync_ready is True
    provider.test_connection.assert_called_once()
    provider.close.assert_called_once()
