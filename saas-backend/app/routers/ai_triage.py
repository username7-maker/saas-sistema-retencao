from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import (
    AITriageApprovalUpdate,
    AITriageMetricsSummaryRead,
    AITriageOutcomeUpdate,
    AITriageRecommendationRead,
    AITriageSafeActionPrepareInput,
    AITriageSafeActionPreparedRead,
    PaginatedResponse,
)
from app.services.ai_triage_service import (
    get_ai_triage_metrics_summary,
    get_ai_triage_recommendation_or_404,
    list_ai_triage_recommendations,
    prepare_ai_triage_recommendation_action,
    serialize_ai_triage_recommendation,
    sync_ai_triage_recommendations,
    update_ai_triage_recommendation_approval,
    update_ai_triage_recommendation_outcome,
)
from app.services.audit_service import log_audit_event


router = APIRouter(prefix="/ai/triage", tags=["ai-triage"])


@router.get("/metrics/summary", response_model=AITriageMetricsSummaryRead)
def get_ai_triage_metrics_summary_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> AITriageMetricsSummaryRead:
    sync_ai_triage_recommendations(db, gym_id=current_user.gym_id)
    db.commit()
    return get_ai_triage_metrics_summary(db, gym_id=current_user.gym_id)


@router.get("/items", response_model=PaginatedResponse[AITriageRecommendationRead])
def list_ai_triage_items(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[AITriageRecommendationRead]:
    sync_ai_triage_recommendations(db, gym_id=current_user.gym_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="ai_triage_list_viewed",
        entity="ai_triage_recommendation",
        user=current_user,
        details={"page": page, "page_size": page_size},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return list_ai_triage_recommendations(db, gym_id=current_user.gym_id, page=page, page_size=page_size)


@router.get("/items/{recommendation_id}", response_model=AITriageRecommendationRead)
def get_ai_triage_item(
    recommendation_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> AITriageRecommendationRead:
    sync_ai_triage_recommendations(db, gym_id=current_user.gym_id)
    recommendation = get_ai_triage_recommendation_or_404(
        db,
        recommendation_id=recommendation_id,
        gym_id=current_user.gym_id,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="ai_triage_detail_viewed",
        entity="ai_triage_recommendation",
        user=current_user,
        member_id=recommendation.member_id,
        entity_id=recommendation.id,
        details={
            "source_domain": recommendation.source_domain,
            "source_entity_kind": recommendation.source_entity_kind,
            "source_entity_id": str(recommendation.source_entity_id),
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return serialize_ai_triage_recommendation(recommendation)


@router.patch("/items/{recommendation_id}/approval", response_model=AITriageRecommendationRead)
def update_ai_triage_item_approval(
    recommendation_id: UUID,
    payload: AITriageApprovalUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> AITriageRecommendationRead:
    context = get_request_context(request)
    recommendation = update_ai_triage_recommendation_approval(
        db,
        recommendation_id=recommendation_id,
        gym_id=current_user.gym_id,
        decision=payload.decision,
        note=payload.note,
        current_user=current_user,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return recommendation


@router.post("/items/{recommendation_id}/actions/prepare", response_model=AITriageSafeActionPreparedRead)
def prepare_ai_triage_item_action(
    recommendation_id: UUID,
    payload: AITriageSafeActionPrepareInput,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> AITriageSafeActionPreparedRead:
    context = get_request_context(request)
    prepared = prepare_ai_triage_recommendation_action(
        db,
        recommendation_id=recommendation_id,
        gym_id=current_user.gym_id,
        action=payload.action,
        current_user=current_user,
        assigned_to_user_id=payload.assigned_to_user_id,
        owner_role=payload.owner_role,
        owner_label=payload.owner_label,
        note=payload.note,
        operator_note=payload.operator_note,
        auto_approve=payload.auto_approve,
        confirm_approval=payload.confirm_approval,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return prepared


@router.patch("/items/{recommendation_id}/outcome", response_model=AITriageRecommendationRead)
def update_ai_triage_item_outcome(
    recommendation_id: UUID,
    payload: AITriageOutcomeUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> AITriageRecommendationRead:
    context = get_request_context(request)
    recommendation = update_ai_triage_recommendation_outcome(
        db,
        recommendation_id=recommendation_id,
        gym_id=current_user.gym_id,
        outcome=payload.outcome,
        note=payload.note,
        current_user=current_user,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return recommendation
