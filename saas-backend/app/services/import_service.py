import csv
import io
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Checkin, CheckinSource, Member
from app.schemas import ImportErrorEntry, ImportSummary
from app.utils.encryption import encrypt_cpf


def import_members_csv(db: Session, csv_content: bytes) -> ImportSummary:
    reader = csv.DictReader(io.StringIO(csv_content.decode("utf-8-sig")))
    errors: list[ImportErrorEntry] = []
    duplicates = 0
    imported = 0
    seen_emails: set[str] = set()

    for row_number, row in enumerate(reader, start=2):
        normalized = {key.strip().lower(): (value or "").strip() for key, value in row.items()}
        email = normalized.get("email") or normalized.get("e-mail")
        full_name = normalized.get("full_name") or normalized.get("name") or normalized.get("nome")
        if not full_name:
            errors.append(ImportErrorEntry(row_number=row_number, reason="Nome ausente", payload=row))
            continue

        if email:
            lower_email = email.lower()
            if lower_email in seen_emails:
                duplicates += 1
                continue
            seen_emails.add(lower_email)
            exists = db.scalar(select(Member).where(Member.email == lower_email, Member.deleted_at.is_(None)))
            if exists:
                duplicates += 1
                continue
        else:
            lower_email = None

        try:
            fee = Decimal(normalized.get("monthly_fee", "0").replace(",", ".") or "0")
            join_date = datetime.strptime(normalized.get("join_date", ""), "%Y-%m-%d").date() if normalized.get("join_date") else datetime.now().date()
        except Exception:
            errors.append(ImportErrorEntry(row_number=row_number, reason="Formato invalido de valor/data", payload=row))
            continue

        member = Member(
            full_name=full_name,
            email=lower_email,
            phone=normalized.get("phone") or normalized.get("telefone") or None,
            cpf_encrypted=encrypt_cpf(normalized["cpf"]) if normalized.get("cpf") else None,
            plan_name=normalized.get("plan_name") or "Plano Base",
            monthly_fee=fee,
            join_date=join_date,
            preferred_shift=normalized.get("preferred_shift") or None,
        )
        db.add(member)
        imported += 1

    db.commit()
    if imported:
        invalidate_dashboard_cache("members")
    return ImportSummary(imported=imported, skipped_duplicates=duplicates, errors=errors)


def import_checkins_csv(db: Session, csv_content: bytes) -> ImportSummary:
    reader = csv.DictReader(io.StringIO(csv_content.decode("utf-8-sig")))
    errors: list[ImportErrorEntry] = []
    duplicates = 0
    imported = 0
    seen_entries: set[tuple[str, str]] = set()

    for row_number, row in enumerate(reader, start=2):
        normalized = {key.strip().lower(): (value or "").strip() for key, value in row.items()}
        member_id = normalized.get("member_id")
        member_email = normalized.get("member_email") or normalized.get("email")
        checkin_raw = normalized.get("checkin_at") or normalized.get("data_checkin")
        if not checkin_raw:
            errors.append(ImportErrorEntry(row_number=row_number, reason="checkin_at ausente", payload=row))
            continue

        member = None
        if member_id:
            try:
                member = db.get(Member, UUID(member_id))
            except ValueError:
                errors.append(ImportErrorEntry(row_number=row_number, reason="member_id invalido", payload=row))
                continue
        elif member_email:
            member = db.scalar(
                select(Member).where(Member.email == member_email.lower(), Member.deleted_at.is_(None))
            )
        if not member:
            errors.append(ImportErrorEntry(row_number=row_number, reason="Membro nao encontrado", payload=row))
            continue

        parsed = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                parsed = datetime.strptime(checkin_raw, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            errors.append(ImportErrorEntry(row_number=row_number, reason="Formato de data invalido", payload=row))
            continue

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        unique_key = (str(member.id), parsed.isoformat())
        if unique_key in seen_entries:
            duplicates += 1
            continue
        seen_entries.add(unique_key)

        exists = db.scalar(select(Checkin).where(Checkin.member_id == member.id, Checkin.checkin_at == parsed))
        if exists:
            duplicates += 1
            continue

        checkin = Checkin(
            member_id=member.id,
            checkin_at=parsed,
            source=CheckinSource.IMPORT,
            hour_bucket=parsed.hour,
            weekday=parsed.weekday(),
            extra_data={"imported": True},
        )
        member.last_checkin_at = max(filter(None, [member.last_checkin_at, parsed]))
        db.add(checkin)
        db.add(member)
        imported += 1

    db.commit()
    if imported:
        invalidate_dashboard_cache("checkins")
    return ImportSummary(imported=imported, skipped_duplicates=duplicates, errors=errors)
