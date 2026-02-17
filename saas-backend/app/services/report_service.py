from datetime import date, datetime, timezone
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RoleEnum, User
from app.services.dashboard_service import (
    get_commercial_dashboard,
    get_executive_dashboard,
    get_financial_dashboard,
    get_operational_dashboard,
    get_retention_dashboard,
)
from app.utils.email import send_email_with_attachment


DashboardReportType = str
ALLOWED_DASHBOARD_REPORTS = {"executive", "operational", "commercial", "financial", "retention", "consolidated"}


def generate_dashboard_pdf(db: Session, dashboard: DashboardReportType) -> tuple[BytesIO, str]:
    dashboard_key = dashboard.strip().lower()
    if dashboard_key not in ALLOWED_DASHBOARD_REPORTS:
        raise ValueError(f"Dashboard invalido: {dashboard}")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    line_height = 16

    def write_line(text: str, *, spacer: bool = False) -> None:
        nonlocal y
        pdf.drawString(40, y, text[:120])
        y -= line_height
        if spacer:
            y -= 4
        if y < 60:
            pdf.showPage()
            y = 800

    write_line(f"AI GYM OS - Relatorio {dashboard_key.upper()}")
    write_line(f"Gerado em: {datetime.now(tz=timezone.utc).isoformat()}", spacer=True)

    if dashboard_key == "executive":
        _write_executive(write_line, db)
    elif dashboard_key == "operational":
        _write_operational(write_line, db)
    elif dashboard_key == "commercial":
        _write_commercial(write_line, db)
    elif dashboard_key == "financial":
        _write_financial(write_line, db)
    elif dashboard_key == "retention":
        _write_retention(write_line, db)
    else:
        _write_executive(write_line, db)
        _write_operational(write_line, db)
        _write_commercial(write_line, db)
        _write_financial(write_line, db)
        _write_retention(write_line, db)

    pdf.save()
    buffer.seek(0)
    filename = f"report_{dashboard_key}_{date.today().isoformat()}.pdf"
    return buffer, filename


def send_monthly_reports(db: Session) -> dict[str, int]:
    buffer, filename = generate_dashboard_pdf(db, "consolidated")
    attachment = buffer.getvalue()
    leadership = db.scalars(
        select(User).where(
            User.deleted_at.is_(None),
            User.is_active.is_(True),
            User.role.in_([RoleEnum.OWNER, RoleEnum.MANAGER]),
        )
    ).all()

    sent = 0
    failed = 0
    for user in leadership:
        ok = send_email_with_attachment(
            user.email,
            "AI GYM OS - Relatorio Mensal Consolidado",
            "Segue em anexo o relatorio mensal consolidado da sua academia.",
            filename=filename,
            attachment_bytes=attachment,
        )
        if ok:
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed, "total_recipients": len(leadership)}


def _write_executive(write_line, db: Session) -> None:  # type: ignore[no-untyped-def]
    data = get_executive_dashboard(db)
    write_line(" ")
    write_line("[Executivo]")
    write_line(f"- Total de alunos: {data.total_members}")
    write_line(f"- Alunos ativos: {data.active_members}")
    write_line(f"- MRR: R$ {data.mrr:.2f}")
    write_line(f"- Churn: {data.churn_rate:.2f}%")
    write_line(f"- NPS medio: {data.nps_avg:.2f}")
    write_line(
        f"- Risco (G/Y/R): {data.risk_distribution['green']}/{data.risk_distribution['yellow']}/{data.risk_distribution['red']}",
        spacer=True,
    )


def _write_operational(write_line, db: Session) -> None:  # type: ignore[no-untyped-def]
    data = get_operational_dashboard(db, page=1, page_size=10)
    write_line("[Operacional]")
    write_line(f"- Check-ins ultima hora: {data['realtime_checkins']}")
    write_line(f"- Inativos 7+ dias: {data['inactive_7d_total']}")
    top_items = data["inactive_7d_items"][:5]
    if top_items:
        write_line("- Top inativos:")
        for item in top_items:
            last_checkin = item.last_checkin_at.date().isoformat() if item.last_checkin_at else "sem registro"
            write_line(f"  - {item.full_name} | risco={item.risk_level.value} | ultimo={last_checkin}")
    write_line(" ", spacer=True)


def _write_commercial(write_line, db: Session) -> None:  # type: ignore[no-untyped-def]
    data = get_commercial_dashboard(db)
    write_line("[Comercial]")
    write_line(f"- CAC: R$ {data['cac']:.2f}")
    write_line("- Pipeline:")
    for stage, total in sorted(data["pipeline"].items()):
        write_line(f"  - {stage}: {total}")
    write_line("- Conversao por origem:")
    for row in data["conversion_by_source"][:5]:
        write_line(f"  - {row.source}: {row.conversion_rate:.2f}% ({row.won}/{row.total})")
    write_line(" ", spacer=True)


def _write_financial(write_line, db: Session) -> None:  # type: ignore[no-untyped-def]
    data = get_financial_dashboard(db)
    write_line("[Financeiro]")
    write_line(f"- Inadimplencia: {data['delinquency_rate']:.2f}%")
    latest_revenue = data["monthly_revenue"][-1].value if data["monthly_revenue"] else 0
    write_line(f"- Receita mensal atual: R$ {latest_revenue:.2f}")
    write_line("- Projecoes:")
    for projection in data["projections"]:
        write_line(f"  - {projection.horizon_months} meses: R$ {projection.projected_revenue:.2f}")
    write_line(" ", spacer=True)


def _write_retention(write_line, db: Session) -> None:  # type: ignore[no-untyped-def]
    data = get_retention_dashboard(db, red_page=1, yellow_page=1, page_size=10)
    write_line("[Retencao]")
    write_line(f"- Vermelho: {data['red']['total']}")
    write_line(f"- Amarelo: {data['yellow']['total']}")
    top_red = data["red"]["items"][:5]
    if top_red:
        write_line("- Top risco vermelho:")
        for member in top_red:
            write_line(f"  - {member.full_name} | score={member.risk_score} | plano={member.plan_name}")
    write_line(" ", spacer=True)
