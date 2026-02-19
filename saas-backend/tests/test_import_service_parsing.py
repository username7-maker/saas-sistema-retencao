from datetime import timezone

from app.models import CheckinSource, MemberStatus
from app.services import import_service


def test_detect_delimiter_semicolon() -> None:
    csv_content = "nome;email\nJoao;joao@example.com\n".encode("utf-8")
    rows = list(import_service._iter_rows(csv_content))
    assert len(rows) == 1
    _, row = rows[0]
    assert row["nome"] == "Joao"
    assert row["email"] == "joao@example.com"


def test_parse_decimal_with_comma() -> None:
    value = import_service._parse_decimal("1.234,56")
    assert str(value) == "1234.56"


def test_parse_datetime_accepts_br_format() -> None:
    dt = import_service._parse_datetime("18/02/2026 19:45")
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 19
    assert dt.minute == 45


def test_parse_member_status_aliases() -> None:
    assert import_service._parse_member_status("ativo") == MemberStatus.ACTIVE
    assert import_service._parse_member_status("pausado") == MemberStatus.PAUSED
    assert import_service._parse_member_status("cancelado") == MemberStatus.CANCELLED


def test_parse_checkin_source_aliases() -> None:
    assert import_service._parse_checkin_source("catraca") == CheckinSource.TURNSTILE
    assert import_service._parse_checkin_source("manual") == CheckinSource.MANUAL
    assert import_service._parse_checkin_source("qualquer_valor") == CheckinSource.IMPORT
