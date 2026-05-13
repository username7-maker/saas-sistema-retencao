from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas.movement_video import (
    MovementVideoAnalyzeInput,
    MovementVideoApproveInput,
    MovementVideoKommoPrepareOut,
    MovementVideoRejectInput,
    MovementVideoReviewCreate,
    MovementVideoReviewOut,
)
from app.services.audit_service import log_audit_event
from app.services.movement_video_service import (
    analyze_movement_video_review,
    approve_movement_video_review,
    create_movement_video_review,
    list_movement_video_reviews,
    prepare_movement_video_review_in_kommo,
    reject_movement_video_review,
)

router = APIRouter(tags=["movement-video"])


@router.get("/members/{member_id}/movement-video/reviews", response_model=list[MovementVideoReviewOut])
def list_member_movement_video_reviews_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
    limit: int = Query(default=50, ge=1, le=100),
) -> list[MovementVideoReviewOut]:
    return list_movement_video_reviews(db, gym_id=current_user.gym_id, member_id=member_id, limit=limit)


@router.post("/members/{member_id}/movement-video/reviews", response_model=MovementVideoReviewOut)
def create_member_movement_video_review_endpoint(
    request: Request,
    member_id: UUID,
    payload: MovementVideoReviewCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
) -> MovementVideoReviewOut:
    result = create_movement_video_review(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        payload=payload,
        trainer_user_id=current_user.id,
        flush=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="movement_video_review_created",
        entity="movement_video_review",
        user=current_user,
        entity_id=result.id,
        details={
            "member_id": str(member_id),
            "exercise_name": result.exercise_name,
            "status": result.status,
            "blocked_reasons": result.blocked_reasons,
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result


@router.post("/movement-video/reviews/{review_id}/analyze", response_model=MovementVideoReviewOut)
def analyze_movement_video_review_endpoint(
    request: Request,
    review_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
    payload: MovementVideoAnalyzeInput | None = None,
) -> MovementVideoReviewOut:
    result = analyze_movement_video_review(db, gym_id=current_user.gym_id, review_id=review_id, payload=payload, flush=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="movement_video_review_analyzed",
        entity="movement_video_review",
        user=current_user,
        entity_id=result.id,
        details={"status": result.status, "analysis_status": result.analysis_status},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result


@router.post("/movement-video/reviews/{review_id}/approve", response_model=MovementVideoReviewOut)
def approve_movement_video_review_endpoint(
    request: Request,
    review_id: UUID,
    payload: MovementVideoApproveInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
) -> MovementVideoReviewOut:
    result = approve_movement_video_review(db, gym_id=current_user.gym_id, review_id=review_id, payload=payload, flush=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="movement_video_feedback_approved",
        entity="movement_video_review",
        user=current_user,
        entity_id=result.id,
        details={"member_id": str(result.member_id), "exercise_name": result.exercise_name, "status": result.status},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result


@router.post("/movement-video/reviews/{review_id}/reject", response_model=MovementVideoReviewOut)
def reject_movement_video_review_endpoint(
    request: Request,
    review_id: UUID,
    payload: MovementVideoRejectInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
) -> MovementVideoReviewOut:
    result = reject_movement_video_review(db, gym_id=current_user.gym_id, review_id=review_id, payload=payload, flush=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="movement_video_review_rejected",
        entity="movement_video_review",
        user=current_user,
        entity_id=result.id,
        details={"member_id": str(result.member_id), "reason": payload.reason},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return result


@router.post("/movement-video/reviews/{review_id}/prepare-kommo", response_model=MovementVideoKommoPrepareOut)
def prepare_movement_video_review_kommo_endpoint(
    request: Request,
    review_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
) -> MovementVideoKommoPrepareOut:
    result = prepare_movement_video_review_in_kommo(db, gym_id=current_user.gym_id, review_id=review_id, flush=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="movement_video_feedback_prepared_kommo",
        entity="movement_video_review",
        user=current_user,
        entity_id=review_id,
        details={
            "status": result.review.status,
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
