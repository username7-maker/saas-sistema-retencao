import csv
import io
import re
import unicodedata
import zipfile
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Checkin, CheckinSource, Member, MemberStatus
from app.schemas import ImportErrorEntry, ImportSummary
from app.utils.encryption import decrypt_cpf, encrypt_cpf


NAME_KEYS = ("full_name", "name", "nome", "aluno", "member_name", "cliente")
EMAIL_KEYS = ("email", "e_mail", "mail", "member_email")
PHONE_KEYS = ("phone", "telefone", "telefones", "celular", "whatsapp")
CPF_KEYS = ("cpf", "documento", "document", "cpf_cnpj")
PLAN_KEYS = ("plan_name", "plan", "plano", "plano_nome", "assinaturas", "assinaturas_condicoes", "assinaturas_horarios")
MONTHLY_FEE_KEYS = ("monthly_fee", "mensalidade", "valor", "valor_mensal", "price")
JOIN_DATE_KEYS = ("join_date", "data_matricula", "data_adesao", "data_inicio", "start_date", "cadastro", "dt_primeira_ativacao", "conversao")
PREFERRED_SHIFT_KEYS = ("preferred_shift", "turno", "turno_preferido", "horario", "shift")
STATUS_KEYS = ("status", "situacao", "state")
EXTERNAL_ID_KEYS = ("external_id", "matricula", "codigo", "member_code", "id_aluno", "id_externo", "codigo_acesso")

MEMBER_ID_KEYS = ("member_id", "id_membro", "aluno_id", "member_uuid")
CHECKIN_AT_KEYS = ("checkin_at", "data_checkin", "checkin", "data_hora", "datetime", "timestamp")
CHECKIN_DATE_KEYS = ("checkin_date", "data_checkin", "data", "date")
CHECKIN_TIME_KEYS = ("checkin_time", "hora_checkin", "hora", "time")
CHECKIN_SOURCE_KEYS = ("source", "origem", "tipo")

DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y")
DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
)


def import_members_csv(db: Session, csv_content: bytes, filename: str | None = None) -> ImportSummary:
    errors: list[ImportErrorEntry] = []
    duplicates = 0
    imported = 0

    existing_members = list(db.scalars(select(Member).where(Member.deleted_at.is_(None))).all())
    lookup = _build_member_lookups(existing_members)
    seen_emails: set[str] = set()
    seen_external_ids: set[str] = set()
    seen_cpfs: set[str] = set()

    for row_number, row in _iter_rows(csv_content, filename=filename):
        full_name = _pick_first(row, NAME_KEYS)
        if not full_name:
            errors.append(ImportErrorEntry(row_number=row_number, reason="Nome ausente", payload=row))
            continue

        email = (_pick_first(row, EMAIL_KEYS) or "").lower() or None
        external_id = (_pick_first(row, EXTERNAL_ID_KEYS) or "").strip().lower() or None
        cpf_digits = _digits(_pick_first(row, CPF_KEYS))

        if email and (email in seen_emails or email in lookup["by_email"]):
            duplicates += 1
            continue
        if external_id and (external_id in seen_external_ids or external_id in lookup["by_external_id"]):
            duplicates += 1
            continue
        if cpf_digits and (cpf_digits in seen_cpfs or cpf_digits in lookup["by_cpf"]):
            duplicates += 1
            continue

        monthly_fee_raw = _pick_first(row, MONTHLY_FEE_KEYS)
        join_date_raw = _pick_first(row, JOIN_DATE_KEYS)
        try:
            monthly_fee = _parse_decimal(monthly_fee_raw)
            join_date = _parse_date(join_date_raw) or datetime.now(tz=timezone.utc).date()
        except ValueError:
            errors.append(
                ImportErrorEntry(
                    row_number=row_number,
                    reason="Formato invalido de valor/data",
                    payload=row,
                )
            )
            continue

        extra_data: dict = {"imported": True}
        if external_id:
            extra_data["external_id"] = external_id

        member = Member(
            full_name=full_name,
            email=email,
            phone=_pick_first(row, PHONE_KEYS),
            cpf_encrypted=encrypt_cpf(cpf_digits) if cpf_digits else None,
            status=_parse_member_status(_pick_first(row, STATUS_KEYS)),
            plan_name=_pick_first(row, PLAN_KEYS) or "Plano Base",
            monthly_fee=monthly_fee,
            join_date=join_date,
            preferred_shift=_pick_first(row, PREFERRED_SHIFT_KEYS),
            extra_data=extra_data,
        )
        db.add(member)
        imported += 1

        if email:
            seen_emails.add(email)
        if external_id:
            seen_external_ids.add(external_id)
        if cpf_digits:
            seen_cpfs.add(cpf_digits)

    db.commit()
    if imported:
        invalidate_dashboard_cache("members")
    return ImportSummary(imported=imported, skipped_duplicates=duplicates, errors=errors)


def import_checkins_csv(db: Session, csv_content: bytes, filename: str | None = None) -> ImportSummary:
    errors: list[ImportErrorEntry] = []
    duplicates = 0
    imported = 0
    seen_entries: set[tuple[str, str]] = set()

    existing_members = list(db.scalars(select(Member).where(Member.deleted_at.is_(None))).all())
    lookup = _build_member_lookups(existing_members)

    for row_number, row in _iter_rows(csv_content, filename=filename):
        member = _resolve_member_from_row(row, lookup)
        if not member:
            errors.append(
                ImportErrorEntry(
                    row_number=row_number,
                    reason="Membro nao encontrado (use member_id, email, matricula, cpf ou nome)",
                    payload=row,
                )
            )
            continue

        checkin_raw = _pick_first(row, CHECKIN_AT_KEYS)
        if not checkin_raw:
            date_raw = _pick_first(row, CHECKIN_DATE_KEYS)
            time_raw = _pick_first(row, CHECKIN_TIME_KEYS)
            if date_raw and time_raw:
                checkin_raw = f"{date_raw} {time_raw}"
            else:
                checkin_raw = date_raw

        parsed = _parse_datetime(checkin_raw)
        if not parsed:
            errors.append(ImportErrorEntry(row_number=row_number, reason="Formato de data invalido", payload=row))
            continue

        unique_key = (str(member.id), parsed.isoformat())
        if unique_key in seen_entries:
            duplicates += 1
            continue
        seen_entries.add(unique_key)

        exists = db.scalar(select(Checkin.id).where(Checkin.member_id == member.id, Checkin.checkin_at == parsed))
        if exists:
            duplicates += 1
            continue

        checkin = Checkin(
            member_id=member.id,
            checkin_at=parsed,
            source=_parse_checkin_source(_pick_first(row, CHECKIN_SOURCE_KEYS)),
            hour_bucket=parsed.hour,
            weekday=parsed.weekday(),
            extra_data={"imported": True, "raw": row},
        )
        if member.last_checkin_at is None or parsed > member.last_checkin_at:
            member.last_checkin_at = parsed
        db.add(checkin)
        db.add(member)
        imported += 1

    db.commit()
    if imported:
        invalidate_dashboard_cache("checkins")
    return ImportSummary(imported=imported, skipped_duplicates=duplicates, errors=errors)


def _decode_csv_text(csv_content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return csv_content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return csv_content.decode("utf-8", errors="ignore")


def _iter_rows(csv_content: bytes, filename: str | None = None):
    kind = _detect_file_kind(csv_content, filename)
    if kind == "xlsx":
        yield from _iter_rows_xlsx(csv_content)
        return
    yield from _iter_rows_csv(csv_content)


def _detect_file_kind(content: bytes, filename: str | None) -> str:
    if filename:
        lower = filename.lower()
        if lower.endswith(".xlsx"):
            return "xlsx"
        if lower.endswith(".csv"):
            return "csv"
    if content.startswith(b"PK\x03\x04"):
        return "xlsx"
    return "csv"


def _iter_rows_csv(csv_content: bytes):
    text = _decode_csv_text(csv_content)
    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    for row_number, row in enumerate(reader, start=2):
        yield row_number, _normalize_row(row)


def _iter_rows_xlsx(content: bytes):
    try:
        from openpyxl import load_workbook
    except ImportError:
        yield from _iter_rows_xlsx_fallback(content)
        return

    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError("Arquivo XLSX invalido ou corrompido.") from exc

    try:
        worksheet = workbook.active
        header_cells = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if not header_cells:
            return

        headers = [str(cell).strip() if cell is not None else "" for cell in header_cells]
        for row_number, row_cells in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
            raw_row: dict[str | None, str | None] = {}
            has_value = False
            for idx, header in enumerate(headers):
                if not header:
                    continue
                value = row_cells[idx] if idx < len(row_cells) else None
                normalized_value = _xlsx_cell_to_text(value)
                if normalized_value:
                    has_value = True
                raw_row[header] = normalized_value
            if not has_value:
                continue
            yield row_number, _normalize_row(raw_row)
    finally:
        workbook.close()


def _iter_rows_xlsx_fallback(content: bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            worksheet_path = _xlsx_first_sheet_path(archive)
            shared_strings = _xlsx_shared_strings(archive)
            worksheet_xml = archive.read(worksheet_path)
    except Exception as exc:
        raise ValueError("Arquivo XLSX invalido ou corrompido.") from exc

    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(worksheet_xml)
    rows = root.findall(".//x:sheetData/x:row", ns)
    if not rows:
        return

    header_values = _xlsx_row_values(rows[0], shared_strings, ns)
    headers = [str(value).strip() if value is not None else "" for value in header_values]
    for row in rows[1:]:
        row_number = int(row.attrib.get("r", "0") or "0")
        values = _xlsx_row_values(row, shared_strings, ns)
        raw_row: dict[str | None, str | None] = {}
        has_value = False
        for idx, header in enumerate(headers):
            if not header:
                continue
            value = values[idx] if idx < len(values) else None
            normalized_value = _xlsx_cell_to_text(value)
            if normalized_value:
                has_value = True
            raw_row[header] = normalized_value
        if not has_value:
            continue
        yield (row_number or 0), _normalize_row(raw_row)


def _xlsx_first_sheet_path(archive: zipfile.ZipFile) -> str:
    default_path = "xl/worksheets/sheet1.xml"
    if default_path in archive.namelist():
        return default_path

    workbook_xml = archive.read("xl/workbook.xml")
    workbook_rels_xml = archive.read("xl/_rels/workbook.xml.rels")

    workbook_ns = {
        "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    rels_ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}

    workbook_root = ET.fromstring(workbook_xml)
    first_sheet = workbook_root.find(".//x:sheets/x:sheet", workbook_ns)
    if first_sheet is None:
        raise ValueError("Planilha XLSX sem abas.")
    rel_id = first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    if not rel_id:
        raise ValueError("Planilha XLSX sem relacao de aba.")

    rels_root = ET.fromstring(workbook_rels_xml)
    for rel in rels_root.findall(".//r:Relationship", rels_ns):
        if rel.attrib.get("Id") != rel_id:
            continue
        target = rel.attrib.get("Target", "").lstrip("/")
        if not target:
            break
        if target.startswith("xl/"):
            return target
        return f"xl/{target}"
    raise ValueError("Nao foi possivel localizar a aba principal no XLSX.")


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in archive.namelist():
        return []

    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(archive.read(path))
    values: list[str] = []
    for si in root.findall(".//x:si", ns):
        texts = [node.text or "" for node in si.findall(".//x:t", ns)]
        values.append("".join(texts))
    return values


def _xlsx_row_values(row: ET.Element, shared_strings: list[str], ns: dict[str, str]) -> list[object | None]:
    values: list[object | None] = []
    for cell in row.findall("x:c", ns):
        ref = cell.attrib.get("r", "")
        col_index = _xlsx_col_index(ref)
        while len(values) <= col_index:
            values.append(None)
        values[col_index] = _xlsx_cell_value(cell, shared_strings, ns)
    return values


def _xlsx_col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    if not letters:
        return 0
    index = 0
    for letter in letters:
        index = index * 26 + (ord(letter) - ord("A") + 1)
    return index - 1


def _xlsx_cell_value(cell: ET.Element, shared_strings: list[str], ns: dict[str, str]) -> object | None:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        node = cell.find("x:is/x:t", ns)
        return node.text if node is not None else ""

    value_node = cell.find("x:v", ns)
    raw_value = value_node.text if value_node is not None else ""
    if raw_value is None:
        return ""

    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except Exception:
            return raw_value
    if cell_type == "b":
        return "1" if raw_value == "1" else "0"
    return raw_value


def _xlsx_cell_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


def _detect_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:10]) or text
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
        return dialect.delimiter
    except csv.Error:
        first_line = sample.splitlines()[0] if sample else ""
        return ";" if first_line.count(";") > first_line.count(",") else ","


def _normalize_row(row: dict[str | None, str | None]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        if not key:
            continue
        normalized_key = _normalize_header(key)
        if not normalized_key:
            continue
        normalized[normalized_key] = (value or "").strip()
    return normalized


def _normalize_header(value: str) -> str:
    collapsed = _normalize_text(value)
    normalized = re.sub(r"[^a-z0-9]+", "_", collapsed).strip("_")
    return normalized


def _normalize_text(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def _pick_first(row: dict[str, str], aliases: tuple[str, ...]) -> str | None:
    for key in aliases:
        value = row.get(key)
        if value:
            return value.strip()
    return None


def _digits(value: str | None) -> str:
    return re.sub(r"\D+", "", value or "")


def _parse_decimal(value: str | None) -> Decimal:
    if not value:
        return Decimal("0")
    cleaned = value.strip().replace("R$", "").replace(" ", "")
    if not cleaned:
        return Decimal("0")
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("decimal invalido") from exc


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None

    serial = _parse_excel_serial(raw)
    if serial is not None:
        return _excel_serial_to_datetime(serial).date()

    if "T" in raw:
        raw = raw.split("T", 1)[0]
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None

    serial = _parse_excel_serial(raw)
    if serial is not None:
        return _excel_serial_to_datetime(serial).replace(tzinfo=timezone.utc)

    iso_candidate = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_candidate)
    except ValueError:
        parsed = None

    if parsed is None:
        for fmt in DATETIME_FORMATS:
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        parsed_date = _parse_date(raw)
        if parsed_date:
            parsed = datetime.combine(parsed_date, time.min)
        else:
            return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_member_status(raw_value: str | None) -> MemberStatus:
    key = _normalize_header(raw_value or "")
    mapping = {
        "active": MemberStatus.ACTIVE,
        "ativo": MemberStatus.ACTIVE,
        "a": MemberStatus.ACTIVE,
        "paused": MemberStatus.PAUSED,
        "pausado": MemberStatus.PAUSED,
        "p": MemberStatus.PAUSED,
        "cancelled": MemberStatus.CANCELLED,
        "canceled": MemberStatus.CANCELLED,
        "cancelado": MemberStatus.CANCELLED,
        "inactive": MemberStatus.CANCELLED,
        "inativo": MemberStatus.CANCELLED,
        "i": MemberStatus.CANCELLED,
    }
    return mapping.get(key, MemberStatus.ACTIVE)


def _parse_excel_serial(raw_value: str) -> float | None:
    cleaned = raw_value.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        serial = float(cleaned)
    except ValueError:
        return None
    if serial <= 0:
        return None
    return serial


def _excel_serial_to_datetime(serial: float) -> datetime:
    # Excel uses 1899-12-30 as base in the 1900 date system.
    base = datetime(1899, 12, 30)
    days = int(serial)
    fraction = serial - days
    seconds = int(round(fraction * 86400))
    if seconds >= 86400:
        days += 1
        seconds -= 86400
    return base + timedelta(days=days, seconds=seconds)


def _parse_checkin_source(raw_value: str | None) -> CheckinSource:
    key = _normalize_header(raw_value or "")
    mapping = {
        "manual": CheckinSource.MANUAL,
        "turnstile": CheckinSource.TURNSTILE,
        "catraca": CheckinSource.TURNSTILE,
        "import": CheckinSource.IMPORT,
        "importado": CheckinSource.IMPORT,
    }
    return mapping.get(key, CheckinSource.IMPORT)


def _build_member_lookups(members: list[Member]) -> dict[str, dict]:
    by_id: dict[str, Member] = {}
    by_email: dict[str, Member] = {}
    by_external_id: dict[str, Member] = {}
    by_cpf: dict[str, Member] = {}
    by_name: dict[str, list[Member]] = {}

    for member in members:
        by_id[str(member.id)] = member

        if member.email:
            by_email[member.email.lower()] = member

        extra_data = member.extra_data or {}
        external_id = str(extra_data.get("external_id") or "").strip().lower()
        if external_id:
            by_external_id[external_id] = member

        if member.cpf_encrypted:
            try:
                cpf_digits = _digits(decrypt_cpf(member.cpf_encrypted))
                if cpf_digits and cpf_digits not in by_cpf:
                    by_cpf[cpf_digits] = member
            except Exception:
                pass

        name_key = _normalize_text(member.full_name)
        by_name.setdefault(name_key, []).append(member)

    return {
        "by_id": by_id,
        "by_email": by_email,
        "by_external_id": by_external_id,
        "by_cpf": by_cpf,
        "by_name": by_name,
    }


def _resolve_member_from_row(row: dict[str, str], lookup: dict[str, dict]) -> Member | None:
    member_id_raw = _pick_first(row, MEMBER_ID_KEYS)
    if member_id_raw:
        try:
            parsed_uuid = UUID(member_id_raw)
            member = lookup["by_id"].get(str(parsed_uuid))
            if member:
                return member
        except ValueError:
            # Segue para outras estrategias de match.
            pass

    email = (_pick_first(row, EMAIL_KEYS) or "").lower()
    if email:
        member = lookup["by_email"].get(email)
        if member:
            return member

    external_id = (_pick_first(row, EXTERNAL_ID_KEYS) or member_id_raw or "").strip().lower()
    if external_id:
        member = lookup["by_external_id"].get(external_id)
        if member:
            return member

    cpf_digits = _digits(_pick_first(row, CPF_KEYS))
    if cpf_digits:
        member = lookup["by_cpf"].get(cpf_digits)
        if member:
            return member

    name = _pick_first(row, NAME_KEYS)
    if name:
        candidates = lookup["by_name"].get(_normalize_text(name), [])
        if len(candidates) == 1:
            return candidates[0]

    return None
