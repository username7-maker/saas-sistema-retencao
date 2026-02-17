import pytest

from app.services.whatsapp_service import _format_phone, render_template, WHATSAPP_TEMPLATES


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
    # Should not crash - template.format will raise KeyError but we catch it
    # The render_template function has a try/except
    assert isinstance(result, str)


def test_all_templates_have_content():
    for name, template in WHATSAPP_TEMPLATES.items():
        assert len(template) > 0, f"Template '{name}' is empty"
        assert isinstance(template, str), f"Template '{name}' is not a string"
