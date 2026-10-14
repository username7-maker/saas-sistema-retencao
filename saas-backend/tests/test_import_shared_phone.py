from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models import Member, MemberStatus
from app.services import import_service


def member(name, email=None):
    return Member(id=uuid4(), gym_id=uuid4(), full_name=name, email=email,
                  phone="11900000000", status=MemberStatus.ACTIVE,
                  plan_name="Plano original", monthly_fee=0,
                  join_date=date(2026, 1, 1), extra_data={})


@pytest.mark.parametrize("preview", [False, True])
def test_shared_phone_different_person_becomes_pending_without_mutation(preview, monkeypatch):
    angelo = member("Carlos Exemplo")
    db = MagicMock()
    db.scalars.return_value.all.return_value = [angelo]
    monkeypatch.setattr(import_service, "refresh_member_risk_snapshot", lambda *a, **k: {})
    content = b"Cliente,Telefones,Assinaturas\nMaria Helena Exemplo,11900000000,LIVRE ANUAL\n"
    operation = import_service.preview_members_csv if preview else import_service.import_members_csv
    result = operation(db, content, filename="clientes.csv")
    assert len(result.errors) == 1
    assert "telefone" in result.errors[0].reason.lower()
    assert angelo.plan_name == "Plano original"
    assert angelo.full_name == "Carlos Exemplo"
    if preview:
        assert result.would_update == result.would_create == result.valid_rows == 0
    else:
        assert result.updated_existing == result.imported == 0
        db.add.assert_not_called()


def test_shared_phone_never_resolves_an_unrelated_person():
    lookup = import_service._build_member_lookups([member("Carlos Exemplo")])
    assert import_service._resolve_member_from_row(
        {"nome": "Maria Helena Exemplo", "telefone": "11900000000"}, lookup
    ) is None


def test_shared_phone_shared_surnames_do_not_identify_relatives():
    lookup = import_service._build_member_lookups([member("Maria Terezinha Rebelato")])
    assert import_service._resolve_member_from_row(
        {"nome": "Maria Helena Exemplo", "telefone": "11900000000"}, lookup
    ) is None


def test_distinct_cpf_does_not_merge_people_with_shared_phone(monkeypatch):
    angelo = member("Carlos Exemplo")
    angelo.cpf_encrypted = "encrypted-fixture"
    monkeypatch.setattr(import_service, "decrypt_cpf", lambda value: "11111111111")
    lookup = import_service._build_member_lookups([angelo])
    assert import_service._resolve_member_from_row(
        {"nome": "Maria Helena Exemplo", "telefone": "11900000000", "cpf": "22222222222"}, lookup
    ) is None


def test_existing_gema_and_angelo_are_updated_independently_without_strong_identifiers(monkeypatch):
    angelo, gema = member("Carlos Exemplo"), member("Maria Helena Exemplo")
    db = MagicMock()
    db.scalars.return_value.all.return_value = [angelo, gema]
    monkeypatch.setattr(import_service, "refresh_member_risk_snapshot", lambda *a, **k: {})
    result = import_service.import_members_csv(
        db, (b"nome,telefone,assinaturas\n"
             b"Maria Helena Exemplo,11900000000,LIVRE ANUAL\n"
             b"Carlos Exemplo,11900000000,LIVRE MENSAL\n"),
        filename="clientes.csv",
    )
    assert result.updated_existing == 2
    assert result.imported == 0
    assert not result.errors
    assert gema.plan_name == "LIVRE ANUAL"
    assert angelo.plan_name == "LIVRE MENSAL"


def test_shared_phone_selects_the_correct_name_from_multiple_members():
    angelo, gema = member("Carlos Exemplo"), member("Maria Helena Exemplo")
    lookup = import_service._build_member_lookups([angelo, gema])
    assert import_service._resolve_member_from_row(
        {"nome": "Maria Helena Exemplo", "telefone": "11900000000"}, lookup
    ) is gema


def test_distinct_email_allows_independent_member_despite_shared_phone(monkeypatch):
    db = MagicMock()
    db.scalars.return_value.all.return_value = [member("Carlos Exemplo")]
    monkeypatch.setattr(import_service, "refresh_member_risk_snapshot", lambda *a, **k: {})
    result = import_service.import_members_csv(
        db, b"nome,telefone,email\nMaria Helena Exemplo,11900000000,gema@example.com\n",
        filename="clientes.csv",
    )
    assert result.imported == 1
    assert result.updated_existing == 0
    assert not result.errors
