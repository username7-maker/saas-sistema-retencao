import logging
import threading
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.core.distributed_lock import with_distributed_lock
from app.database import SessionLocal, get_db, set_current_gym_id, clear_current_gym_id
from app.models import MemberStatus, RiskLevel, RoleEnum, User
from app.schemas import APIMessage, MemberCreate, MemberOut, MemberUpdate, PaginatedResponse
from app.schemas.body_composition import BodyCompositionEvaluationCreate, BodyCompositionEvaluationRead
from app.services.audit_service import log_audit_event
from app.services.body_composition_service import (
    create_body_composition_evaluation,
    list_body_composition_evaluations,
    update_body_composition_evaluation,
)
from app.services.member_service import create_member, get_member_or_404, list_members, soft_delete_member, update_member
from app.services.member_timeline_service import get_member_timeline
from app.services.onboarding_score_service import calculate_onboarding_score
from app.services.risk import run_daily_risk_processing

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/members", tags=["members"])


@router.post("/", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def create_member_endpoint(
    request: Request,
    payload: MemberCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> MemberOut:
    member = create_member(db, payload, gym_id=current_user.gym_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="member_created",
        entity="member",
        user=current_user,
        member_id=member.id,
        entity_id=member.id,
        details={"plan_name": member.plan_name},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return member


@router.get("/", response_model=PaginatedResponse[MemberOut])
def list_members_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    risk_level: RiskLevel | None = None,
    status: MemberStatus | None = None,
    plan_cycle: Literal["monthly", "semiannual", "annual"] | None = None,
    min_days_without_checkin: int | None = Query(default=None, ge=0),
    provisional_only: bool | None = None,
) -> PaginatedResponse[MemberOut]:
    return list_members(
        db,
        gym_id=current_user.gym_id,
        page=page,
        page_size=page_size,
        search=search,
        risk_level=risk_level,
        status=status,
        plan_cycle=plan_cycle,
        min_days_without_checkin=min_days_without_checkin,
        provisional_only=provisional_only,
    )


@router.get("/{member_id}", response_model=MemberOut)
def get_member_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
) -> MemberOut:
    return get_member_or_404(db, member_id, gym_id=current_user.gym_id)


@router.patch("/{member_id}", response_model=MemberOut)
def update_member_endpoint(
    request: Request,
    member_id: UUID,
    payload: MemberUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> MemberOut:
    member = update_member(db, member_id, payload, gym_id=current_user.gym_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="member_updated",
        entity="member",
        user=current_user,
        member_id=member.id,
        entity_id=member.id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return member


@router.delete("/{member_id}", response_model=APIMessage)
def delete_member_endpoint(
    request: Request,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> APIMessage:
    soft_delete_member(db, member_id, gym_id=current_user.gym_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="member_soft_deleted",
        entity="member",
        user=current_user,
        member_id=member_id,
        entity_id=member_id,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return APIMessage(message="Membro removido com soft delete")


@router.post("/recalculate-risk", status_code=202)
def recalculate_risk_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> JSONResponse:
    gym_id = current_user.gym_id
    context = get_request_context(request)
    log_audit_event(
        db,
        action="risk_recalculation_triggered",
        entity="member",
        user=current_user,
        details={"status": "started_background"},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()

    threading.Thread(
        target=_run_risk_recalculation_background,
        args=(gym_id,),
        daemon=True,
    ).start()

    return JSONResponse(
        status_code=202,
        content={"message": "Recalculo de risco iniciado em segundo plano", "status": "processing"},
    )


def _run_risk_recalculation_background(gym_id: UUID) -> None:
    @with_distributed_lock("daily_risk", ttl_seconds=1800)
    def _inner() -> None:
        db = SessionLocal()
        try:
            set_current_gym_id(gym_id)
            result = run_daily_risk_processing(db)
            logger.info("Background risk recalculation completed for gym %s: %s", gym_id, result)
        except Exception:
            logger.exception("Background risk recalculation failed for gym %s", gym_id)
            db.rollback()
        finally:
            clear_current_gym_id()
            db.close()

    try:
        _inner()
    except Exception:
        logger.warning("Risk recalculation skipped - lock already held (daily job running)")


@router.get("/{member_id}/onboarding-score")
def get_onboarding_score_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> dict:
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    return calculate_onboarding_score(db, member)


@router.get("/{member_id}/timeline")
def member_timeline_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    return get_member_timeline(db, member_id, limit=limit)


@router.get("/{member_id}/body-composition", response_model=list[BodyCompositionEvaluationRead])
def list_body_composition_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
    limit: int = Query(20, ge=1, le=100),
) -> list[BodyCompositionEvaluationRead]:
    return list_body_composition_evaluations(db, current_user.gym_id, member_id, limit=limit)


@router.post("/{member_id}/body-composition", response_model=BodyCompositionEvaluationRead, status_code=status.HTTP_201_CREATED)
def create_body_composition_endpoint(
    member_id: UUID,
    payload: BodyCompositionEvaluationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> BodyCompositionEvaluationRead:
    evaluation = create_body_composition_evaluation(db, current_user.gym_id, member_id, payload)
    db.commit()
    return evaluation


@router.put("/{member_id}/body-composition/{evaluation_id}", response_model=BodyCompositionEvaluationRead)
def update_body_composition_endpoint(
    member_id: UUID,
    evaluation_id: UUID,
    payload: BodyCompositionEvaluationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> BodyCompositionEvaluationRead:
    evaluation = update_body_composition_evaluation(db, current_user.gym_id, member_id, evaluation_id, payload)
    db.commit()
    return evaluation


class ContactLogCreate(BaseModel):
    outcome: Literal["answered", "no_answer", "voicemail", "invalid_number"]
    note: str | None = None


@router.post("/{member_id}/contact-log", status_code=status.HTTP_201_CREATED)
def create_contact_log_endpoint(
    request: Request,
    member_id: UUID,
    payload: ContactLogCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
) -> dict:
    get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="call_log_manual",
        entity="contact_log",
        member_id=member_id,
        user=current_user,
        details={"outcome": payload.outcome, "note": payload.note or ""},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return {"status": "logged"}
