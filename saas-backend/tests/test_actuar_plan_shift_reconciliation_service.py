from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.actuar_plan_shift_reconciliation_service import (
    EXPECTED_ACCESS_SHA256,
    EXPECTED_CLIENTS_SHA256,
    MatchDecision,
    MemberChange,
    PreparedCheckin,
    ReconciliationPlan,
    _bridge_access_decision_through_clients,
    _build_member_index,
    _match_row,
    _safe_plan_candidate,
    _shift_for_hour,
    _verify_file,
)
from app.services.preferred_shift_service import derive_preferred_shift_from_counts


def _member(*, external_id: str, email: str, name: str, phone: str = "11999999999", plan: str = "LIVRE MENSAL"):
    return SimpleNamespace(
        id=uuid4(),
        extra_data={"external_id": external_id},
        cpf_encrypted=None,
        email=email,
        full_name=name,
        phone=phone,
        join_date=None,
        plan_name=plan,
    )


def test_only_unique_strong_identifiers_are_high_confidence():
    member = _member(external_id="7027", email="aluna@example.com", name="Aluna Unica")
    index = _build_member_index([member])

    by_code = _match_row({"codigo_acesso": "7027"}, index, expected_plan=None)
    by_email = _match_row({"email": "ALUNA@example.com"}, index, expected_plan=None)

    assert by_code.member_id == member.id
    assert by_code.confidence == "high"
    assert by_code.method == "codigo_acesso"
    assert by_email.member_id == member.id
    assert by_email.confidence == "high"


def test_duplicate_strong_identifier_is_ambiguous_and_never_applied():
    first = _member(external_id="1", email="duplicado@example.com", name="Primeiro")
    second = _member(external_id="2", email="duplicado@example.com", name="Segundo")
    decision = _match_row(
        {"email": "duplicado@example.com"},
        _build_member_index([first, second]),
        expected_plan=None,
    )

    assert decision.member_id is None
    assert decision.confidence == "ambiguous"


def test_unique_name_needs_corroboration_and_still_goes_to_manual_review():
    member = _member(external_id="1", email="one@example.com", name="Nome Unico", phone="11988887777")
    index = _build_member_index([member])

    corroborated = _match_row(
        {"nome": "Nome Unico", "telefone": "(11) 98888-7777"},
        index,
        expected_plan=None,
    )
    name_only = _match_row({"nome": "Nome Unico"}, index, expected_plan=None)

    assert corroborated.member_id == member.id
    assert corroborated.confidence == "review"
    assert "phone" in corroborated.method
    assert name_only.member_id is None
    assert name_only.confidence == "unmatched"


def test_access_can_bridge_unique_cpf_between_exports_to_strong_client_match():
    member_id = uuid4()
    direct = MatchDecision(None, "name", "ambiguous", "Nome duplicado.")

    bridged = _bridge_access_decision_through_clients(
        {"cpf": "070.315.049-96"},
        direct,
        client_members_by_cpf={"07031504996": {member_id}},
    )

    assert bridged.member_id == member_id
    assert bridged.confidence == "high"
    assert bridged.method == "cpf_between_exports+client_strong"


def test_access_bridge_never_overrides_strong_conflict_or_ambiguous_cpf():
    first = uuid4()
    second = uuid4()
    strong_conflict = MatchDecision(None, "cpf", "ambiguous", "CPF duplicado na base.")

    preserved = _bridge_access_decision_through_clients(
        {"cpf": "07031504996"},
        strong_conflict,
        client_members_by_cpf={"07031504996": {first}},
    )
    ambiguous = _bridge_access_decision_through_clients(
        {"cpf": "07031504996"},
        MatchDecision(None, "none", "unmatched", "Sem match."),
        client_members_by_cpf={"07031504996": {first, second}},
    )

    assert preserved is strong_conflict
    assert ambiguous.member_id is None
    assert ambiguous.confidence == "ambiguous"


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"assinatura": "LIVRE", "assinaturas_condicoes": "12 meses"}, ("LIVRE ANUAL", "annual", "conditions")),
        ({"assinatura": "LIVRE", "assinaturas_condicoes": "6 meses"}, ("LIVRE SEMESTRAL", "semiannual", "conditions")),
        ({"assinatura": "LIVRE MENSAL"}, ("LIVRE MENSAL", "monthly", "plan_name")),
    ],
)
def test_plan_reconstruction_preserves_monthly_semiannual_and_annual(row, expected):
    assert _safe_plan_candidate(row) == expected


@pytest.mark.parametrize("row", [{}, {"assinatura": "Plano Base"}, {"assinatura": "LIVRE"}])
def test_empty_or_generic_plan_is_never_a_replacement(row):
    assert _safe_plan_candidate(row) is None


def test_shift_boundaries_ties_and_no_access_do_not_guess():
    assert [_shift_for_hour(hour) for hour in (0, 5, 6, 11, 12, 17, 18, 23)] == [
        "overnight",
        "overnight",
        "morning",
        "morning",
        "afternoon",
        "afternoon",
        "evening",
        "evening",
    ]
    assert derive_preferred_shift_from_counts({"morning": 4, "evening": 2}) == "morning"
    assert derive_preferred_shift_from_counts({"morning": 4, "evening": 4}) is None
    assert derive_preferred_shift_from_counts({}) is None


def test_hash_guard_and_plan_digest_are_fail_closed():
    with pytest.raises(ValueError, match="SHA-256 inesperado"):
        _verify_file(b"arquivo diferente", expected_sha256=EXPECTED_CLIENTS_SHA256, label="clientes")

    gym_id = uuid4()
    member_id = uuid4()
    base = ReconciliationPlan(
        gym_id=gym_id,
        clients_filename="Todos os Clientes.xlsx",
        access_filename="Acessos.xlsx",
        clients_sha256=EXPECTED_CLIENTS_SHA256,
        access_sha256=EXPECTED_ACCESS_SHA256,
        client_rows=1427,
        access_rows=4391,
        reference_at=datetime(2026, 8, 31, 23, 59, tzinfo=UTC),
        changes=[
            MemberChange(
                member_id=member_id,
                plan_before="LIVRE MENSAL",
                plan_after="LIVRE ANUAL",
                shift_before=None,
                shift_after="morning",
                plan_cycle_before="monthly",
                plan_cycle_after="annual",
                plan_cycle_source_before="plan_name",
                plan_cycle_source_after="conditions",
                plan_source="Todos os Clientes.xlsx:conditions",
                shift_source="checkins_30d:dominant",
            )
        ],
        checkins=[
            PreparedCheckin(
                member_id=member_id,
                checkin_at=datetime(2026, 8, 31, 9, 0, tzinfo=UTC),
                hour_bucket=9,
                weekday=0,
            )
        ],
    )
    changed = ReconciliationPlan(**{**base.__dict__, "checkins": []})

    assert base.digest() != changed.digest()
