from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Member
from app.models.body_composition import BodyCompositionEvaluation
from app.services.body_composition_actuar_sync_service import get_body_composition_evaluation_or_404
from app.services.body_composition_ai_service import build_body_composition_member_summary
from app.services.body_composition_report_service import (
    build_body_composition_premium_pdf_payload,
    build_body_composition_report_read,
)
from app.services.kommo_service import KommoHandoffResult, KommoSalesbotOutboundResult, handoff_member_to_kommo, send_member_message_via_kommo_salesbot
from app.services.member_service import get_member_or_404
from app.services.premium_report_service import render_premium_report_pdf
from app.services.public_report_link_service import create_body_composition_report_public_url
from app.services.whatsapp_service import get_gym_instance, send_whatsapp_document_sync


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
    previous_evaluation = get_previous_body_composition_evaluation(
        db,
        gym_id=gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )
    pdf_bytes, filename = generate_body_composition_technical_pdf(member, evaluation, previous_evaluation)
    return send_whatsapp_document_sync(
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


def send_body_composition_kommo_handoff(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
) -> KommoHandoffResult:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    evaluation = get_body_composition_evaluation_or_404(
        db,
        gym_id=gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )

    first_name = (member.full_name or "").split(" ")[0] or "aluno"
    member_summary = build_body_composition_member_summary(evaluation, member_first_name=first_name)
    coach_summary = " ".join((evaluation.ai_coach_summary or "").split()).strip()
    risk_flags = evaluation.ai_risk_flags_json or []
    training_focus = evaluation.ai_training_focus_json or {}
    suggested_focuses = [str(item).strip() for item in (training_focus.get("suggested_focuses") or []) if str(item).strip()]

    summary_lines = [
        f"Bioimpedancia pronta de {member.full_name}.",
        member_summary.strip(),
    ]
    if coach_summary:
        summary_lines.extend(["", "Resumo para o coach:", coach_summary])
    if risk_flags:
        summary_lines.extend(["", "Alertas principais:"] + [f"- {flag}" for flag in risk_flags[:4]])
    if suggested_focuses:
        summary_lines.extend(["", "Direcao inicial sugerida:"] + [f"- {focus}" for focus in suggested_focuses[:4]])

    return handoff_member_to_kommo(
        db,
        gym_id=gym_id,
        member=member,
        title=f"Bioimpedancia pronta - {member.full_name}",
        summary="\n".join(summary_lines).strip()[:2400],
        source="body_composition",
        ai_gym_profile_url=_build_member_profile_url(member.id),
        due_in_hours=12,
    )


def send_body_composition_kommo_salesbot(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
    pdf_kind: str = "technical",
    pdf_delivery_mode: str = "native_file_required",
) -> KommoSalesbotOutboundResult:
    member = get_member_or_404(db, member_id, gym_id=gym_id)
    evaluation = get_body_composition_evaluation_or_404(
        db,
        gym_id=gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )
    message = build_body_composition_whatsapp_message(member, evaluation)
    previous_evaluation = get_previous_body_composition_evaluation(
        db,
        gym_id=gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )
    pdf_bytes, pdf_filename = (
        generate_body_composition_technical_pdf(member, evaluation, previous_evaluation)
        if pdf_kind == "technical"
        else generate_body_composition_pdf(member, evaluation, previous_evaluation)
    )
    pdf_url = None
    if pdf_delivery_mode in {"native_file_preferred", "link_only"}:
        pdf_url = create_body_composition_report_public_url(
            gym_id=gym_id,
            member_id=member_id,
            evaluation_id=evaluation_id,
            pdf_kind=pdf_kind,
        )
    return send_member_message_via_kommo_salesbot(
        db,
        gym_id=gym_id,
        member=member,
        domain="body_composition",
        message_text=message,
        source_type="body_composition",
        source_id=evaluation_id,
        pdf_url=pdf_url,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_filename,
        pdf_delivery_mode=pdf_delivery_mode,
        title=f"Bioimpedancia pronta - {member.full_name}",
    )


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


def get_previous_body_composition_evaluation(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    evaluation_id: UUID,
) -> BodyCompositionEvaluation | None:
    return db.scalar(
        select(BodyCompositionEvaluation)
        .where(
            BodyCompositionEvaluation.gym_id == gym_id,
            BodyCompositionEvaluation.member_id == member_id,
            BodyCompositionEvaluation.id != evaluation_id,
        )
        .order_by(desc(BodyCompositionEvaluation.evaluation_date), desc(BodyCompositionEvaluation.created_at))
        .limit(1)
    )


def generate_body_composition_pdf(
    member: Member,
    evaluation: BodyCompositionEvaluation,
    previous_evaluation: BodyCompositionEvaluation | None = None,
) -> tuple[bytes, str]:
    filename = _build_filename(member, evaluation)
    history = [item for item in (previous_evaluation, evaluation) if item is not None]
    report = build_body_composition_report_payload(member, evaluation, history=history)
    premium_payload = build_body_composition_premium_pdf_payload(report, technical=False)
    return render_premium_report_pdf(premium_payload), filename


def generate_body_composition_technical_pdf(
    member: Member,
    evaluation: BodyCompositionEvaluation,
    previous_evaluation: BodyCompositionEvaluation | None = None,
) -> tuple[bytes, str]:
    filename = _build_filename(member, evaluation, technical=True)
    history = [item for item in (previous_evaluation, evaluation) if item is not None]
    report = build_body_composition_report_payload(member, evaluation, history=history)
    premium_payload = build_body_composition_premium_pdf_payload(report, technical=True)
    return render_premium_report_pdf(premium_payload), filename


def build_body_composition_report_payload(
    member: Member,
    evaluation: BodyCompositionEvaluation,
    *,
    history: list[BodyCompositionEvaluation] | None = None,
):
    report_history = list(history or [evaluation])
    if all(item.id != evaluation.id for item in report_history):
        report_history.append(evaluation)
    return build_body_composition_report_read(member, evaluation, history=report_history)


def _build_filename(member: Member, evaluation: BodyCompositionEvaluation, *, technical: bool = False) -> str:
    safe_name = "".join(ch.lower() if ch.isalnum() else "_" for ch in (member.full_name or "aluno")).strip("_")
    safe_name = "_".join(part for part in safe_name.split("_") if part) or "aluno"
    prefix = "bioimpedancia_tecnica" if technical else "bioimpedancia"
    return f"{prefix}_{safe_name}_{evaluation.evaluation_date.isoformat()}.pdf"


def _build_member_profile_url(member_id: UUID) -> str | None:
    frontend_url = (settings.frontend_url or "").strip().rstrip("/")
    if not frontend_url:
        return None
    return f"{frontend_url}/assessments/members/{member_id}"
