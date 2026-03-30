import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.whatsapp_service import (
    _format_phone,
    WHATSAPP_TEMPLATES,
    get_gym_instance,
    render_template,
    resolve_instance,
    send_whatsapp_document_sync,
    send_whatsapp_sync,
)


def test_format_phone_adds_country_code():
    assert _format_phone("11999999999") == "5511999999999"


def test_format_phone_keeps_existing_country_code():
    assert _format_phone("5511999999999") == "5511999999999"


def test_format_phone_strips_non_digits():
    assert _format_phone("+55 (11) 99999-9999") == "5511999999999"


def test_render_template_reengagement_3d():
    result = render_template("reengagement_3d", {"nome": "Joao", "dias": "3"})
    assert "Joao" in result
    assert "3 dias" in result


def test_render_template_risk_red():
    result = render_template("risk_red", {"nome": "Maria", "plano": "Plano Gold"})
    assert "Maria" in result
    assert "Plano Gold" in result


def test_render_template_birthday():
    result = render_template("birthday", {"nome": "Carlos"})
    assert "Carlos" in result
    assert "aniversario" in result.lower()


def test_render_template_custom():
    result = render_template("custom", {"mensagem": "Mensagem personalizada"})
    assert result == "Mensagem personalizada"


def test_render_template_unknown_falls_back_to_custom():
    result = render_template("nonexistent_template", {"mensagem": "Fallback"})
    assert result == "Fallback"


def test_render_template_handles_missing_vars():
    result = render_template("reengagement_3d", {"nome": "Joao"})
    assert isinstance(result, str)


def test_all_templates_have_content():
    for name, template in WHATSAPP_TEMPLATES.items():
        assert len(template) > 0, f"Template '{name}' is empty"
        assert isinstance(template, str), f"Template '{name}' is not a string"


def test_resolve_instance_explicit_wins(monkeypatch):
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_allow_global_fallback", False)
    assert resolve_instance("gym_abc123") == "gym_abc123"


def test_resolve_instance_none_fallback_disabled(monkeypatch):
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_allow_global_fallback", False)
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_instance", "default")
    assert resolve_instance(None) is None


def test_resolve_instance_none_fallback_enabled(monkeypatch):
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_allow_global_fallback", True)
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_instance", "global_default")
    assert resolve_instance(None) == "global_default"


def test_get_gym_instance_connected():
    db = MagicMock()
    db.get.return_value = SimpleNamespace(whatsapp_instance="gym_abc", whatsapp_status="connected")
    assert get_gym_instance(db, uuid.uuid4()) == "gym_abc"


def test_get_gym_instance_disconnected():
    db = MagicMock()
    db.get.return_value = SimpleNamespace(whatsapp_instance="gym_abc", whatsapp_status="disconnected")
    assert get_gym_instance(db, uuid.uuid4()) is None


def test_get_gym_instance_connecting():
    db = MagicMock()
    db.get.return_value = SimpleNamespace(whatsapp_instance="gym_abc", whatsapp_status="connecting")
    assert get_gym_instance(db, uuid.uuid4()) is None


def test_get_gym_instance_no_instance():
    db = MagicMock()
    db.get.return_value = SimpleNamespace(whatsapp_instance=None, whatsapp_status="disconnected")
    assert get_gym_instance(db, uuid.uuid4()) is None


def test_get_gym_instance_gym_not_found():
    db = MagicMock()
    db.get.return_value = None
    assert get_gym_instance(db, uuid.uuid4()) is None


def _mock_db_send():
    db = MagicMock()
    db.scalar.return_value = 0
    return db


def test_send_skips_without_instance(monkeypatch):
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_allow_global_fallback", False)
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_api_url", "http://evo.test")
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_api_token", "tok")
    log = send_whatsapp_sync(_mock_db_send(), phone="11999999999", message="Oi", instance=None)
    assert log.status == "skipped"
    assert log.extra_data["instance_source"] == "none"


def test_send_uses_gym_instance_in_url(monkeypatch):
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_api_url", "http://evo.test")
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_api_token", "tok")
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_rate_limit_per_hour", 100)
    with patch("httpx.Client") as mock_client:
        response = MagicMock(status_code=200)
        response.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.post.return_value = response
        log = send_whatsapp_sync(_mock_db_send(), phone="11999999999", message="Oi", instance="gym_abc123")
    url = mock_client.return_value.__enter__.return_value.post.call_args[0][0]
    assert "gym_abc123" in url
    assert log.extra_data["instance_used"] == "gym_abc123"
    assert log.extra_data["instance_source"] == "gym"


def test_send_global_fallback_logged(monkeypatch):
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_allow_global_fallback", True)
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_instance", "global_default")
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_api_url", "http://evo.test")
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_api_token", "tok")
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_rate_limit_per_hour", 100)
    with patch("httpx.Client") as mock_client:
        response = MagicMock(status_code=200)
        response.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.post.return_value = response
        log = send_whatsapp_sync(_mock_db_send(), phone="11999999999", message="Oi", instance=None)
    assert log.extra_data["instance_source"] == "global_fallback"


def test_send_document_uses_send_media_endpoint(monkeypatch):
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_api_url", "http://evo.test")
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_api_token", "tok")
    monkeypatch.setattr("app.services.whatsapp_service.settings.whatsapp_rate_limit_per_hour", 100)
    with patch("httpx.Client") as mock_client:
        response = MagicMock(status_code=201)
        response.raise_for_status = MagicMock()
        mock_client.return_value.__enter__.return_value.post.return_value = response
        log = send_whatsapp_document_sync(
            _mock_db_send(),
            phone="11999999999",
            caption="Resumo da bioimpedancia",
            file_bytes=b"%PDF-1.4 fake",
            filename="bioimpedancia.pdf",
            instance="gym_abc123",
        )

    call = mock_client.return_value.__enter__.return_value.post.call_args
    assert "/message/sendMedia/gym_abc123" in call[0][0]
    assert call.kwargs["json"]["mediatype"] == "document"
    assert call.kwargs["json"]["fileName"] == "bioimpedancia.pdf"
    assert log.status == "sent"
    assert log.extra_data["delivery_kind"] == "document"
