from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import AuditLog, RoleEnum, User
from app.schemas import AuditLogOut


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogOut])
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    limit: int = Query(100, ge=1, le=1000),
) -> list[AuditLog]:
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
