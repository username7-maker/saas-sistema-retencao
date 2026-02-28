from datetime import timezone
from io import BytesIO
import zipfile
from xml.sax.saxutils import escape

from app.models import CheckinSource, MemberStatus
from app.services import import_service


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
