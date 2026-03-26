from datetime import date, timezone
from io import BytesIO
from collections import Counter
from uuid import uuid4
import zipfile
from xml.sax.saxutils import escape
from unittest.mock import MagicMock
import pytest

from app.models import CheckinSource, Member, MemberStatus
from app.services import import_service


@pytest.fixture(autouse=True)
def _stub_risk_snapshot_refresh(monkeypatch):
    monkeypatch.setattr(
        import_service,
        "refresh_member_risk_snapshot",
        lambda *_args, **_kwargs: {"members_refreshed": 0},
    )


def _build_xlsx_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    def col_name(index: int) -> str:
        letters = ""
        current = index + 1
        while current:
            current, remainder = divmod(current - 1, 26)
            letters = chr(65 + remainder) + letters
        return letters

    shared_strings: list[str] = []
    shared_index: dict[str, int] = {}

    def shared_id(value: object) -> int:
        text = "" if value is None else str(value)
        if text not in shared_index:
            shared_index[text] = len(shared_strings)
            shared_strings.append(text)
        return shared_index[text]

    all_rows = [headers] + rows
    sheet_rows_xml: list[str] = []
    for row_idx, row_values in enumerate(all_rows, start=1):
        cells_xml: list[str] = []
        for col_idx, value in enumerate(row_values):
            cell_ref = f"{col_name(col_idx)}{row_idx}"
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cells_xml.append(f'<c r="{cell_ref}"><v>{value}</v></c>')
            else:
                sst_id = shared_id(value)
                cells_xml.append(f'<c r="{cell_ref}" t="s"><v>{sst_id}</v></c>')
        sheet_rows_xml.append(f'<row r="{row_idx}">{"".join(cells_xml)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows_xml)}</sheetData>'
        "</worksheet>"
    )

    shared_items = "".join(f"<si><t>{escape(text)}</t></si>" for text in shared_strings)
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">{shared_items}</sst>'
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )

    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
        'Target="sharedStrings.xml"/>'
        "</Relationships>"
    )

    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        archive.writestr("xl/sharedStrings.xml", shared_xml)
    return buffer.getvalue()


class _FakeScalars:
    def __init__(self, members: list[Member]) -> None:
        self._members = members

    def all(self) -> list[Member]:
        return list(self._members)


class _FakeMemberImportDB:
    def __init__(self, members: list[Member] | None = None) -> None:
        self.members = list(members or [])
        self.commit_count = 0
        self.flush_count = 0

    def scalars(self, _query) -> _FakeScalars:
        return _FakeScalars(self.members)

    def add(self, obj) -> None:
        if isinstance(obj, Member) and obj not in self.members:
            self.members.append(obj)

    def commit(self) -> None:
        self.commit_count += 1

    def flush(self) -> None:
        self.flush_count += 1


def test_detect_delimiter_semicolon() -> None:
    csv_content = "nome;email\nJoao;joao@example.com\n".encode("utf-8")
    rows = list(import_service._iter_rows(csv_content))
    assert len(rows) == 1
    _, row = rows[0]
    assert row["nome"] == "Joao"
    assert row["email"] == "joao@example.com"


def test_iter_rows_xlsx_normalizes_headers() -> None:
    xlsx_content = _build_xlsx_bytes(
        headers=["Nome", "E-mail", "Plano Nome"],
        rows=[["Ana Silva", "ana@example.com", "Mensal"]],
    )
    rows = list(import_service._iter_rows(xlsx_content, filename="clientes.xlsx"))
    assert len(rows) == 1
    _, row = rows[0]
    assert row["nome"] == "Ana Silva"
    assert row["e_mail"] == "ana@example.com"
    assert row["plano_nome"] == "Mensal"


def test_parse_decimal_with_comma() -> None:
    value = import_service._parse_decimal("1.234,56")
    assert str(value) == "1234.56"


def test_parse_datetime_accepts_br_format() -> None:
    dt = import_service._parse_datetime("18/02/2026 19:45")
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 19
    assert dt.minute == 45


def test_parse_datetime_accepts_excel_serial() -> None:
    dt = import_service._parse_datetime("45269.66221628472")
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.date().isoformat() == "2023-12-09"


def test_parse_date_accepts_excel_serial() -> None:
    parsed = import_service._parse_date("45269")
    assert parsed is not None
    assert parsed.isoformat() == "2023-12-09"


def test_parse_member_status_aliases() -> None:
    assert import_service._parse_member_status("ativo") == MemberStatus.ACTIVE
    assert import_service._parse_member_status("A") == MemberStatus.ACTIVE
    assert import_service._parse_member_status("pausado") == MemberStatus.PAUSED
    assert import_service._parse_member_status("P") == MemberStatus.PAUSED
    assert import_service._parse_member_status("cancelado") == MemberStatus.CANCELLED
    assert import_service._parse_member_status("I") == MemberStatus.CANCELLED


def test_parse_checkin_source_aliases() -> None:
    assert import_service._parse_checkin_source("catraca") == CheckinSource.TURNSTILE
    assert import_service._parse_checkin_source("manual") == CheckinSource.MANUAL
    assert import_service._parse_checkin_source("qualquer_valor") == CheckinSource.IMPORT


def test_checkin_datetime_uses_hora_alias_with_excel_serial() -> None:
    row = {"hora": "46060.99887030093", "data": "46060.99887030093"}
    value = import_service._pick_first(row, import_service.CHECKIN_AT_KEYS)
    assert value == "46060.99887030093"
    parsed = import_service._parse_datetime(value)
    assert parsed is not None
    assert parsed.tzinfo == timezone.utc


def test_normalize_phone_prefers_first_number_candidate() -> None:
    raw = "Celular (54)999723860, Residencial (54)999723860"
    normalized = import_service._normalize_phone(raw)
    assert normalized == "54999723860"


def test_extract_plan_name_ignores_generic_shift_values() -> None:
    row = {
        "assinaturas": "",
        "assinaturas_condicoes": "",
        "assinaturas_horarios": "LIVRE",
    }
    assert import_service._extract_plan_name(row) == "Plano Base"


def test_extract_plan_name_prefers_real_plan_value() -> None:
    row = {
        "assinaturas_horarios": "LIVRE",
        "assinatura": "LIVRE MENSAL",
    }
    assert import_service._extract_plan_name(row) == "LIVRE MENSAL"


def test_extract_plan_metadata_prefers_conditions_for_contract_cycle() -> None:
    row = {
        "assinaturas": "LIVRE MENSAL",
        "assinaturas_condicoes": "PLANO PRO-LIVRE 12 MESES",
    }
    plan_name, plan_cycle, source = import_service._extract_plan_metadata(row)
    assert plan_name == "LIVRE ANUAL"
    assert plan_cycle == "annual"
    assert source == "conditions"


def test_extract_plan_metadata_uses_dates_when_conditions_are_generic() -> None:
    row = {
        "assinaturas": "LIVRE MENSAL",
        "assinaturas_condicoes": "LIVRE - NORMAL",
        "dt_primeira_ativacao": "01/02/2026",
        "dt_prox_renovacao_assinatura": "01/08/2026",
    }
    plan_name, plan_cycle, source = import_service._extract_plan_metadata(row)
    assert plan_name == "LIVRE SEMESTRAL"
    assert plan_cycle == "semiannual"
    assert source == "dates"


def test_extract_plan_metadata_deduplicates_repeated_plan_labels() -> None:
    row = {
        "assinaturas": "LIVRE MENSAL, LIVRE MENSAL",
        "assinaturas_condicoes": "PLANO PRO-LIVRE 12 MESES,LIVRE - NORMAL",
    }
    plan_name, plan_cycle, source = import_service._extract_plan_metadata(row)
    assert plan_name == "LIVRE ANUAL"
    assert plan_cycle == "annual"
    assert source == "conditions"


def test_refresh_member_plan_metadata_reclassifies_existing_members() -> None:
    member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Aluno Reclassificado",
        email="aluno.reclassificado@example.com",
        status=MemberStatus.ACTIVE,
        plan_name="LIVRE MENSAL",
        monthly_fee=0,
        join_date=date(2026, 2, 1),
        extra_data={
            "raw_plan_name": "LIVRE MENSAL",
            "raw_plan_conditions": "LIVRE - NORMAL",
            "next_plan_renewal_raw": "01/08/2026",
        },
    )
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars

    updated = import_service.refresh_member_plan_metadata(db, gym_id=member.gym_id)

    assert updated == 1
    assert member.plan_name == "LIVRE SEMESTRAL"
    assert member.extra_data["plan_cycle"] == "semiannual"
    assert member.extra_data["plan_cycle_source"] == "dates"
    db.commit.assert_called_once()


def test_import_members_csv_updates_existing_duplicate_with_plan_cycle() -> None:
    member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Aluno Existente",
        email="aluno.existente@example.com",
        status=MemberStatus.ACTIVE,
        plan_name="Plano Base",
        monthly_fee=0,
        join_date=date(2026, 1, 1),
        extra_data={},
    )
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars

    csv_content = (
        "nome,email,assinaturas,assinaturas_condicoes,dt_primeira_ativacao,dt_prox_renovacao_assinatura\n"
        "Aluno Existente,aluno.existente@example.com,LIVRE MENSAL,PLANO PRO-LIVRE 12 MESES,01/02/2026,01/02/2027\n"
    ).encode("utf-8")

    summary = import_service.import_members_csv(db, csv_content, filename="clientes.csv")

    assert summary.imported == 0
    assert summary.updated_existing == 1
    assert summary.skipped_duplicates == 0
    assert member.plan_name == "LIVRE ANUAL"
    assert member.extra_data["plan_cycle"] == "annual"
    assert member.extra_data["plan_cycle_source"] == "conditions"
    assert db.commit.call_count == 2


def test_preview_members_csv_reports_updates_and_unknown_columns() -> None:
    member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Aluno Existente",
        email="aluno.existente@example.com",
        status=MemberStatus.ACTIVE,
        plan_name="Plano Base",
        monthly_fee=0,
        join_date=date(2026, 1, 1),
        extra_data={},
    )
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars

    csv_content = (
        "nome,email,data_matricula,coluna_extra\n"
        "Aluno Existente,aluno.existente@example.com,01/03/2026,sim\n"
        "Aluno Novo,novo@example.com,,sim\n"
    ).encode("utf-8")

    preview = import_service.preview_members_csv(db, csv_content, filename="clientes.csv")

    assert preview.preview_kind == "members"
    assert preview.total_rows == 2
    assert preview.valid_rows == 2
    assert preview.would_update == 1
    assert preview.would_create == 1
    assert "coluna_extra" in preview.unrecognized_columns
    assert any("atualizadas" in warning for warning in preview.warnings)
    assert any("nao geram onboarding" in warning for warning in preview.warnings)
    assert len(preview.sample_rows) == 2


def test_preview_members_csv_matches_existing_member_by_name_without_strong_identifiers() -> None:
    member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Tais Tomasi",
        email=None,
        status=MemberStatus.ACTIVE,
        plan_name="Plano Base",
        monthly_fee=0,
        join_date=date(2026, 1, 1),
        extra_data={},
    )
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars

    csv_content = "nome,telefones\nTais Tomasi,54999990000\n".encode("utf-8")

    preview = import_service.preview_members_csv(db, csv_content, filename="clientes.csv")

    assert preview.would_update == 1
    assert preview.would_create == 0
    assert preview.sample_rows[0].action == "update_member"


def test_preview_members_csv_reports_manual_mapping_metadata() -> None:
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    db.scalars.return_value = mock_scalars

    csv_content = "nome,email,registro\nAluno Novo,novo@example.com,MAT-001\n".encode("utf-8")

    preview = import_service.preview_members_csv(
        db,
        csv_content,
        filename="clientes.csv",
        column_mappings={"registro": "external_id"},
    )

    assert preview.unrecognized_columns == []
    assert preview.resolved_mappings == {"registro": "external_id"}
    assert preview.can_confirm is True
    assert any(
        column.source_key == "registro"
        and column.status == "mapped"
        and column.applied_target == "external_id"
        for column in preview.source_columns
    )


def test_import_members_csv_creates_import_playbook_tasks_for_recent_join_date(monkeypatch) -> None:
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    db.scalars.return_value = mock_scalars

    import_task_calls: list[str] = []

    monkeypatch.setattr(
        import_service,
        "create_import_playbook_tasks_for_member",
        lambda _db, member, commit=False: import_task_calls.append(member.full_name),
    )

    csv_content = f"nome,email,data_matricula\nAluno Novo,novo@example.com,{date.today().strftime('%d/%m/%Y')}\n".encode("utf-8")

    summary = import_service.import_members_csv(db, csv_content, filename="clientes.csv")

    assert summary.imported == 1
    assert import_task_calls == ["Aluno Novo"]
    assert db.flush.called


def test_import_members_csv_updates_existing_member_by_name_without_strong_identifiers() -> None:
    member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Tais Tomasi",
        email=None,
        status=MemberStatus.ACTIVE,
        plan_name="Plano Base",
        monthly_fee=0,
        join_date=date(2026, 1, 1),
        extra_data={},
    )
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars

    csv_content = "nome,telefones\nTais Tomasi,54999990000\n".encode("utf-8")

    summary = import_service.import_members_csv(db, csv_content, filename="clientes.csv")

    assert summary.imported == 0
    assert summary.updated_existing == 1
    assert member.phone == "54999990000"


def test_import_members_csv_skips_onboarding_when_join_date_is_missing(monkeypatch) -> None:
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    db.scalars.return_value = mock_scalars

    import_task_calls: list[str] = []

    monkeypatch.setattr(
        import_service,
        "create_import_playbook_tasks_for_member",
        lambda _db, member, commit=False: import_task_calls.append(member.full_name),
    )

    csv_content = "nome,email\nAluno Historico,historico@example.com\n".encode("utf-8")

    summary = import_service.import_members_csv(db, csv_content, filename="clientes.csv")

    assert summary.imported == 1
    assert import_task_calls == []


def test_import_members_csv_applies_manual_mapping_to_external_id() -> None:
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    db.scalars.return_value = mock_scalars

    csv_content = "nome,email,registro\nAluno Novo,novo@example.com,MAT-001\n".encode("utf-8")

    summary = import_service.import_members_csv(
        db,
        csv_content,
        filename="clientes.csv",
        column_mappings={"registro": "external_id"},
    )

    created_members = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], Member) and call.args[0].email == "novo@example.com"
    ]

    assert summary.imported == 1
    assert len(created_members) == 1
    assert created_members[0].extra_data["external_id"] == "mat-001"


def test_import_members_csv_reuses_lookup_for_duplicate_name_only_rows() -> None:
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    db.scalars.return_value = mock_scalars

    csv_content = "nome,telefones\nTais Tomasi,54999990000\nTais Tomasi,54999990000\n".encode("utf-8")

    summary = import_service.import_members_csv(db, csv_content, filename="clientes.csv")

    created_members = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], Member)]

    assert summary.imported == 1
    assert summary.updated_existing == 1
    assert len([member for member in created_members if member.full_name == "Tais Tomasi"]) == 1


def test_preview_members_csv_second_reimport_stays_at_updates_for_name_only_rows() -> None:
    db = _FakeMemberImportDB()
    csv_content = "nome\nTais Tomasi\nAna Silva\n".encode("utf-8")

    first_import = import_service.import_members_csv(db, csv_content, filename="clientes.csv")
    second_preview = import_service.preview_members_csv(db, csv_content, filename="clientes.csv")

    assert first_import.imported == 2
    assert second_preview.would_create == 0
    assert second_preview.would_update == 2
    assert second_preview.would_skip == 0


def test_import_members_csv_second_reimport_does_not_create_name_only_rows_again() -> None:
    db = _FakeMemberImportDB()
    csv_content = "nome\nTais Tomasi\nAna Silva\n".encode("utf-8")

    first_import = import_service.import_members_csv(db, csv_content, filename="clientes.csv")
    second_import = import_service.import_members_csv(db, csv_content, filename="clientes.csv")

    assert first_import.imported == 2
    assert second_import.imported == 0
    assert second_import.updated_existing == 2
    assert len([member for member in db.members if member.full_name in {"Tais Tomasi", "Ana Silva"}]) == 2


def test_add_member_to_lookups_is_idempotent_for_name_indexes() -> None:
    member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Tais Tomasi",
        email="tais@example.com",
        status=MemberStatus.ACTIVE,
        plan_name="Plano Base",
        monthly_fee=0,
        join_date=date(2026, 1, 1),
        extra_data={},
    )
    lookup = import_service._build_member_lookups([member])

    import_service._add_member_to_lookups(member, lookup)

    name_key = import_service._normalize_text(member.full_name)
    compact_key = import_service._compact_name(member.full_name)
    core_key = import_service._core_name_key(member.full_name)

    assert len(lookup["by_name"][name_key]) == 1
    assert len(lookup["by_name_compact"][compact_key]) == 1
    assert len(lookup["by_name_core"][core_key]) == 1


def test_import_members_csv_refreshes_risk_snapshot_for_touched_members(monkeypatch) -> None:
    member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Aluno Existente",
        email="aluno.existente@example.com",
        status=MemberStatus.ACTIVE,
        plan_name="Plano Base",
        monthly_fee=0,
        join_date=date(2026, 1, 1),
        extra_data={},
    )
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars

    def _assign_ids_on_commit():
        for call in db.add.call_args_list:
            candidate = call.args[0]
            if isinstance(candidate, Member) and candidate.id is None:
                candidate.id = uuid4()

    db.commit.side_effect = _assign_ids_on_commit

    refreshed_ids: list[set] = []
    monkeypatch.setattr(
        import_service,
        "refresh_member_risk_snapshot",
        lambda _db, *, member_ids, now=None, sync_alerts=False: refreshed_ids.append(set(member_ids)) or {"members_refreshed": len(set(member_ids))},
    )

    csv_content = (
        "nome,email,ult_acesso\n"
        "Aluno Existente,aluno.existente@example.com,04/03/2026 08:11\n"
        "Aluno Novo,novo@example.com,04/03/2026 08:11\n"
    ).encode("utf-8")

    summary = import_service.import_members_csv(db, csv_content, filename="clientes.csv")

    created_members = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], Member) and call.args[0].email == "novo@example.com"
    ]

    assert summary.imported == 1
    assert summary.updated_existing == 1
    assert len(created_members) == 1
    assert refreshed_ids == [{member.id, created_members[0].id}]


def test_preview_members_csv_warns_about_next_action_task_generation() -> None:
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    db.scalars.return_value = mock_scalars

    csv_content = f"nome,email,data_matricula\nAluno Novo,novo@example.com,{date.today().strftime('%d/%m/%Y')}\n".encode("utf-8")

    preview = import_service.preview_members_csv(db, csv_content, filename="clientes.csv")

    assert any("proxima acao operacional" in warning for warning in preview.warnings)


def test_import_members_csv_rejects_conflicting_manual_mappings() -> None:
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    db.scalars.return_value = mock_scalars

    csv_content = "nome,registro,codigo\nAluno Novo,MAT-001,COD-001\n".encode("utf-8")

    with pytest.raises(ValueError, match="mesmo campo de destino"):
        import_service.import_members_csv(
            db,
            csv_content,
            filename="clientes.csv",
            column_mappings={"registro": "external_id", "codigo": "external_id"},
        )


def test_extract_preferred_shift_uses_schedule_column() -> None:
    row = {"assinaturas_horarios": "Manha"}
    assert import_service._extract_preferred_shift(row) == "Manha"


def test_extract_member_name_combines_first_and_last_names() -> None:
    row = {"primeiro_nome": "Ana", "sobrenome": "Silva"}
    assert import_service._extract_member_name(row) == "Ana Silva"


def test_extract_member_name_collapses_repeated_spaces() -> None:
    row = {"nome": "Mateus   Dalsant   Zonatto"}
    assert import_service._extract_member_name(row) == "Mateus Dalsant Zonatto"


def test_external_id_candidates_include_digits_and_zero_stripped() -> None:
    candidates = import_service._external_id_candidates("000123")
    assert candidates == ("000123", "123")


def test_resolve_member_from_row_matches_compact_name_and_external_id() -> None:
    member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Maria da Silva",
        email="maria@example.com",
        status=MemberStatus.ACTIVE,
        plan_name="Mensal",
        monthly_fee=0,
        join_date=date(2026, 1, 1),
        extra_data={"external_id": "000123"},
    )
    lookup = import_service._build_member_lookups([member])

    by_name = import_service._resolve_member_from_row({"nome": "Mariadasilva"}, lookup)
    by_external_id = import_service._resolve_member_from_row({"codigo_acesso": "123"}, lookup)

    assert by_name is member
    assert by_external_id is member


def test_is_ignorable_checkin_row_skips_manual_turnstile_events() -> None:
    assert import_service._is_ignorable_checkin_row({"nome": "Passagem liberada manualmente"}) is True
    assert import_service._is_ignorable_checkin_row({"nome": "Total de registros:"}) is True
    assert import_service._is_ignorable_checkin_row({"nome": "Gabriel Rosalem"}) is False


def test_resolve_member_from_row_prefers_active_member_when_name_is_duplicated() -> None:
    cancelled = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Iago Gehlen",
        email=None,
        status=MemberStatus.CANCELLED,
        plan_name="Mensal",
        monthly_fee=0,
        join_date=date(2020, 3, 12),
        extra_data={},
    )
    active = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Iago Gehlen",
        email="iago@example.com",
        status=MemberStatus.ACTIVE,
        plan_name="Mensal",
        monthly_fee=0,
        join_date=date(2020, 8, 3),
        extra_data={},
    )
    lookup = import_service._build_member_lookups([cancelled, active])

    resolved = import_service._resolve_member_from_row({"nome": "Iago Gehlen"}, lookup)

    assert resolved is active


def test_build_missing_member_entries_returns_sorted_entries() -> None:
    entries = import_service._build_missing_member_entries(
        Counter({"Mateus Zonatto": 4, "Ronaldo Dos Santos": 2}),
        {"Mateus Zonatto": "Mensal"},
    )

    assert [entry.name for entry in entries] == ["Mateus Zonatto", "Ronaldo Dos Santos"]
    assert entries[0].occurrences == 4
    assert entries[0].sample_plan == "Mensal"
    assert entries[1].sample_plan is None


def test_create_provisional_member_from_checkin_builds_member() -> None:
    db = MagicMock()
    row = {"nome": "Ronaldo Dos Santos", "assinatura": "Plano Silver", "codigo_acesso": "00045"}
    parsed = import_service._parse_datetime("2026-03-07 08:30")

    member = import_service._create_provisional_member_from_checkin(db, row, parsed)

    assert member is not None
    assert member.full_name == "Ronaldo Dos Santos"
    assert member.plan_name == "Plano Silver"
    assert member.status == MemberStatus.ACTIVE
    assert member.extra_data["provisional_member"] is True
    assert member.extra_data["external_id"] == "00045"
    db.add.assert_called_once_with(member)
    db.flush.assert_called_once()


def test_import_checkins_csv_groups_missing_members() -> None:
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    db.scalars.return_value = mock_scalars
    db.execute.return_value.all.return_value = []

    csv_content = (
        "nome,data,hora\n"
        "Mateus Dalsant Zonatto,2026-03-01,08:00\n"
        "Mateus Dalsant Zonatto,2026-03-01,18:00\n"
        "Ronaldo Dos Santos,2026-03-02,07:30\n"
    ).encode("utf-8")

    summary = import_service.import_checkins_csv(db, csv_content)

    assert summary.imported == 0
    assert summary.provisional_members_created == 0
    assert summary.ignored_rows == 0
    assert len(summary.errors) == 3
    assert [item.name for item in summary.missing_members] == [
        "Mateus Dalsant Zonatto",
        "Ronaldo Dos Santos",
    ]
    assert summary.missing_members[0].occurrences == 2


def test_import_checkins_csv_auto_creates_missing_members(monkeypatch) -> None:
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    db.scalars.return_value = mock_scalars
    db.execute.return_value.all.return_value = []

    provisional_member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Mateus Dalsant Zonatto",
        email=None,
        status=MemberStatus.ACTIVE,
        plan_name="Plano Base",
        monthly_fee=0,
        join_date=date(2026, 3, 1),
        extra_data={"provisional_member": True},
    )

    monkeypatch.setattr(
        import_service,
        "_create_provisional_member_from_checkin",
        lambda _db, _row, _parsed: provisional_member,
    )

    csv_content = "nome,data,hora\nMateus Dalsant Zonatto,2026-03-01,08:00\n".encode("utf-8")

    summary = import_service.import_checkins_csv(db, csv_content, auto_create_missing_members=True)

    assert summary.imported == 1
    assert summary.provisional_members_created == 1
    assert summary.provisional_members == ["Mateus Dalsant Zonatto"]
    assert summary.missing_members == []
    assert summary.errors == []
    assert any(call.args and call.args[0].__class__.__name__ == "Checkin" for call in db.add.call_args_list)


def test_import_checkins_csv_applies_manual_mapping_to_external_id() -> None:
    member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Aluno Existente",
        email="aluno.existente@example.com",
        status=MemberStatus.ACTIVE,
        plan_name="Mensal",
        monthly_fee=0,
        join_date=date(2026, 1, 1),
        extra_data={"external_id": "mat-001"},
    )
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars
    db.execute.return_value.all.return_value = []

    csv_content = "registro,data,hora\nMAT-001,2026-03-01,08:00\n".encode("utf-8")

    summary = import_service.import_checkins_csv(
        db,
        csv_content,
        filename="checkins.csv",
        column_mappings={"registro": "external_id"},
    )

    assert summary.imported == 1
    assert summary.errors == []
    assert any(call.args and call.args[0].__class__.__name__ == "Checkin" for call in db.add.call_args_list)


def test_import_checkins_csv_accepts_turnstile_xlsx_with_data_entrada_serial() -> None:
    member = Member(
        id=uuid4(),
        gym_id=uuid4(),
        full_name="Diego Rafagnin De Oliverira",
        email=None,
        status=MemberStatus.ACTIVE,
        plan_name="LIVRE MENSAL",
        monthly_fee=0,
        join_date=date(2026, 1, 1),
        cpf_encrypted=None,
        extra_data={"external_id": "0001"},
    )

    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars
    db.execute.return_value.all.return_value = []

    xlsx_content = _build_xlsx_bytes(
        headers=[
            "Data Entrada",
            "Hora Entrada",
            "Data Saída",
            "Hora Saída",
            "Tipo Cadastro",
            "Cliente",
            "Assinatura",
            "CPF",
        ],
        rows=[
            [46097.834181909726, "20:01", 46097.83567262732, "20:03", "Cliente", "Diego Rafagnin De Oliverira", "LIVRE MENSAL", ""],
        ],
    )

    summary = import_service.import_checkins_csv(db, xlsx_content, filename="Acessos.xlsx")

    assert summary.imported == 1
    assert summary.errors == []
    assert summary.skipped_duplicates == 0
    assert any(call.args and call.args[0].__class__.__name__ == "Checkin" for call in db.add.call_args_list)
