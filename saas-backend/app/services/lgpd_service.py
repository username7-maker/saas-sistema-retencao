from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, status
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Checkin, Member, MemberStatus, NPSResponse


def export_member_pdf(db: Session, member_id: UUID) -> tuple[BytesIO, str]:
    member = db.scalar(select(Member).where(Member.id == member_id, Member.deleted_at.is_(None)))
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")

    checkins = db.scalars(
        select(Checkin).where(Checkin.member_id == member_id).order_by(Checkin.checkin_at.desc()).limit(200)
    ).all()
    nps_items = db.scalars(
        select(NPSResponse).where(NPSResponse.member_id == member_id).order_by(NPSResponse.response_date.desc()).limit(50)
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
    write_line(f"Status: {member.status.value}")
    write_line(f"Score de risco: {member.risk_score} ({member.risk_level.value})")
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

    pdf.save()
    buffer.seek(0)
    filename = f"lgpd_member_{member_id}.pdf"
    return buffer, filename


def anonymize_member(db: Session, member_id: UUID) -> Member:
    member = db.scalar(select(Member).where(Member.id == member_id, Member.deleted_at.is_(None)))
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")

    member.full_name = f"anon-{str(member.id)[:8]}"
    member.email = None
    member.phone = None
    member.cpf_encrypted = None
    member.extra_data = {"anonymized_at": datetime.now(tz=timezone.utc).isoformat()}
    member.status = MemberStatus.CANCELLED
    member.deleted_at = datetime.now(tz=timezone.utc)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member
