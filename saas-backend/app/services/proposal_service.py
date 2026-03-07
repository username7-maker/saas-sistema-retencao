from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Lead, NurturingSequence
from app.schemas.public_diagnosis import PublicProposalRequest
from app.utils.email import send_email_with_attachment

SETUP_FEE = Decimal("10000")
MONTHLY_FEE = Decimal("2500")


def recommended_plan(total_members: int) -> str:
    if total_members < 300:
        return "starter"
    if total_members <= 800:
        return "growth"
    return "pro"


def proposal_financials(payload: PublicProposalRequest) -> dict:
    at_risk_total = payload.diagnosed_red + payload.diagnosed_yellow
    avg_fee = Decimal(payload.avg_monthly_fee)
    recovered_members = round(at_risk_total * 0.35)
    preserved_annual_revenue = Decimal(recovered_members) * avg_fee * Decimal("12")
    total_investment_12m = SETUP_FEE + (MONTHLY_FEE * Decimal("12"))

    daily_preserved = preserved_annual_revenue / Decimal("365") if preserved_annual_revenue > 0 else Decimal("0")
    if daily_preserved > 0:
        payback_days = float((total_investment_12m / daily_preserved).quantize(Decimal("0.01")))
    else:
        payback_days = 0.0

    roi_12m_pct = (
        float(((preserved_annual_revenue - total_investment_12m) / total_investment_12m * Decimal("100")).quantize(Decimal("0.01")))
        if total_investment_12m > 0
        else 0.0
    )

    return {
        "plan": recommended_plan(payload.total_members),
        "at_risk_total": at_risk_total,
        "mrr_at_risk": float(Decimal(at_risk_total) * avg_fee),
        "annual_loss_projection": float(Decimal(at_risk_total) * avg_fee * Decimal("12")),
        "estimated_recovered_members": recovered_members,
        "estimated_preserved_annual_revenue": float(preserved_annual_revenue),
        "total_investment_12m": float(total_investment_12m),
        "payback_days": payback_days,
        "roi_12m_pct": roi_12m_pct,
        "setup_fee": float(SETUP_FEE),
        "monthly_fee": float(MONTHLY_FEE),
    }


def generate_proposal_pdf(payload: PublicProposalRequest) -> tuple[bytes, str]:
    values = proposal_financials(payload)
    filename = f"proposta_ai_gym_os_{date.today().isoformat()}.pdf"

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    def write_line(text: str, *, step: int = 16, size: int = 11, bold: bool = False) -> None:
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        pdf.setFont(font, size)
        pdf.drawString(40, y, text[:130])
        y -= step
        if y < 60:
            pdf.showPage()
            y = height - 50

    write_line("Proposta Personalizada - AI GYM OS", size=18, bold=True, step=24)
    write_line(f"Academia: {payload.gym_name}", bold=True)
    write_line(f"Responsavel: {payload.prospect_name}")
    write_line(f"Data: {datetime.now(tz=timezone.utc).strftime('%d/%m/%Y')}", step=20)

    write_line("1) O Problema", bold=True, size=14, step=20)
    write_line(f"- Alunos em risco vermelho: {payload.diagnosed_red}")
    write_line(f"- Alunos em risco amarelo: {payload.diagnosed_yellow}")
    write_line(f"- MRR em risco: R$ {values['mrr_at_risk']:,.2f}")
    write_line(f"- Projecao de perda anual: R$ {values['annual_loss_projection']:,.2f}", step=20)

    write_line("2) A Solucao", bold=True, size=14, step=20)
    write_line("- Motor de retencao preditiva com alertas diarios")
    write_line("- Automacao de contato e tarefas para equipe")
    write_line("- Dashboard de BI com foco em MRR, churn e recuperacao", step=20)

    write_line("3) ROI Estimado (12 meses)", bold=True, size=14, step=20)
    write_line(f"- Alunos recuperados (estimativa 35%): {values['estimated_recovered_members']}")
    write_line(f"- Receita anual preservada: R$ {values['estimated_preserved_annual_revenue']:,.2f}")
    write_line(f"- Investimento 12 meses: R$ {values['total_investment_12m']:,.2f}")
    write_line(f"- Payback estimado: {values['payback_days']:.2f} dias")
    write_line(f"- ROI em 12 meses: {values['roi_12m_pct']:.2f}%", step=20)

    write_line("4) Plano Recomendado", bold=True, size=14, step=20)
    write_line(f"- Plano sugerido: {str(values['plan']).upper()}")
    write_line(f"- Setup: R$ {values['setup_fee']:,.2f}")
    write_line(f"- Mensalidade: R$ {values['monthly_fee']:,.2f}", step=20)

    write_line("5) Proximo Passo", bold=True, size=14, step=20)
    write_line(f"- Agenda para demo: {settings.public_booking_url}")
    write_line("- Assinatura digital: _________________________________")

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue(), filename


def send_proposal_email_if_needed(payload: PublicProposalRequest, pdf_bytes: bytes, filename: str) -> bool:
    if not payload.email:
        return False
    return send_email_with_attachment(
        to_email=payload.email,
        subject="Sua proposta personalizada - AI GYM OS",
        content=(
            f"Ola {payload.prospect_name},\n\n"
            "Segue em anexo sua proposta personalizada com estimativa de ROI e plano recomendado."
        ),
        filename=filename,
        attachment_bytes=pdf_bytes,
    )


def hydrate_proposal_from_lead(db: Session, payload: PublicProposalRequest) -> PublicProposalRequest:
    if not payload.lead_id:
        return payload

    sequence = db.scalar(
        select(NurturingSequence)
        .where(NurturingSequence.lead_id == payload.lead_id)
        .order_by(NurturingSequence.created_at.desc())
        .limit(1)
    )
    if not sequence or not isinstance(sequence.diagnosis_data, dict):
        return payload

    diagnosis = dict(sequence.diagnosis_data)
    updates: dict[str, object] = {}

    if payload.diagnosed_red == 0 and diagnosis.get("red_total") is not None:
        updates["diagnosed_red"] = int(diagnosis["red_total"])
    if payload.diagnosed_yellow == 0 and diagnosis.get("yellow_total") is not None:
        updates["diagnosed_yellow"] = int(diagnosis["yellow_total"])
    if diagnosis.get("gym_name"):
        updates["gym_name"] = payload.gym_name or str(diagnosis["gym_name"])
    if diagnosis.get("total_members") is not None:
        updates["total_members"] = payload.total_members or int(diagnosis["total_members"])
    if diagnosis.get("avg_monthly_fee") is not None:
        current_avg = Decimal(payload.avg_monthly_fee)
        updates["avg_monthly_fee"] = current_avg if current_avg > 0 else Decimal(str(diagnosis["avg_monthly_fee"]))
    if sequence.prospect_name and not payload.prospect_name.strip():
        updates["prospect_name"] = sequence.prospect_name
    if sequence.prospect_email and not payload.email:
        updates["email"] = sequence.prospect_email

    if not updates:
        return payload
    return payload.model_copy(update=updates)


def generate_and_send_for_lead(db: Session, lead_id) -> dict:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise ValueError("Lead nao encontrado para gerar proposta")

    sequence = db.scalar(
        select(NurturingSequence)
        .where(NurturingSequence.lead_id == lead_id)
        .order_by(NurturingSequence.created_at.desc())
        .limit(1)
    )
    diagnosis = dict(sequence.diagnosis_data or {}) if sequence and isinstance(sequence.diagnosis_data, dict) else {}

    payload = PublicProposalRequest(
        lead_id=lead.id,
        prospect_name=lead.full_name,
        gym_name=_infer_gym_name(lead, diagnosis),
        total_members=int(diagnosis.get("total_members") or 1),
        avg_monthly_fee=Decimal(str(diagnosis.get("avg_monthly_fee") or "0")),
        diagnosed_red=int(diagnosis.get("red_total") or 0),
        diagnosed_yellow=int(diagnosis.get("yellow_total") or 0),
        email=lead.email,
    )
    hydrated = hydrate_proposal_from_lead(db, payload)
    pdf_bytes, filename = generate_proposal_pdf(hydrated)
    emailed = send_proposal_email_if_needed(hydrated, pdf_bytes, filename)
    return {
        "payload": hydrated,
        "filename": filename,
        "emailed": emailed,
        "pdf_bytes": pdf_bytes,
    }


def _infer_gym_name(lead: Lead, diagnosis: dict) -> str:
    gym_name = str(diagnosis.get("gym_name") or "").strip()
    if gym_name:
        return gym_name

    for item in lead.notes or []:
        if isinstance(item, dict):
            candidate = str(item.get("gym_name") or "").strip()
            if candidate:
                return candidate
    return lead.full_name
