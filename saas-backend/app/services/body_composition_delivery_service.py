from __future__ import annotations

from io import BytesIO
from textwrap import wrap
from uuid import UUID

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models import Member
from app.models.body_composition import BodyCompositionEvaluation
from app.services.body_composition_actuar_sync_service import get_body_composition_evaluation_or_404
from app.services.body_composition_ai_service import build_body_composition_member_summary
from app.services.member_service import get_member_or_404
from app.services.whatsapp_service import get_gym_instance, send_whatsapp_document_sync

_KEY_METRICS = (
    ("Peso", "weight_kg", "kg"),
    ("Gordura corporal", "body_fat_percent", "%"),
    ("Massa muscular", "muscle_mass_kg", "kg"),
    ("Musculo esqueletico", "skeletal_muscle_kg", "kg"),
    ("Relacao cintura-quadril", "waist_hip_ratio", ""),
    ("Gordura visceral", "visceral_fat_level", ""),
    ("IMC", "bmi", ""),
    ("Health score", "health_score", ""),
)


def send_body_composition_whatsapp_summary(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
):
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    evaluation = get_body_composition_evaluation_or_404(
        db,
        gym_id=gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )
    instance = get_gym_instance(db, gym_id)
    if not member.phone:
        raise ValueError("Aluno sem telefone cadastrado para envio por WhatsApp.")

    message = build_body_composition_whatsapp_message(member, evaluation)
    pdf_bytes, filename = generate_body_composition_pdf(member, evaluation)
    log = send_whatsapp_document_sync(
        db,
        phone=member.phone,
        caption=message,
        file_bytes=pdf_bytes,
        filename=filename,
        mime_type="application/pdf",
        instance=instance,
        member_id=member.id,
        template_name="body_composition_summary",
        event_type="body_composition_summary_pdf",
    )
    return log


def build_body_composition_whatsapp_message(member: Member, evaluation: BodyCompositionEvaluation) -> str:
    first_name = (member.full_name or "").split(" ")[0] or "Tudo bem"
    summary = build_body_composition_member_summary(evaluation, member_first_name=first_name)
    summary = " ".join(summary.split()).strip()
    if len(summary) > 520:
        summary = summary[:517].rstrip(" ,;:-") + "..."

    return (
        f"Oi {first_name}! Separei o resumo da sua bioimpedancia em PDF. "
        f"{summary} Se quiser, na proxima conversa a gente transforma isso em metas simples e objetivas para a sua rotina."
    )


def generate_body_composition_pdf(member: Member, evaluation: BodyCompositionEvaluation) -> tuple[bytes, str]:
    filename = _build_filename(member, evaluation)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    def write_line(text: str, *, size: int = 11, step: int = 15, bold: bool = False) -> None:
        nonlocal y
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        for line in wrap(text, width=92) or [""]:
            pdf.drawString(40, y, line[:120])
            y -= step
            if y < 60:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)

    write_line("Resumo de Bioimpedancia - AI GYM OS", size=18, step=22, bold=True)
    write_line(f"Aluno: {member.full_name}", bold=True)
    write_line(f"Data do exame: {evaluation.evaluation_date.strftime('%d/%m/%Y')}")
    write_line("", step=10)

    write_line("Resumo para o aluno", size=14, step=18, bold=True)
    write_line(build_body_composition_member_summary(evaluation, member_first_name=(member.full_name or "").split(" ")[0]))
    write_line("", step=10)

    write_line("Principais alertas", size=14, step=18, bold=True)
    flags = evaluation.ai_risk_flags_json or []
    if flags:
        for flag in flags[:4]:
            write_line(f"- {flag}")
    else:
        write_line("- Sem alertas estruturados relevantes neste exame.")
    write_line("", step=10)

    write_line("Direcao inicial sugerida", size=14, step=18, bold=True)
    training_focus = evaluation.ai_training_focus_json or {}
    write_line(f"Objetivo principal: {_format_goal(training_focus.get('primary_goal'))}")
    write_line(f"Objetivo secundario: {_format_goal(training_focus.get('secondary_goal'))}")
    for item in (training_focus.get("suggested_focuses") or [])[:4]:
        write_line(f"- {str(item)}")
    write_line("", step=10)

    write_line("Numeros principais do exame", size=14, step=18, bold=True)
    for label, field_name, unit in _KEY_METRICS:
        value = getattr(evaluation, field_name, None)
        if value is None:
            continue
        write_line(f"- {label}: {_format_metric(value, unit)}")

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue(), filename


def _build_filename(member: Member, evaluation: BodyCompositionEvaluation) -> str:
    safe_name = "".join(ch.lower() if ch.isalnum() else "_" for ch in (member.full_name or "aluno")).strip("_")
    safe_name = "_".join(part for part in safe_name.split("_") if part) or "aluno"
    return f"bioimpedancia_{safe_name}_{evaluation.evaluation_date.isoformat()}.pdf"


def _format_metric(value: object, unit: str) -> str:
    if isinstance(value, float):
        text = f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    else:
        text = str(value).replace(".", ",")
    return f"{text} {unit}".strip()


def _format_goal(value: object) -> str:
    goal = str(value or "").strip()
    labels = {
        "reducao_de_gordura": "Reducao de gordura",
        "ganho_de_massa": "Ganho de massa",
        "melhora_metabolica": "Melhora metabolica",
        "acompanhamento_geral": "Acompanhamento geral",
        "preservacao_de_massa_magra": "Preservacao de massa magra",
        "controle_de_gordura": "Controle de gordura",
    }
    return labels.get(goal, goal.replace("_", " ") if goal else "Acompanhamento geral")
