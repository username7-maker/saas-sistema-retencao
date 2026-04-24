from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.core.config import settings
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import CoreAsyncJobAcceptedResponse, CoreAsyncJobStatusRead
from app.services.audit_service import log_audit_event
from app.services.core_async_job_service import (
    CORE_ASYNC_JOB_TYPE_MONTHLY_REPORTS_DISPATCH,
    enqueue_monthly_reports_dispatch_job,
    get_core_async_job,
    serialize_core_async_job,
)
from app.services.report_service import ALLOWED_DASHBOARD_REPORTS, generate_dashboard_pdf


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

    buffer, filename = generate_dashboard_pdf(
        db,
        normalized,
        generated_by=current_user.full_name,
    )
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


@router.post("/monthly-dispatch", response_model=CoreAsyncJobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def dispatch_monthly_reports(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> CoreAsyncJobAcceptedResponse:
    if not settings.monthly_reports_dispatch_enabled:
        raise HTTPException(status_code=503, detail="Disparo mensal temporariamente desabilitado para o piloto")
    job, created = enqueue_monthly_reports_dispatch_job(
        db,
        gym_id=current_user.gym_id,
        requested_by_user_id=current_user.id,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="monthly_reports_dispatch_queued",
        entity="report",
        user=current_user,
        entity_id=job.id,
        details={"job_id": str(job.id), "status": job.status, "created": created},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return CoreAsyncJobAcceptedResponse(
        message="Disparo mensal enfileirado.",
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
    )


@router.get("/monthly-dispatches/{job_id}", response_model=CoreAsyncJobStatusRead)
def get_monthly_dispatch_status(
    job_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> CoreAsyncJobStatusRead:
    job = get_core_async_job(db, job_id=job_id, gym_id=current_user.gym_id)
    if job is None or job.job_type != CORE_ASYNC_JOB_TYPE_MONTHLY_REPORTS_DISPATCH:
        raise HTTPException(status_code=404, detail="Disparo mensal nao encontrado")
    return CoreAsyncJobStatusRead(**serialize_core_async_job(job))
