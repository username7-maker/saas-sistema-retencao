import csv
import io
import re
import traceback
import unicodedata
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from typing import Any
from uuid import UUID

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import DiagnosisError, Lead
from app.services.audit_service import log_audit_event
from app.services.nurturing_service import create_nurturing_sequence
from app.services.whatsapp_service import send_whatsapp_sync
from app.utils.email import send_email_with_attachment

MEMBER_COLUMN_ALIASES = (
    "member_id",
    "aluno_id",
    "id_aluno",
    "matricula",
    "codigo",
    "full_name",
    "name",
    "nome",
    "aluno",
    "member_name",
)
CHECKIN_COLUMN_ALIASES = ("checkin_at", "data_hora", "datetime", "timestamp", "checkin", "data_checkin")
CHECKIN_DATE_COLUMN_ALIASES = ("checkin_date", "data", "date", "data_checkin")
CHECKIN_TIME_COLUMN_ALIASES = ("checkin_time", "hora", "time", "hora_checkin")


def resolve_public_gym_id() -> UUID:
    raw = (settings.public_diag_gym_id or "").strip()
    if not raw:
        raise RuntimeError("PUBLIC_DIAG_GYM_ID nao configurado")
    return UUID(raw)


def classify_member_risk(days_since_last_checkin: int, frequency_drop_pct: float) -> str:
    if days_since_last_checkin > 14 or frequency_drop_pct > 50:
        return "red"
    if 7 <= days_since_last_checkin <= 14 or (25 <= frequency_drop_pct <= 50):
        return "yellow"
    return "green"


def parse_diagnosis_checkins_csv(csv_content: bytes) -> list[dict[str, Any]]:
    text = _decode_csv_text(csv_content)
    reader = csv.DictReader(io.StringIO(text), delimiter=_detect_delimiter(text))
    headers = [_normalize_header(item) for item in (reader.fieldnames or []) if item]
    if not headers:
        raise ValueError("CSV vazio ou sem cabecalho.")

    member_column = _find_column(headers, MEMBER_COLUMN_ALIASES)
    checkin_column = _find_column(headers, CHECKIN_COLUMN_ALIASES)
    checkin_date_column = _find_column(headers, CHECKIN_DATE_COLUMN_ALIASES)
    checkin_time_column = _find_column(headers, CHECKIN_TIME_COLUMN_ALIASES)

    if not member_column:
        raise ValueError(
            "Coluna de aluno nao identificada. Use uma destas: member_id, matricula, nome, full_name."
        )
    if not checkin_column and not checkin_date_column:
        raise ValueError(
            "Coluna de check-in nao identificada. Use checkin_at/data_hora ou data (+ hora opcional)."
        )

    now = datetime.now(tz=timezone.utc)
    grouped_checkins: dict[str, list[datetime]] = {}
    for row_number, row in enumerate(reader, start=2):
        normalized = {_normalize_header(k): (v or "").strip() for k, v in row.items() if k}
        member_key = (normalized.get(member_column) or "").strip()
        if not member_key:
            continue
        grouped_checkins.setdefault(member_key, [])

        raw_datetime = (normalized.get(checkin_column) or "").strip() if checkin_column else ""
        if not raw_datetime and checkin_date_column:
            date_part = (normalized.get(checkin_date_column) or "").strip()
            time_part = (normalized.get(checkin_time_column) or "").strip() if checkin_time_column else ""
            raw_datetime = f"{date_part} {time_part}".strip()

        if not raw_datetime:
            continue

        parsed = _parse_datetime(raw_datetime)
        if not parsed:
            raise ValueError(f"Data/hora invalida na linha {row_number}: '{raw_datetime}'")
        grouped_checkins[member_key].append(parsed)

    if not grouped_checkins:
        raise ValueError("CSV sem check-ins validos.")

    analyzed_members: list[dict[str, Any]] = []
    for member_key, checkins in grouped_checkins.items():
        sorted_checkins = sorted(checkins)
        if sorted_checkins:
            last_checkin = sorted_checkins[-1]
            last_checkin_at = last_checkin.isoformat()
            days_since_last = max(0, (now - last_checkin).days)
            recent_count = sum(1 for dt in sorted_checkins if dt >= now - timedelta(days=28))
            previous_count = sum(1 for dt in sorted_checkins if now - timedelta(days=56) <= dt < now - timedelta(days=28))
            recent_avg = recent_count / 4.0
            previous_avg = previous_count / 4.0
            if previous_avg <= 0:
                drop_pct = 0.0
            else:
                drop_pct = max(0.0, ((previous_avg - recent_avg) / previous_avg) * 100)
        else:
            last_checkin_at = None
            days_since_last = 999
            recent_avg = 0.0
            previous_avg = 0.0
            drop_pct = 100.0

        risk_level = classify_member_risk(days_since_last, drop_pct)
        analyzed_members.append(
            {
                "member_key": member_key,
                "last_checkin_at": last_checkin_at,
                "days_since_last_checkin": days_since_last,
                "recent_weekly_avg": round(recent_avg, 2),
                "previous_weekly_avg": round(previous_avg, 2),
                "frequency_drop_pct": round(drop_pct, 2),
                "risk_level": risk_level,
            }
        )
    return analyzed_members


def compute_diagnosis_kpis(
    *,
    analyzed_members: list[dict[str, Any]],
    total_members: int,
    avg_monthly_fee: Decimal,
) -> dict[str, Any]:
    red = sum(1 for item in analyzed_members if item["risk_level"] == "red")
    yellow = sum(1 for item in analyzed_members if item["risk_level"] == "yellow")
    green = sum(1 for item in analyzed_members if item["risk_level"] == "green")
    at_risk_total = red + yellow

    mrr_at_risk = Decimal(at_risk_total) * avg_monthly_fee
    annual_loss_projection = mrr_at_risk * Decimal("12")
    estimated_recovered_members = round(at_risk_total * 0.35)
    estimated_preserved_annual_revenue = Decimal(estimated_recovered_members) * avg_monthly_fee * Decimal("12")

    return {
        "analyzed_members": len(analyzed_members),
        "total_members": total_members,
        "avg_monthly_fee": float(avg_monthly_fee),
        "green_total": green,
        "yellow_total": yellow,
        "red_total": red,
        "at_risk_total": at_risk_total,
        "mrr_at_risk": float(mrr_at_risk),
        "annual_loss_projection": float(annual_loss_projection),
        "recovery_rate_benchmark": 0.35,
        "estimated_recovered_members": estimated_recovered_members,
        "estimated_preserved_annual_revenue": float(estimated_preserved_annual_revenue),
    }


def generate_diagnosis_pdf(payload: dict[str, Any], kpis: dict[str, Any], top_risk: list[dict[str, Any]]) -> tuple[bytes, str]:
    filename = f"diagnostico_ai_gym_os_{date.today().isoformat()}.pdf"
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    def write_line(text: str, *, step: int = 16, size: int = 11, bold: bool = False) -> None:
        nonlocal y
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(40, y, text[:130])
        y -= step
        if y < 60:
            pdf.showPage()
            y = height - 50

    write_line("Diagnostico Gratuito - AI GYM OS", size=18, bold=True, step=24)
    write_line(f"Academia: {payload['gym_name']}", bold=True)
    write_line(f"Responsavel: {payload['full_name']}")
    write_line(f"Data: {datetime.now(tz=timezone.utc).strftime('%d/%m/%Y')}", step=20)

    write_line("Resumo do diagnostico", bold=True, size=14, step=20)
    write_line(f"- Alunos analisados no CSV: {kpis['analyzed_members']}")
    write_line(f"- Total alunos informado: {kpis['total_members']}")
    write_line(f"- Verde: {kpis['green_total']} | Amarelo: {kpis['yellow_total']} | Vermelho: {kpis['red_total']}")
    write_line(f"- MRR em risco: R$ {kpis['mrr_at_risk']:,.2f}")
    write_line(f"- Projecao de perda anual: R$ {kpis['annual_loss_projection']:,.2f}")
    write_line(f"- Recuperacao estimada (35%): {kpis['estimated_recovered_members']} alunos", step=20)

    write_line("Top alunos em risco (amostra)", bold=True, size=14, step=20)
    for row in top_risk[:10]:
        write_line(
            f"- {row['member_key']} | risco={row['risk_level']} | dias sem check-in={row['days_since_last_checkin']} | queda={row['frequency_drop_pct']}%"
        )

    write_line("Proximo passo", bold=True, size=14, step=20)
    write_line(
        f"- Agende uma call de 15 min para ver o plano personalizado: {settings.public_booking_url}",
        step=20,
    )

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue(), filename


def process_public_diagnosis_background(
    *,
    diagnosis_id: UUID,
    lead_id: UUID,
    payload: dict[str, Any],
    csv_content: bytes,
    requester_ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    db = SessionLocal()
    gym_id: UUID | None = None
    try:
        gym_id = resolve_public_gym_id()
        set_current_gym_id(gym_id)

        analyzed_members = parse_diagnosis_checkins_csv(csv_content)
        avg_monthly_fee = Decimal(str(payload["avg_monthly_fee"]))
        kpis = compute_diagnosis_kpis(
            analyzed_members=analyzed_members,
            total_members=int(payload["total_members"]),
            avg_monthly_fee=avg_monthly_fee,
        )
        sorted_risk = sorted(
            analyzed_members,
            key=lambda item: (item["risk_level"] != "red", -item["days_since_last_checkin"]),
        )

        pdf_bytes, filename = generate_diagnosis_pdf(payload, kpis, sorted_risk)
        email_sent = send_email_with_attachment(
            to_email=payload["email"],
            subject="Seu diagnostico de retencao - AI GYM OS",
            content=(
                f"Ola {payload['full_name']},\n\n"
                "Seu diagnostico foi processado. Segue o relatorio em anexo.\n"
                f"Para ver o plano de acao: {settings.public_booking_url}"
            ),
            filename=filename,
            attachment_bytes=pdf_bytes,
        )
        wa_text = (
            f"Ola {payload['full_name']}! Seu diagnostico ficou pronto: "
            f"{kpis['red_total']} vermelhos, {kpis['yellow_total']} amarelos, "
            f"MRR em risco de R$ {kpis['mrr_at_risk']:,.2f}. "
            f"Agende sua call: {settings.public_booking_url}"
        )
        wa_log = send_whatsapp_sync(
            db,
            phone=payload["whatsapp"],
            message=wa_text,
            template_name="custom",
        )

        lead = db.get(Lead, lead_id)
        if lead:
            notes = list(lead.notes or [])
            notes.append(
                {
                    "type": "public_diagnosis_completed",
                    "diagnosis_id": str(diagnosis_id),
                    "kpis": kpis,
                    "email_sent": email_sent,
                    "whatsapp_status": wa_log.status,
                    "created_at": datetime.now(tz=timezone.utc).isoformat(),
                }
            )
            lead.notes = notes
            db.add(lead)

        create_nurturing_sequence(
            db,
            gym_id=gym_id,
            lead_id=lead_id,
            prospect_email=payload["email"],
            prospect_whatsapp=payload["whatsapp"],
            prospect_name=payload["full_name"],
            diagnosis_data={
                **kpis,
                "diagnosis_id": str(diagnosis_id),
                "gym_name": payload["gym_name"],
            },
        )

        log_audit_event(
            db,
            action="public_diagnosis_completed",
            entity="lead",
            gym_id=gym_id,
            entity_id=lead_id,
            details={"diagnosis_id": str(diagnosis_id), "email": payload["email"], "kpis": kpis},
            ip_address=requester_ip,
            user_agent=user_agent,
        )
        db.commit()
    except Exception as exc:
        traceback_snippet = traceback.format_exc(limit=8)[:4000]
        db.add(
            DiagnosisError(
                gym_id=gym_id,
                prospect_email=payload.get("email", ""),
                prospect_name=payload.get("full_name"),
                endpoint="public_diagnostico",
                error_message=str(exc)[:1000],
                traceback_snippet=traceback_snippet,
                payload={k: v for k, v in payload.items() if k != "csv_content"},
            )
        )

        if lead_id:
            lead = db.get(Lead, lead_id)
            if lead:
                notes = list(lead.notes or [])
                notes.append(
                    {
                        "type": "public_diagnosis_failed",
                        "diagnosis_id": str(diagnosis_id),
                        "error": str(exc)[:300],
                        "created_at": datetime.now(tz=timezone.utc).isoformat(),
                    }
                )
                lead.notes = notes
                db.add(lead)

        log_audit_event(
            db,
            action="public_diagnosis_failed",
            entity="public_diagnosis",
            gym_id=gym_id,
            entity_id=lead_id,
            details={
                "diagnosis_id": str(diagnosis_id),
                "email": payload.get("email"),
                "error": str(exc)[:500],
            },
            ip_address=requester_ip,
            user_agent=user_agent,
        )
        db.commit()
    finally:
        clear_current_gym_id()
        db.close()


def _decode_csv_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _detect_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:10]) or text
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
        return dialect.delimiter
    except csv.Error:
        return ";" if sample.count(";") > sample.count(",") else ","


def _normalize_header(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")


def _find_column(headers: list[str], aliases: tuple[str, ...]) -> str | None:
    for candidate in aliases:
        normalized = _normalize_header(candidate)
        if normalized in headers:
            return normalized
    return None


def _parse_datetime(raw_value: str) -> datetime | None:
    value = (raw_value or "").strip()
    if not value:
        return None

    iso_candidate = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_candidate)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    patterns = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
    )
    for pattern in patterns:
        try:
            parsed = datetime.strptime(value, pattern)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def build_public_diagnosis_payload(
    *,
    full_name: str,
    email: str,
    whatsapp: str,
    gym_name: str,
    total_members: int,
    avg_monthly_fee: Decimal,
) -> dict[str, Any]:
    return {
        "full_name": full_name.strip(),
        "email": email.strip().lower(),
        "whatsapp": re.sub(r"\D+", "", whatsapp),
        "gym_name": gym_name.strip(),
        "total_members": total_members,
        "avg_monthly_fee": float(avg_monthly_fee),
    }


def new_diagnosis_id() -> UUID:
    return uuid.uuid4()
