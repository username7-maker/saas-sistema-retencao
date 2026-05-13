from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.personal_ai import (
    PersonalAiContextOut,
    PersonalAiDraftCreate,
    PersonalAiDraftOut,
    PersonalAiPrepareResultOut,
)
from app.services.audit_service import log_audit_event
from app.services.personal_ai_service import (
    build_personal_ai_context,
    create_personal_ai_draft,
    list_personal_ai_drafts,
    prepare_personal_ai_draft_in_kommo,
)

router = APIRouter(tags=["personal-ai"])


@router.get("/members/{member_id}/personal-ai/context", response_model=PersonalAiContextOut)
def get_member_personal_ai_context_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
) -> PersonalAiContextOut:
    return build_personal_ai_context(db, gym_id=current_user.gym_id, member_id=member_id)


@router.post("/members/{member_id}/personal-ai/drafts", response_model=PersonalAiDraftOut)
def create_member_personal_ai_draft_endpoint(
    request: Request,
    member_id: UUID,
    payload: PersonalAiDraftCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
) -> PersonalAiDraftOut:
    result = create_personal_ai_draft(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        payload=payload,
        created_by_user_id=current_user.id,
        flush=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="personal_ai_draft_created",
        entity="autopilot_action",
        user=current_user,
        entity_id=result.id,
        details={
            "member_id": str(member_id),
            "intent": result.intent,
            "status": result.status,
            "blocked_reasons": result.blocked_reasons,
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result


@router.get("/personal-ai/drafts", response_model=list[PersonalAiDraftOut])
def list_personal_ai_drafts_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
    member_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[PersonalAiDraftOut]:
    return list_personal_ai_drafts(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        status_filter=status_filter,
        limit=limit,
    )


@router.post("/personal-ai/drafts/{draft_id}/prepare-kommo", response_model=PersonalAiPrepareResultOut)
def prepare_personal_ai_draft_kommo_endpoint(
    request: Request,
    draft_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
) -> PersonalAiPrepareResultOut:
    result = prepare_personal_ai_draft_in_kommo(db, gym_id=current_user.gym_id, draft_id=draft_id, flush=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="personal_ai_draft_prepared_kommo",
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
