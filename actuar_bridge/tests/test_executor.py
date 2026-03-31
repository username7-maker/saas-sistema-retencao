from __future__ import annotations

from actuar_bridge.executor import (
    MemberCardCandidate,
    _extract_assessment_id_from_url,
    _format_field_value,
    _select_member_candidate,
)


def test_select_member_candidate_prefers_exact_email_match():
    candidates = [
        MemberCardCandidate(
            person_id="1599b20a-d246-4a3b-bf8a-c38b7d3dc9d4",
            name="erick bedin",
            email="erickbedin9047@gmail.com",
            age=20,
            text="Erick Bedin 20 anos",
        ),
        MemberCardCandidate(
            person_id="da91a17c-9e67-454e-bc2e-b747d1bd753b",
            name="erick bedin",
            email="erickbedin904@gmail.com",
            age=21,
            text="Erick Bedin 21 anos",
        ),
    ]

    selected = _select_member_candidate(
        candidates,
        {
            "member_name": "Erick Bedin",
            "member_email": "erickbedin904@gmail.com",
            "member_birthdate": "2004-04-27",
        },
    )

    assert selected is not None
    assert selected.person_id == "da91a17c-9e67-454e-bc2e-b747d1bd753b"


def test_select_member_candidate_falls_back_to_age_when_email_is_missing():
    candidates = [
        MemberCardCandidate(
            person_id="older",
            name="erick bedin",
            email=None,
            age=20,
            text="Erick Bedin 20 anos",
        ),
        MemberCardCandidate(
            person_id="expected",
            name="erick bedin",
            email=None,
            age=21,
            text="Erick Bedin 21 anos",
        ),
    ]

    selected = _select_member_candidate(
        candidates,
        {
            "member_name": "Erick Bedin",
            "member_birthdate": "2004-04-27",
        },
    )

    assert selected is not None
    assert selected.person_id == "expected"


def test_format_field_value_uses_actuar_number_format():
    assert _format_field_value("weight", 84.5) == "84,50"
    assert _format_field_value("body_fat_percent", 23) == "23,00"
    assert _format_field_value("height_cm", 177.6) == "178"


def test_extract_assessment_id_from_real_edit_route():
    assessment_id = _extract_assessment_id_from_url(
        "https://app.actuar.com/#/avaliacoes/avaliacao/da91a17c-9e67-454e-bc2e-b747d1bd753b/019d44b0-779d-72ef-aa46-0c294cb9c670",
        "da91a17c-9e67-454e-bc2e-b747d1bd753b",
    )

    assert assessment_id == "019d44b0-779d-72ef-aa46-0c294cb9c670"
