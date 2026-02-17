from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import APIMessage
from app.services.audit_service import log_audit_event
from app.services.report_service import ALLOWED_DASHBOARD_REPORTS, generate_dashboard_pdf, send_monthly_reports


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard/{dashboard}/pdf")
def export_dashboard_pdf(
    request: Request,
    dashboard: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> StreamingResponse:
    normalized = dashboard.strip().lower()
    if normalized not in ALLOWED_DASHBOARD_REPORTS:
        raise HTTPException(status_code=404, detail="Dashboard de relatorio nao encontrado")

    buffer, filename = generate_dashboard_pdf(db, normalized)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="dashboard_pdf_exported",
        entity="report",
        user=current_user,
        details={"dashboard": normalized, "filename": filename},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
    )


@router.post("/monthly-dispatch", response_model=APIMessage)
def dispatch_monthly_reports(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> APIMessage:
    result = send_monthly_reports(db)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="monthly_reports_dispatched",
        entity="report",
        user=current_user,
        details=result,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return APIMessage(message=f"Relatorios enviados: {result['sent']} sucesso, {result['failed']} falhas")
