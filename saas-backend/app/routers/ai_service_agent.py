from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.ai_service_agent import AiServiceAgentDraftOut, AiServiceAgentPrepareResultOut
from app.services.ai_service_agent_service import list_ai_service_agent_drafts, prepare_ai_service_agent_draft_in_kommo
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/ai/service-agent", tags=["ai-service-agent"])


@router.get("/drafts", response_model=list[AiServiceAgentDraftOut])
def list_ai_service_agent_drafts_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER, RoleEnum.SALESPERSON))],
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[AiServiceAgentDraftOut]:
    return list_ai_service_agent_drafts(db, gym_id=current_user.gym_id, status_filter=status_filter, limit=limit)


@router.post("/drafts/{draft_id}/prepare-kommo", response_model=AiServiceAgentPrepareResultOut)
def prepare_ai_service_agent_draft_kommo_endpoint(
    request: Request,
    draft_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER, RoleEnum.SALESPERSON))],
) -> AiServiceAgentPrepareResultOut:
    result = prepare_ai_service_agent_draft_in_kommo(db, gym_id=current_user.gym_id, draft_id=draft_id, flush=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="ai_service_agent_draft_prepared_kommo",
        entity="autopilot_action",
        user=current_user,
        entity_id=draft_id,
        details={
            "status": result.draft.status,
            "intent": result.draft.intent,
            "kommo_contact_id": result.kommo_contact_id,
            "kommo_lead_id": result.kommo_lead_id,
            "kommo_task_id": result.kommo_task_id,
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result
