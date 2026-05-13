from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.ai_review_center import (
    AiReviewCenterActionOut,
    AiReviewCenterFeedbackInput,
    AiReviewCenterListOut,
    AiReviewCenterMetricsOut,
    AiReviewCenterRejectInput,
)
from app.services.ai_review_center_service import (
    list_ai_review_center_items,
    prepare_review_center_item_in_kommo,
    record_review_center_feedback,
)
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/ai/review-center", tags=["ai-review-center"])

ALLOWED_ROLES = (
    RoleEnum.OWNER,
    RoleEnum.MANAGER,
    RoleEnum.RECEPTIONIST,
    RoleEnum.TRAINER,
    RoleEnum.SALESPERSON,
)


@router.get("/items", response_model=AiReviewCenterListOut)
def list_ai_review_center_items_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*ALLOWED_ROLES))],
    source: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
) -> AiReviewCenterListOut:
    return list_ai_review_center_items(
        db,
        gym_id=current_user.gym_id,
        user_role=current_user.role,
        source_filter=source,
        status_filter=status_filter,
        q=q,
        limit=limit,
    )


@router.get("/metrics", response_model=AiReviewCenterMetricsOut)
def get_ai_review_center_metrics_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*ALLOWED_ROLES))],
    source: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> AiReviewCenterMetricsOut:
    result = list_ai_review_center_items(
        db,
        gym_id=current_user.gym_id,
        user_role=current_user.role,
        source_filter=source,
        status_filter=status_filter,
        limit=200,
    )
    return result.metrics


@router.post("/items/{source_type}/{source_id}/prepare-kommo", response_model=AiReviewCenterActionOut)
def prepare_ai_review_center_item_kommo_endpoint(
    request: Request,
    source_type: str,
    source_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*ALLOWED_ROLES))],
) -> AiReviewCenterActionOut:
    result = prepare_review_center_item_in_kommo(
        db,
        gym_id=current_user.gym_id,
        user_role=current_user.role,
        reviewer_user_id=current_user.id,
        source_type=source_type,
        source_id=source_id,
        flush=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="ai_review_center_prepare_kommo",
        entity="ai_review_center",
        user=current_user,
        entity_id=source_id,
        member_id=result.item.member_id,
        details={
            "source_type": source_type,
            "status": result.item.status,
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


@router.post("/items/{source_type}/{source_id}/feedback", response_model=AiReviewCenterActionOut)
def record_ai_review_center_feedback_endpoint(
    request: Request,
    source_type: str,
    source_id: UUID,
    payload: AiReviewCenterFeedbackInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*ALLOWED_ROLES))],
) -> AiReviewCenterActionOut:
    result = record_review_center_feedback(
        db,
        gym_id=current_user.gym_id,
        user_role=current_user.role,
        reviewer_user_id=current_user.id,
        source_type=source_type,
        source_id=source_id,
        payload=payload,
        flush=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="ai_review_center_feedback",
        entity="ai_review_center",
        user=current_user,
        entity_id=source_id,
        member_id=result.item.member_id,
        details={
            "source_type": source_type,
            "decision": payload.decision,
            "has_edit": bool(payload.edited_reply),
            "status": result.item.status,
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result


@router.post("/items/{source_type}/{source_id}/reject", response_model=AiReviewCenterActionOut)
def reject_ai_review_center_item_endpoint(
    request: Request,
    source_type: str,
    source_id: UUID,
    payload: AiReviewCenterRejectInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*ALLOWED_ROLES))],
) -> AiReviewCenterActionOut:
    result = record_review_center_feedback(
        db,
        gym_id=current_user.gym_id,
        user_role=current_user.role,
        reviewer_user_id=current_user.id,
        source_type=source_type,
        source_id=source_id,
        payload=AiReviewCenterFeedbackInput(decision="rejected", reason=payload.reason),
        flush=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="ai_review_center_reject",
        entity="ai_review_center",
        user=current_user,
        entity_id=source_id,
        member_id=result.item.member_id,
        details={"source_type": source_type, "reason": payload.reason, "status": result.item.status},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result
