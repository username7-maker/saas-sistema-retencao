from unittest.mock import MagicMock, patch

from app.services.ai_prompt_registry_service import AiInvocationContext, generate_specialist_text
from app.services.operational_message_ai_service import _build_user_prompt, generate_operational_message_draft


def test_communication_prompt_never_calls_provider_without_explicit_user_action(monkeypatch):
    monkeypatch.setattr("app.services.ai_prompt_registry_service.settings.openai_api_key", "secret")
    with patch("app.services.ai_prompt_registry_service.OpenAI") as client:
        result = generate_specialist_text(
            "retention_copy_agent_v1",
            user_prompt="melhore",
            fallback_text="Mensagem pronta",
        )
    assert result.text == "Mensagem pronta"
    assert result.metadata["ai_skipped_reason"] == "explicit_user_action_required"
    client.assert_not_called()


def test_operational_message_defaults_to_template_without_ai(monkeypatch):
    monkeypatch.setattr("app.services.ai_prompt_registry_service.settings.openai_api_key", "secret")
    with patch("app.services.ai_prompt_registry_service.OpenAI") as client:
        draft = generate_operational_message_draft(None, domain="retention", base_message="Oi, aluno")
    assert draft.message == "Oi, aluno"
    assert draft.message_source == "template_safe"
    client.assert_not_called()


def test_explicit_composer_action_can_call_provider(monkeypatch):
    monkeypatch.setattr("app.services.ai_prompt_registry_service.settings.openai_api_key", "secret")
    response = MagicMock(output_text="Mensagem melhorada", usage=MagicMock(input_tokens=12, output_tokens=4))
    context = AiInvocationContext(True, "gym", "user", "retomar rotina", "task", "source", "idem-key")
    with patch("app.services.ai_prompt_registry_service.OpenAI") as client:
        client.return_value.responses.create.return_value = response
        result = generate_specialist_text(
            "retention_copy_agent_v1",
            user_prompt="melhore",
            fallback_text="Mensagem pronta",
            invocation_context=context,
        )
    assert result.text == "Mensagem melhorada"
    assert result.metadata["input_tokens"] == 12
    client.return_value.responses.create.assert_called_once()


def test_communication_prompt_redacts_contact_and_document_identifiers():
    prompt = _build_user_prompt(
        domain="retention",
        base_message="Fale no (11) 99999-1234 ou teste@example.com. CPF 123.456.789-01.",
        member=None,
        lead=None,
        task=None,
        context={"note": "Contato alternativo 11988887777"},
    )

    assert "teste@example.com" not in prompt
    assert "123.456.789-01" not in prompt
    assert "99999-1234" not in prompt
    assert "11988887777" not in prompt
    assert "[email removido]" in prompt
    assert "[documento removido]" in prompt
    assert "[telefone removido]" in prompt
