from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, status
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    BodyCompositionEvaluation,
    Checkin,
    Lead,
    Member,
    MemberConsentRecord,
    MemberConstraints,
    MemberStatus,
    MessageLog,
    NPSResponse,
    RiskAlert,
    Task,
)

_LGPD_REDACTED_TEXT = "[redacted-by-lgpd]"


def _get_member_or_404(db: Session, member_id: UUID, gym_id: UUID) -> Member:
    member = db.scalar(
        select(Member).where(
            Member.id == member_id,
            Member.gym_id == gym_id,
            Member.deleted_at.is_(None),
        )
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")
    return member


def export_member_pdf(db: Session, member_id: UUID, gym_id: UUID) -> tuple[BytesIO, str]:
    member = _get_member_or_404(db, member_id, gym_id)

    checkins = db.scalars(
        select(Checkin).where(Checkin.member_id == member_id).order_by(Checkin.checkin_at.desc()).limit(200)
    ).all()
    nps_items = db.scalars(
        select(NPSResponse).where(NPSResponse.member_id == member_id).order_by(NPSResponse.response_date.desc()).limit(50)
    ).all()
    tasks = db.scalars(select(Task).where(Task.member_id == member_id).order_by(Task.created_at.desc()).limit(100)).all()
    risk_alerts = db.scalars(
        select(RiskAlert).where(RiskAlert.member_id == member_id).order_by(RiskAlert.created_at.desc()).limit(100)
    ).all()
    audit_logs = db.scalars(
        select(AuditLog).where(AuditLog.member_id == member_id).order_by(AuditLog.created_at.desc()).limit(150)
    ).all()
    message_logs = db.scalars(
        select(MessageLog).where(MessageLog.member_id == member_id).order_by(MessageLog.created_at.desc()).limit(100)
    ).all()
    body_composition = db.scalars(
        select(BodyCompositionEvaluation)
        .where(BodyCompositionEvaluation.member_id == member_id)
        .order_by(BodyCompositionEvaluation.evaluation_date.desc(), BodyCompositionEvaluation.created_at.desc())
        .limit(30)
    ).all()
    converted_lead = db.scalar(
        select(Lead).where(
            Lead.converted_member_id == member_id,
            Lead.gym_id == gym_id,
            Lead.deleted_at.is_(None),
        )
    )
    member_constraints = db.scalar(
        select(MemberConstraints).where(
            MemberConstraints.member_id == member_id,
            MemberConstraints.gym_id == gym_id,
            MemberConstraints.deleted_at.is_(None),
        )
    )
    consent_records = db.scalars(
        select(MemberConsentRecord)
        .where(MemberConsentRecord.member_id == member_id, MemberConsentRecord.gym_id == gym_id)
        .order_by(MemberConsentRecord.created_at.desc())
        .limit(100)
    ).all()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    line_height = 18

    def write_line(text: str) -> None:
        nonlocal y
        pdf.drawString(40, y, text[:120])
        y -= line_height
        if y < 60:
            pdf.showPage()
            y = 800

    write_line("AI GYM OS - Exportacao LGPD")
    write_line(f"Gerado em: {datetime.now(tz=timezone.utc).isoformat()}")
    write_line("")
    write_line(f"Membro: {member.full_name}")
    write_line(f"Email: {member.email or '-'}")
    write_line(f"Telefone: {member.phone or '-'}")
    write_line(f"Plano: {member.plan_name}")
    write_line(f"Valor mensal: R$ {member.monthly_fee}")
    write_line(f"Status: {member.status.value}")
    write_line(f"Score de risco: {member.risk_score} ({member.risk_level.value})")
    write_line("")
    if converted_lead:
        write_line("Lead convertido relacionado:")
        write_line(f"Nome: {converted_lead.full_name}")
        write_line(f"Email: {converted_lead.email or '-'}")
        write_line(f"Telefone: {converted_lead.phone or '-'}")
        write_line(f"Origem: {converted_lead.source} | Stage: {converted_lead.stage.value}")
        write_line("")
    if member_constraints:
        write_line("Restricoes e contexto do aluno:")
        write_line(f"Condicoes medicas: {member_constraints.medical_conditions or '-'}")
        write_line(f"Lesoes: {member_constraints.injuries or '-'}")
        write_line(f"Medicacoes: {member_constraints.medications or '-'}")
        write_line(f"Contraindicacoes: {member_constraints.contraindications or '-'}")
        write_line(f"Notas: {member_constraints.notes or '-'}")
        write_line("")
    write_line(f"Total de consentimentos/termos exportados: {len(consent_records)}")
    for idx, consent in enumerate(consent_records[:30], start=1):
        write_line(
            f"{idx}. {consent.created_at.isoformat()} | tipo={consent.consent_type} | status={consent.status} | fonte={consent.source}"
        )
        write_line(
            f"   documento={consent.document_title or '-'} | versao={consent.document_version or '-'} | expira={consent.expires_at.isoformat() if consent.expires_at else '-'}"
        )
    write_line("")
    write_line(f"Total de check-ins exportados: {len(checkins)}")
    for idx, checkin in enumerate(checkins[:30], start=1):
        write_line(f"{idx}. {checkin.checkin_at.isoformat()} - origem: {checkin.source.value}")
    write_line("")
    write_line(f"Total de respostas NPS exportadas: {len(nps_items)}")
    for idx, nps in enumerate(nps_items[:20], start=1):
        write_line(
            f"{idx}. {nps.response_date.isoformat()} | score={nps.score} | sentimento={nps.sentiment.value}"
        )
        if nps.comment:
            write_line(f"   comentario: {nps.comment}")
    write_line("")
    write_line(f"Total de tasks exportadas: {len(tasks)}")
    for idx, task in enumerate(tasks[:25], start=1):
        write_line(
            f"{idx}. {task.created_at.isoformat()} | {task.title} | status={task.status.value} | prioridade={task.priority.value}"
        )
    write_line("")
    write_line(f"Total de alertas de risco exportados: {len(risk_alerts)}")
    for idx, alert in enumerate(risk_alerts[:25], start=1):
        write_line(
            f"{idx}. {alert.created_at.isoformat()} | score={alert.score} | nivel={alert.level.value} | resolvido={alert.resolved}"
        )
    write_line("")
    write_line(f"Total de logs de mensagem exportados: {len(message_logs)}")
    for idx, log in enumerate(message_logs[:20], start=1):
        write_line(
            f"{idx}. {log.created_at.isoformat()} | canal={log.channel} | status={log.status} | destino={log.recipient}"
        )
        write_line(f"   conteudo: {log.content}")
    write_line("")
    write_line(f"Total de bioimpedancias exportadas: {len(body_composition)}")
    for idx, evaluation in enumerate(body_composition[:10], start=1):
        write_line(
            f"{idx}. {evaluation.evaluation_date.isoformat()} | peso={evaluation.weight_kg or '-'} | gordura%={evaluation.body_fat_percent or '-'} | musculo={evaluation.muscle_mass_kg or '-'}"
        )
        if evaluation.notes:
            write_line(f"   notas: {evaluation.notes}")
    write_line("")
    write_line(f"Total de logs de auditoria exportados: {len(audit_logs)}")
    for idx, log in enumerate(audit_logs[:40], start=1):
        write_line(f"{idx}. {log.created_at.isoformat()} | {log.action} | entidade={log.entity}")

    pdf.save()
    buffer.seek(0)
    filename = f"lgpd_member_{member_id}.pdf"
    return buffer, filename


def anonymize_member(db: Session, member_id: UUID, gym_id: UUID) -> Member:
    member = _get_member_or_404(db, member_id, gym_id)
    timestamp = datetime.now(tz=timezone.utc)
    stamp = timestamp.isoformat()
    member_tag = f"anon-{str(member.id)[:8]}"

    _anonymize_converted_lead(db, member_id, gym_id, member_tag, stamp)
    _redact_message_logs(db, member_id, member_tag, stamp)
    _redact_member_constraints(db, member_id, gym_id, stamp)
    _redact_consent_records(db, member_id, gym_id, stamp)
    _redact_body_composition_records(db, member_id, stamp)
    _redact_nps_free_text(db, member_id, stamp)

    member.full_name = member_tag
    member.email = None
    member.phone = None
    member.cpf_encrypted = None
    member.extra_data = {"anonymized_at": stamp}
    member.status = MemberStatus.CANCELLED
    member.deleted_at = timestamp
    db.add(member)
    return member


def _anonymize_converted_lead(db: Session, member_id: UUID, gym_id: UUID, member_tag: str, stamp: str) -> None:
    leads = db.scalars(
        select(Lead).where(
            Lead.converted_member_id == member_id,
            Lead.gym_id == gym_id,
            Lead.deleted_at.is_(None),
        )
    ).all()
    for lead in leads:
        lead.full_name = f"{member_tag}-lead"
        lead.email = None
        lead.phone = None
        lead.notes = []
        lead.lost_reason = None
        db.add(lead)


def _redact_consent_records(db: Session, member_id: UUID, gym_id: UUID, stamp: str) -> None:
    records = db.scalars(
        select(MemberConsentRecord).where(
            MemberConsentRecord.member_id == member_id,
            MemberConsentRecord.gym_id == gym_id,
        )
    ).all()
    for record in records:
        record.evidence_ref = None
        record.notes = _LGPD_REDACTED_TEXT if record.notes else None
        record.extra_data = {"anonymized_at": stamp, "redacted": True}
        db.add(record)


def _redact_message_logs(db: Session, member_id: UUID, member_tag: str, stamp: str) -> None:
    message_logs = db.scalars(select(MessageLog).where(MessageLog.member_id == member_id)).all()
    for log in message_logs:
        log.recipient = f"{member_tag}-message"
        log.content = _LGPD_REDACTED_TEXT
        log.error_detail = _LGPD_REDACTED_TEXT if log.error_detail else None
        log.extra_data = {
            "anonymized_at": stamp,
            "redacted": True,
            "delivery_kind": (log.extra_data or {}).get("delivery_kind"),
            "instance_source": (log.extra_data or {}).get("instance_source"),
            "response_status": (log.extra_data or {}).get("response_status"),
        }
        db.add(log)


def _redact_member_constraints(db: Session, member_id: UUID, gym_id: UUID, stamp: str) -> None:
    constraint = db.scalar(
        select(MemberConstraints).where(
            MemberConstraints.member_id == member_id,
            MemberConstraints.gym_id == gym_id,
            MemberConstraints.deleted_at.is_(None),
        )
    )
    if constraint is None:
        return
    constraint.medical_conditions = None
    constraint.injuries = None
    constraint.medications = None
    constraint.contraindications = None
    constraint.notes = None
    constraint.restrictions = {"anonymized_at": stamp, "redacted": True}
    db.add(constraint)


def _redact_body_composition_records(db: Session, member_id: UUID, stamp: str) -> None:
    evaluations = db.scalars(select(BodyCompositionEvaluation).where(BodyCompositionEvaluation.member_id == member_id)).all()
    for evaluation in evaluations:
        evaluation.notes = None
        evaluation.report_file_url = None
        evaluation.raw_ocr_text = None
        evaluation.ocr_source_file_ref = None
        evaluation.ai_coach_summary = None
        evaluation.ai_member_friendly_summary = None
        evaluation.actuar_external_id = None
        evaluation.actuar_last_error = None
        evaluation.sync_last_error_message = None
        flags = list(evaluation.data_quality_flags_json or [])
        if "lgpd_redacted" not in flags:
            flags.append("lgpd_redacted")
        evaluation.data_quality_flags_json = flags
        db.add(evaluation)


def _redact_nps_free_text(db: Session, member_id: UUID, stamp: str) -> None:
    responses = db.scalars(select(NPSResponse).where(NPSResponse.member_id == member_id)).all()
    for response in responses:
        response.comment = None
        response.sentiment_summary = None
        extra_data = dict(response.extra_data or {})
        extra_data["anonymized_at"] = stamp
        extra_data["redacted"] = True
        response.extra_data = extra_data
        db.add(response)
