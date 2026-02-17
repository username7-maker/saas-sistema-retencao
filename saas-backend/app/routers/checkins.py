from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import CheckinCreate, CheckinOut
from app.services.audit_service import log_audit_event
from app.services.checkin_service import create_checkin
from app.services.websocket_manager import websocket_manager


router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.post("/", response_model=CheckinOut, status_code=status.HTTP_201_CREATED)
async def create_checkin_endpoint(
    request: Request,
    payload: CheckinCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> CheckinOut:
    try:
        checkin = create_checkin(db, payload)
        context = get_request_context(request)
        log_audit_event(
            db,
            action="checkin_created",
            entity="checkin",
            user=current_user,
            member_id=checkin.member_id,
            entity_id=checkin.id,
            details={"source": checkin.source.value},
            ip_address=context["ip_address"],
            user_agent=context["user_agent"],
        )
        db.commit()
        await websocket_manager.broadcast_event(
            str(checkin.gym_id),
            "checkin_created",
            {
                "checkin_id": str(checkin.id),
                "member_id": str(checkin.member_id),
                "checkin_at": checkin.checkin_at.isoformat(),
            },
        )
        return checkin
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
