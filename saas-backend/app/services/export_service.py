import csv
from datetime import date, datetime, time, timezone
from io import BytesIO, StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Checkin, Member


def export_members_csv(db: Session) -> tuple[BytesIO, str]:
    members = list(
        db.scalars(
            select(Member)
            .where(Member.deleted_at.is_(None))
            .order_by(Member.full_name.asc())
        ).all()
    )

    headers = [
        "id",
        "full_name",
        "email",
        "phone",
        "plan_name",
        "monthly_fee",
        "join_date",
        "status",
        "preferred_shift",
        "nps_last_score",
        "loyalty_months",
        "risk_score",
        "risk_level",
        "last_checkin_at",
        "external_id",
    ]

    rows: list[dict[str, str]] = []
    for member in members:
        extra_data = member.extra_data or {}
        rows.append(
            {
                "id": str(member.id),
                "full_name": member.full_name,
                "email": member.email or "",
                "phone": member.phone or "",
                "plan_name": member.plan_name,
                "monthly_fee": f"{member.monthly_fee:.2f}",
                "join_date": member.join_date.isoformat(),
                "status": member.status.value,
                "preferred_shift": member.preferred_shift or "",
                "nps_last_score": str(member.nps_last_score),
                "loyalty_months": str(member.loyalty_months),
                "risk_score": str(member.risk_score),
                "risk_level": member.risk_level.value,
                "last_checkin_at": member.last_checkin_at.isoformat() if member.last_checkin_at else "",
                "external_id": str(extra_data.get("external_id") or ""),
            }
        )

    buffer = _dict_rows_to_csv(headers, rows)
    filename = f"members_export_{date.today().isoformat()}.csv"
    return buffer, filename


def export_checkins_csv(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[BytesIO, str]:
    stmt = (
        select(Checkin, Member)
        .join(Member, Member.id == Checkin.member_id)
        .where(Member.deleted_at.is_(None))
    )

    if date_from:
        start_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        stmt = stmt.where(Checkin.checkin_at >= start_dt)
    if date_to:
        end_dt = datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(Checkin.checkin_at <= end_dt)

    rows_db = list(db.execute(stmt.order_by(Checkin.checkin_at.desc())).all())

    headers = [
        "id",
        "member_id",
        "member_name",
        "member_email",
        "member_external_id",
        "checkin_at",
        "source",
        "hour_bucket",
        "weekday",
        "nome",
        "email",
        "matricula",
        "data_checkin",
        "hora",
        "origem",
    ]

    rows: list[dict[str, str]] = []
    for checkin, member in rows_db:
        extra_data = member.extra_data or {}
        checkin_at = checkin.checkin_at
        if checkin_at.tzinfo is None:
            checkin_at = checkin_at.replace(tzinfo=timezone.utc)
        source = checkin.source.value
        origem = "catraca" if source == "turnstile" else source
        rows.append(
            {
                "id": str(checkin.id),
                "member_id": str(member.id),
                "member_name": member.full_name,
                "member_email": member.email or "",
                "member_external_id": str(extra_data.get("external_id") or ""),
                "checkin_at": checkin_at.isoformat(),
                "source": source,
                "hour_bucket": str(checkin.hour_bucket),
                "weekday": str(checkin.weekday),
                # Compatibility aliases used by turnstile spreadsheets/imports.
                "nome": member.full_name,
                "email": member.email or "",
                "matricula": str(extra_data.get("external_id") or ""),
                "data_checkin": checkin_at.date().isoformat(),
                "hora": checkin_at.strftime("%H:%M:%S"),
                "origem": origem,
            }
        )

    suffix = date.today().isoformat()
    if date_from or date_to:
        from_part = date_from.isoformat() if date_from else "start"
        to_part = date_to.isoformat() if date_to else "today"
        suffix = f"{from_part}_to_{to_part}"
    filename = f"checkins_export_{suffix}.csv"
    return _dict_rows_to_csv(headers, rows), filename


def export_members_template_csv() -> tuple[BytesIO, str]:
    headers = ["nome", "email", "telefone", "cpf", "matricula", "plano", "mensalidade", "data_matricula", "turno", "status"]
    rows = [
        {
            "nome": "Joao Silva",
            "email": "joao@example.com",
            "telefone": "11999999999",
            "cpf": "12345678901",
            "matricula": "A12345",
            "plano": "Premium",
            "mensalidade": "129,90",
            "data_matricula": "15/02/2026",
            "turno": "manha",
            "status": "ativo",
        }
    ]
    return _dict_rows_to_csv(headers, rows), "template_members.csv"


def export_checkins_template_csv() -> tuple[BytesIO, str]:
    headers = ["matricula", "email", "cpf", "data_checkin", "hora", "origem"]
    rows = [
        {
            "matricula": "A12345",
            "email": "joao@example.com",
            "cpf": "12345678901",
            "data_checkin": "15/02/2026",
            "hora": "18:30",
            "origem": "catraca",
        }
    ]
    return _dict_rows_to_csv(headers, rows), "template_checkins.csv"


def _dict_rows_to_csv(headers: list[str], rows: list[dict[str, str]]) -> BytesIO:
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    payload = stream.getvalue().encode("utf-8-sig")
    return BytesIO(payload)
