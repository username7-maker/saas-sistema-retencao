from __future__ import annotations

from datetime import date
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RoleEnum, User
from app.services.core_async_job_service import CoreAsyncJobNonRetryableError
from app.services.audit_service import log_audit_event
from app.services.premium_report_service import (
    ALLOWED_DASHBOARD_REPORTS,
    DashboardReportType,
    build_dashboard_report_payload,
    render_premium_report_pdf,
)
from app.utils.email import send_email_with_attachment_result


def generate_dashboard_pdf(
    db: Session,
    dashboard: DashboardReportType,
    *,
    generated_by: str | None = None,
) -> tuple[BytesIO, str]:
    payload = build_dashboard_report_payload(db, dashboard, generated_by=generated_by)
    pdf_bytes = render_premium_report_pdf(payload)
    filename = f"report_{dashboard.strip().lower()}_{date.today().isoformat()}.pdf"
    return BytesIO(pdf_bytes), filename


def send_monthly_reports(db: Session) -> dict[str, object]:
    buffer, filename = generate_dashboard_pdf(db, "consolidated", generated_by="Sistema")
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
    blocked = 0
    blocked_reasons: dict[str, int] = {}
    for user in leadership:
        result = send_email_with_attachment_result(
            user.email,
            "AI GYM OS - Relatorio Mensal Consolidado",
            "Segue em anexo o relatorio mensal consolidado da sua academia.",
            filename=filename,
            attachment_bytes=attachment,
        )
        if result.sent:
            sent += 1
        else:
            failed += 1
            if result.blocked:
                blocked += 1
            if result.reason:
                blocked_reasons[result.reason] = blocked_reasons.get(result.reason, 0) + 1
    return {
        "sent": sent,
        "failed": failed,
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "total_recipients": len(leadership),
    }


def execute_monthly_reports_dispatch_job(
    db: Session,
    *,
    gym_id,
    job_id,
    requested_by_user_id=None,
) -> dict[str, object]:
    result = send_monthly_reports(db)
    if result["total_recipients"] > 0 and result["sent"] == 0:
        primary_reason = next(iter(result.get("blocked_reasons", {}) or {}), "monthly_reports_delivery_failed")
        raise CoreAsyncJobNonRetryableError(
            primary_reason,
            "Disparo mensal nao entregou nenhum email para a lideranca da academia",
        )

    requested_by = db.get(User, requested_by_user_id) if requested_by_user_id else None
    log_audit_event(
        db,
        action="monthly_reports_dispatched",
        entity="report",
        user=requested_by,
        entity_id=job_id,
        details={"job_id": str(job_id), "gym_id": str(gym_id), **result},
    )
    db.flush()
    return result
