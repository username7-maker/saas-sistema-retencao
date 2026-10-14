from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.integrations.actuar.browser_client import ActuarBrowserClient
from app.services.actuar_member_link_service import resolve_actuar_member
from app.services.body_composition_actuar_mapping_service import build_actuar_field_mapping


def test_registered_height_is_used_without_bmi():
    evaluation = SimpleNamespace(
        id=uuid4(),
        evaluation_date=date(2026, 10, 1),
        weight_kg=65.1,
        height_cm=158,
        bmi=None,
        body_fat_percent=32.4,
        muscle_mass_kg=23.4,
    )
    mapping = build_actuar_field_mapping(SimpleNamespace(id=uuid4()), evaluation)
    assert mapping["payload"]["height_cm"] == 158
    assert mapping["missing_critical_fields"] == []
    assert (
        next(f for f in mapping["critical_fields"] if f["field"] == "height_cm")["classification"] == "critical_direct"
    )


def test_registered_height_has_priority_over_rounded_bmi():
    evaluation = SimpleNamespace(
        id=uuid4(),
        evaluation_date=date(2026, 10, 1),
        weight_kg=65.1,
        height_cm=158,
        bmi=23.1,
        body_fat_percent=32.4,
        muscle_mass_kg=23.4,
    )
    assert build_actuar_field_mapping(SimpleNamespace(id=uuid4()), evaluation)["payload"]["height_cm"] == 158


def test_imported_code_is_looked_up_with_independent_identity_evidence():
    member = SimpleNamespace(
        id=uuid4(),
        full_name="Bruno Almeida",
        email="bruno@example.com",
        birthdate=None,
        cpf_encrypted=None,
        extra_data={"external_id": "9002"},
    )
    provider = MagicMock()
    provider.find_member.return_value = {
        "status": "matched",
        "actuar_external_id": "9002",
        "member_context": {"person_id": str(uuid4())},
    }
    with (
        patch("app.services.actuar_member_link_service.get_actuar_member_link", return_value=None),
        patch("app.services.actuar_member_link_service.upsert_actuar_member_link"),
    ):
        resolution = resolve_actuar_member(MagicMock(), gym_id=uuid4(), member=member, provider=provider)
    assert resolution.status == "matched"
    lookup = provider.find_member.call_args.args[0]
    assert lookup["external_id"] == "9002"
    assert lookup["require_identity_confirmation"] is True
    assert lookup["email"] == member.email


@pytest.mark.parametrize(
    "candidate,lookup",
    [
        ({"name": "outra pessoa", "external_id": "9999"}, {"full_name": "Bruno Almeida", "external_id": "9002"}),
        (
            {"name": "bruno almeida", "email": "other@example.com"},
            {"full_name": "Bruno Almeida", "email": "bruno@example.com"},
        ),
        ({"name": "bruno almeida", "age": 80}, {"full_name": "Bruno Almeida", "birthdate": "2000-01-01"}),
        ({"name": "bruno almeida"}, {"full_name": "Bruno Almeida", "birthdate": "2000-01-01"}),
        (
            {"external_id": "9002"},
            {"external_id": "9002", "full_name": "Bruno Almeida", "require_identity_confirmation": True},
        ),
        ({"text": "12345678900", "document": "99945678900"}, {"document": "12345678900"}),
    ],
)
def test_single_candidate_does_not_bypass_identity_checks(candidate, lookup):
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    assert client._select_member_candidate([{"person_id": "p1", **candidate}], lookup) is None


def test_imported_code_and_matching_name_are_accepted_without_birthdate():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    candidate = {"person_id": "p1", "external_id": "9002", "name": "bruno almeida"}
    assert (
        client._select_member_candidate(
            [candidate],
            {
                "external_id": "9002",
                "full_name": "Bruno Almeida",
                "require_identity_confirmation": True,
            },
        )
        == candidate
    )


def test_same_name_without_other_evidence_is_not_accepted():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    assert (
        client._select_member_candidate([{"person_id": "p1", "name": "bruno almeida"}], {"full_name": "Bruno Almeida"})
        is None
    )


def test_same_age_with_different_birthdate_is_not_accepted():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    candidate = {"person_id": "p1", "name": "bruno almeida", "birthdate": "1990-01-02"}
    assert (
        client._select_member_candidate(
            [candidate],
            {
                "full_name": "Bruno Almeida",
                "birthdate": "1990-01-01",
            },
        )
        is None
    )


def test_duplicate_identity_evidence_stays_ambiguous():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    candidates = [{"person_id": "p1", "document": "12345678900"}, {"person_id": "p2", "document": "12345678900"}]
    assert client._select_member_candidate(candidates, {"document": "12345678900"}) is None


def test_name_and_matching_email_can_identify_without_birthdate():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    candidate = {"person_id": "p1", "name": "bruno almeida", "email": "bruno@example.com"}
    assert (
        client._select_member_candidate(
            [candidate],
            {
                "full_name": "Bruno Almeida",
                "email": "bruno@example.com",
            },
        )
        == candidate
    )
