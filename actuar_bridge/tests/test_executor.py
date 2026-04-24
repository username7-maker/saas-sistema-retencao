from __future__ import annotations

from actuar_bridge.executor import (
    ACTUAR_SELECTORS,
    MemberCardCandidate,
    _build_member_name_queries,
    _coerce_candidate_age,
    _dedupe_member_candidates,
    _extract_assessment_id_from_url,
    _format_field_value,
    _looks_like_actuar_person_id,
    _member_lookup_terms,
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


def test_select_member_candidate_uses_linked_external_id_when_results_are_ambiguous():
    candidates = [
        MemberCardCandidate(
            person_id="other",
            name="diego rafagnin de oliverira",
            email="other@example.com",
            age=None,
            text="Diego Rafagnin De Oliverira 1001",
        ),
        MemberCardCandidate(
            person_id="expected",
            name="diego rafagnin de oliverira",
            email="rafagnindiego5@gmail.com",
            age=None,
            text="Diego Rafagnin De Oliverira 3867",
        ),
    ]

    selected = _select_member_candidate(
        candidates,
        {
            "actuar_external_id": "3867",
            "member_name": "Diego Rafagnin De Oliverira",
        },
    )

    assert selected is not None
    assert selected.person_id == "expected"


def test_select_member_candidate_uses_actuar_search_document_with_formatted_text():
    candidates = [
        MemberCardCandidate(
            person_id="other",
            name="diego rafagnin de oliverira",
            email=None,
            age=21,
            text="Diego Rafagnin De Oliverira CPF 111.222.333-44",
        ),
        MemberCardCandidate(
            person_id="expected",
            name="diego rafagnin de oliverira",
            email=None,
            age=21,
            text="Diego Rafagnin De Oliverira CPF 044.320.520-58",
        ),
    ]

    selected = _select_member_candidate(
        candidates,
        {
            "actuar_search_name": "Diego Rafagnin De Oliverira",
            "actuar_search_document": "04432052058",
            "actuar_search_birthdate": "2004-04-27",
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


def test_actuar_selectors_cover_current_body_composition_field_names():
    assert 'select[name="ProtocoloComposicaoCorporalId"]' in ACTUAR_SELECTORS["protocol_select"]
    assert 'input[name="MassaTotalAtual"]' in ACTUAR_SELECTORS["weight_input"]
    assert 'input[name="Estatura"]' in ACTUAR_SELECTORS["height_input"]
    assert 'input[name="PercentualGorduraAtual"]' in ACTUAR_SELECTORS["body_fat_percent_input"]
    assert 'input[name="MassaMuscularAtual"]' in ACTUAR_SELECTORS["muscle_mass_input"]


def test_looks_like_actuar_person_id_only_accepts_uuid_shape():
    assert _looks_like_actuar_person_id("1bd7e299-dd6e-4ae2-826c-e86c75993f97") is True
    assert _looks_like_actuar_person_id("3867") is False


def test_member_lookup_terms_prioritize_external_id_but_keep_route_lookup_separate():
    terms = _member_lookup_terms(
        {
            "actuar_external_id": "3867",
            "actuar_search_document": "044.320.520-58",
            "actuar_search_name": "Diego Rafagnin De Oliverira",
            "member_document": "044.320.520-58",
            "member_email": "rafagnindiego5@gmail.com",
            "member_name": "Diego Rafagnin De Oliverira",
        }
    )

    assert terms == [
        ("linked_external_id", "3867"),
        ("actuar_search_document", "04432052058"),
        ("member_email", "rafagnindiego5@gmail.com"),
        ("actuar_search_name", "Diego Rafagnin De Oliverira"),
    ]


def test_build_member_name_queries_adds_progressive_fallbacks():
    queries = _build_member_name_queries("Diego Rafagnin De Oliverira")

    assert queries == [
        "Diego Rafagnin De Oliverira",
        "Diego Oliverira",
        "Diego Rafagnin",
        "Diego",
    ]


def test_dedupe_member_candidates_keeps_first_match_per_person_id():
    candidates = [
        MemberCardCandidate(person_id="same", name="diego", email="a@example.com", age=20, text="diego"),
        MemberCardCandidate(person_id="same", name="diego", email="b@example.com", age=21, text="diego 2"),
        MemberCardCandidate(person_id="other", name="diego", email="c@example.com", age=22, text="diego 3"),
    ]

    deduped = _dedupe_member_candidates(candidates)

    assert deduped == [candidates[0], candidates[2]]


def test_coerce_candidate_age_accepts_birthdate_payloads():
    assert _coerce_candidate_age("2004-04-27T00:00:00") == 21
