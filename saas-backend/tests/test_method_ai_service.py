from app.services.method_ai_service import (
    build_wa_me_link,
    generate_follow_up_message,
    generate_post_sale_message,
    normalize_brazilian_whatsapp_phone,
)


def test_brazilian_phone_normalization_accepts_valid_ddd_numbers() -> None:
    assert normalize_brazilian_whatsapp_phone("(11) 99999-0001") == "5511999990001"
    assert normalize_brazilian_whatsapp_phone("55 21 3333-4444") == "552133334444"


def test_brazilian_phone_normalization_rejects_invalid_or_ambiguous_numbers() -> None:
    assert normalize_brazilian_whatsapp_phone("10 99999-0001") is None
    assert normalize_brazilian_whatsapp_phone("99999-0001") is None
    assert normalize_brazilian_whatsapp_phone("11 89999-0001") is None


def test_wa_me_link_is_only_generated_for_valid_phone_and_encodes_message() -> None:
    link = build_wa_me_link("11 99999-0001", "Oi Maria, tudo bem?")

    assert link == "https://wa.me/5511999990001?text=Oi%20Maria%2C%20tudo%20bem%3F"
    assert build_wa_me_link("99999-0001", "Oi") is None


def test_method_ai_outputs_are_human_review_only() -> None:
    follow_up = generate_follow_up_message({"person_name": "Maria Silva", "event_type": "proposal_no_response"})
    post_sale = generate_post_sale_message({"person_name": "Joao", "event_type": "low_frequency"})

    assert follow_up["requires_human_approval"] is True
    assert follow_up["metadata"]["provider"] == "deterministic_fallback"
    assert post_sale["requires_human_approval"] is True
    assert "Joao" in post_sale["message"]
