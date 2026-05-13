from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.student_personal_ai import (
    StudentPersonalAiDraftOut,
    StudentPersonalAiPrepareResultOut,
    StudentPersonalAiRejectInput,
)
from app.services.audit_service import log_audit_event
from app.services.student_personal_ai_service import (
    list_student_personal_ai_drafts,
    prepare_student_personal_ai_draft_in_kommo,
    reject_student_personal_ai_draft,
)

router = APIRouter(prefix="/ai/student-personal", tags=["student-personal-ai"])


@router.get("/drafts", response_model=list[StudentPersonalAiDraftOut])
def list_student_personal_ai_drafts_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
    member_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[StudentPersonalAiDraftOut]:
    return list_student_personal_ai_drafts(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        status_filter=status_filter,
        limit=limit,
    )


@router.post("/drafts/{draft_id}/prepare-kommo", response_model=StudentPersonalAiPrepareResultOut)
def prepare_student_personal_ai_draft_kommo_endpoint(
    request: Request,
    draft_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> StudentPersonalAiPrepareResultOut:
    result = prepare_student_personal_ai_draft_in_kommo(db, gym_id=current_user.gym_id, draft_id=draft_id, flush=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="student_personal_ai_prepared_kommo",
        entity="autopilot_action",
        user=current_user,
        entity_id=draft_id,
        member_id=result.draft.member_id,
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


@router.post("/drafts/{draft_id}/reject", response_model=StudentPersonalAiDraftOut)
def reject_student_personal_ai_draft_endpoint(
    request: Request,
    draft_id: UUID,
    payload: StudentPersonalAiRejectInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> StudentPersonalAiDraftOut:
    result = reject_student_personal_ai_draft(
        db,
        gym_id=current_user.gym_id,
        draft_id=draft_id,
        reason=payload.reason,
        flush=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="student_personal_ai_rejected",
        entity="autopilot_action",
        user=current_user,
        entity_id=draft_id,
        member_id=result.member_id,
        details={"reason": payload.reason, "status": result.status, "intent": result.intent},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result
