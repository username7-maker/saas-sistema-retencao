import json
import logging
from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.core.config import settings
from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import BodyCompositionEvaluation, Member, MemberStatus, RiskLevel, RoleEnum, User
from app.schemas import (
    APIMessage,
    MemberCreate,
    MemberNoteCreate,
    MemberNoteOut,
    MemberOperationalProfileOut,
    MemberOut,
    MemberUpdate,
    OnboardingScoreOut,
    OnboardingScoreSnapshotOut,
    PaginatedResponse,
    RiskRecalculationRequestOut,
)
from app.schemas.body_composition import (
    ActuarManualSyncConfirmInput,
    ActuarMemberLinkRead,
    ActuarMemberLinkUpsert,
    BodyCompositionActuarSyncStatusRead,
    BodyCompositionEvaluationCreate,
    BodyCompositionEvaluationRead,
    BodyCompositionEvaluationReviewInput,
    BodyCompositionEvaluationUpdate,
    BodyCompositionImageOcrPayload,
    BodyCompositionImageParseResultRead,
    BodyCompositionCaptureMetadata,
    BodyCompositionCaptureEventInput,
    BodyCompositionKommoDispatchRead,
    BodyCompositionManualSyncSummaryRead,
    BodyCompositionReportRead,
    BodyCompositionWhatsAppDispatchRead,
)
from app.schemas.assessment import (
    AssessmentMiniOut,
    AssessmentOut,
    AssessmentSummary360Out,
    MemberConstraintsOut,
    MemberGoalOut,
    MemberMiniOut,
    Profile360Out,
    TrainingPlanOut,
)
from app.schemas.member_intelligence import LeadToMemberIntelligenceContextOut
from app.services.ai_assistant_service import build_onboarding_assistant
from app.services.ai_assistant_service import build_assessment_assistant
from app.services.assessment_intelligence_service import get_assessment_summary_360
from app.services.assessment_service import get_member_profile_360, list_assessments
from app.services.audit_service import log_audit_event
from app.services.body_composition_actuar_sync_service import (
    confirm_manual_actuar_sync,
    create_body_composition_sync_job,
    get_body_composition_evaluation_or_404,
    get_body_composition_manual_sync_summary,
    get_body_composition_sync_status,
    schedule_body_composition_sync_retry,
    upsert_body_composition_actuar_link,
)
from app.services.body_composition_delivery_service import (
    build_body_composition_report_payload,
    generate_body_composition_pdf,
    generate_body_composition_technical_pdf,
    send_body_composition_kommo_handoff,
    send_body_composition_kommo_salesbot,
    send_body_composition_whatsapp_summary,
)
from app.services.body_composition_image_parse_service import MAX_IMAGE_SIZE_BYTES, parse_body_composition_image
from app.services.document_image_preprocessing import preprocess_receipt_image
from app.services.body_composition_service import (
    create_body_composition_evaluation,
    delete_body_composition_evaluation,
    list_body_composition_evaluations,
    review_body_composition_evaluation,
    serialize_body_composition_evaluation,
    serialize_body_composition_evaluations,
    update_body_composition_evaluation,
)
from app.services.kommo_service import KommoSalesbotDispatchError, KommoServiceError
from app.services.member_intelligence_service import get_member_intelligence_context
from app.services.member_operational_profile_service import (
    build_member_operational_profile,
    create_member_note,
    list_member_notes,
)
from app.services.member_profile_permissions_service import build_member_profile_permissions
from app.services.member_service import (
    create_member,
    get_member_or_404,
    list_member_index,
    list_members,
    reconcile_member_last_checkin,
    soft_delete_member,
    update_member,
)
from app.services.member_timeline_service import get_member_timeline
from app.services.onboarding_score_service import calculate_onboarding_score
from app.services.preferred_shift_service import sync_preferred_shifts_from_checkins
from app.services.risk_recalculation_service import (
    enqueue_risk_recalculation_request,
    get_risk_recalculation_request,
    serialize_risk_recalculation_request,
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/members", tags=["members"])
BODY_COMPOSITION_PDF_LAYOUT_VERSION = "clinical-a4-weight-comparison-2026-09-01"


class PreferredShiftSyncResult(BaseModel):
    updated_count: int
    message: str


@router.post("/", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def create_member_endpoint(
    request: Request,
    payload: MemberCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> MemberOut:
    member = create_member(db, payload, gym_id=current_user.gym_id, commit=False)
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
    invalidate_dashboard_cache("members")
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
    preferred_shift: Literal["overnight", "morning", "afternoon", "evening"] | None = None,
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
        preferred_shift=preferred_shift,
        min_days_without_checkin=min_days_without_checkin,
        provisional_only=provisional_only,
    )


@router.get("/index", response_model=list[MemberOut])
def list_members_index_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
    search: str | None = None,
    risk_level: RiskLevel | None = None,
    status: MemberStatus | None = None,
    plan_cycle: Literal["monthly", "semiannual", "annual"] | None = None,
    preferred_shift: Literal["overnight", "morning", "afternoon", "evening"] | None = None,
    min_days_without_checkin: int | None = Query(default=None, ge=0),
    provisional_only: bool | None = None,
) -> list[MemberOut]:
    return list_member_index(
        db,
        gym_id=current_user.gym_id,
        search=search,
        risk_level=risk_level,
        status=status,
        plan_cycle=plan_cycle,
        preferred_shift=preferred_shift,
        min_days_without_checkin=min_days_without_checkin,
        provisional_only=provisional_only,
    )


@router.post("/preferred-shifts/sync", response_model=PreferredShiftSyncResult)
def sync_preferred_shifts_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> PreferredShiftSyncResult:
    updated_count = sync_preferred_shifts_from_checkins(
        db,
        gym_id=current_user.gym_id,
        commit=False,
        flush=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="preferred_shift_sync_requested",
        entity="member",
        user=current_user,
        details={"updated_count": updated_count},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    invalidate_dashboard_cache("members", "dashboard_retention", "dashboard_operational")
    return PreferredShiftSyncResult(
        updated_count=updated_count,
        message=f"{updated_count} turno(s) recalculados por check-in.",
    )


@router.get("/onboarding-scoreboard", response_model=list[OnboardingScoreSnapshotOut])
def list_onboarding_scoreboard_endpoint(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> list[OnboardingScoreSnapshotOut]:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    today = datetime.now().date()
    rows = db.execute(
        select(Member.id, Member.onboarding_score, Member.onboarding_status)
        .where(
            Member.gym_id == current_user.gym_id,
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.join_date >= today - timedelta(days=30),
            Member.join_date <= today,
            Member.onboarding_status.in_(("active", "at_risk")),
        )
        .order_by(Member.onboarding_score.asc(), Member.join_date.asc())
    ).all()
    return [
        OnboardingScoreSnapshotOut(
            member_id=member_id,
            score=int(onboarding_score or 0),
            status=str(onboarding_status or "active"),
        )
        for member_id, onboarding_score, onboarding_status in rows
    ]


@router.get("/{member_id}", response_model=MemberOut)
def get_member_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
) -> MemberOut:
    return get_member_or_404(db, member_id, gym_id=current_user.gym_id)


@router.get("/{member_id}/workspace-bootstrap")
def get_member_workspace_bootstrap_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
) -> dict:
    """Return only the above-the-fold member workspace data in one network roundtrip."""
    if not settings.member_workspace_bootstrap_v1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace bootstrap desabilitado")
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    profile_payload = get_member_profile_360(db, member_id)
    summary_payload = get_assessment_summary_360(db, member_id)
    # The operational profile is intentionally loaded by its own lazy endpoint.
    # Building it here duplicated dozens of queries and one invalid optional
    # operational signal could turn the entire workspace bootstrap into a 422.
    permissions = build_member_profile_permissions(current_user)
    assessments = list_assessments(db, member_id, gym_id=current_user.gym_id)[:10]
    body_evaluations = list_body_composition_evaluations(db, current_user.gym_id, member_id, limit=5)

    profile = Profile360Out(
        member=MemberMiniOut.model_validate(profile_payload["member"]),
        latest_assessment=(
            AssessmentMiniOut.model_validate(profile_payload.get("latest_assessment"))
            if profile_payload.get("latest_assessment") else None
        ),
        constraints=(
            MemberConstraintsOut.model_validate(profile_payload.get("constraints"))
            if profile_payload.get("constraints") else None
        ),
        goals=[MemberGoalOut.model_validate(item) for item in profile_payload.get("goals", [])],
        active_training_plan=(
            TrainingPlanOut.model_validate(profile_payload.get("active_training_plan"))
            if profile_payload.get("active_training_plan") else None
        ),
        insight_summary=profile_payload.get("insight_summary"),
    )
    summary = AssessmentSummary360Out(
        member=MemberMiniOut.model_validate(summary_payload["member"]),
        latest_assessment=(
            AssessmentMiniOut.model_validate(summary_payload["latest_assessment"])
            if summary_payload.get("latest_assessment") else None
        ),
        goal_type=summary_payload["goal_type"],
        status=summary_payload["status"],
        days_since_last_checkin=summary_payload["days_since_last_checkin"],
        recent_weekly_checkins=summary_payload["recent_weekly_checkins"],
        target_frequency_per_week=summary_payload["target_frequency_per_week"],
        forecast=summary_payload["forecast"],
        diagnosis=summary_payload["diagnosis"],
        benchmark=summary_payload["benchmark"],
        narratives=summary_payload["narratives"],
        next_best_action=summary_payload["next_best_action"],
        actions=summary_payload["actions"],
        assistant=build_assessment_assistant(summary_payload),
    )
    return {
        "member": MemberOut.model_validate(member).model_dump(mode="json"),
        "profile_summary": profile.model_dump(mode="json"),
        "latest_assessments": [AssessmentOut.model_validate(item).model_dump(mode="json") for item in assessments],
        "operational_summary": None,
        "summary_360": summary.model_dump(mode="json"),
        "body_composition": [
            item.model_dump(mode="json")
            for item in serialize_body_composition_evaluations(
                db, current_user.gym_id, member_id, body_evaluations
            )
        ],
        "permissions": permissions,
        "version": getattr(member, "updated_at", None).isoformat() if getattr(member, "updated_at", None) else "1",
    }


@router.get("/{member_id}/operational-profile", response_model=MemberOperationalProfileOut)
def get_member_operational_profile_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
) -> MemberOperationalProfileOut:
    return MemberOperationalProfileOut.model_validate(
        build_member_operational_profile(db, member_id=member_id, current_user=current_user)
    )


@router.get("/{member_id}/notes", response_model=list[MemberNoteOut])
def list_member_notes_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
) -> list[MemberNoteOut]:
    return list_member_notes(db, member_id=member_id, current_user=current_user)


@router.post("/{member_id}/notes", response_model=MemberNoteOut, status_code=status.HTTP_201_CREATED)
def create_member_note_endpoint(
    request: Request,
    member_id: UUID,
    payload: MemberNoteCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
) -> MemberNoteOut:
    note = create_member_note(db, member_id=member_id, current_user=current_user, payload=payload)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="member_note_created",
        entity="member_note",
        user=current_user,
        member_id=member_id,
        entity_id=note.id,
        details={"note_type": note.note_type, "visibility": note.visibility},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(note)
    return note


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
    db.refresh(member)
    return member


@router.post("/{member_id}/reconcile-last-checkin", response_model=MemberOut)
def reconcile_member_last_checkin_endpoint(
    request: Request,
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> MemberOut:
    member, previous_last_checkin_at, latest_checkin_at = reconcile_member_last_checkin(
        db,
        member_id,
        gym_id=current_user.gym_id,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="member_last_checkin_reconciled",
        entity="member",
        user=current_user,
        member_id=member.id,
        entity_id=member.id,
        details={
            "previous_last_checkin_at": (
                previous_last_checkin_at.isoformat() if previous_last_checkin_at is not None else None
            ),
            "reconciled_last_checkin_at": latest_checkin_at.isoformat(),
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(member)
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


@router.post("/recalculate-risk", response_model=RiskRecalculationRequestOut, status_code=202)
def recalculate_risk_endpoint(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> RiskRecalculationRequestOut:
    gym_id = current_user.gym_id
    request_record, created = enqueue_risk_recalculation_request(
        db,
        gym_id=gym_id,
        requested_by_user_id=current_user.id,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="risk_recalculation_triggered",
        entity="member",
        user=current_user,
        details={"status": "queued", "request_id": str(request_record.id), "created": created},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return RiskRecalculationRequestOut.model_validate(serialize_risk_recalculation_request(request_record))


@router.get("/recalculate-risk/{request_id}", response_model=RiskRecalculationRequestOut)
def get_recalculate_risk_status_endpoint(
    request_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> RiskRecalculationRequestOut:
    request_record = get_risk_recalculation_request(
        db,
        request_id=request_id,
        gym_id=current_user.gym_id,
    )
    if request_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitacao de recalculo nao encontrada")
    return RiskRecalculationRequestOut.model_validate(serialize_risk_recalculation_request(request_record))


@router.get("/{member_id}/onboarding-score", response_model=OnboardingScoreOut)
def get_onboarding_score_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> OnboardingScoreOut:
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    payload = calculate_onboarding_score(db, member)
    return OnboardingScoreOut(**payload, assistant=build_onboarding_assistant(member, payload))


@router.get("/{member_id}/intelligence-context", response_model=LeadToMemberIntelligenceContextOut)
def get_member_intelligence_context_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER)),
    ],
) -> LeadToMemberIntelligenceContextOut:
    return get_member_intelligence_context(db, member_id, gym_id=current_user.gym_id)


@router.get("/{member_id}/timeline")
def member_timeline_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    if current_user.role == RoleEnum.TRAINER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissao insuficiente")
    get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    return get_member_timeline(db, member_id, limit=limit)


@router.get("/{member_id}/body-composition", response_model=list[BodyCompositionEvaluationRead])
def list_body_composition_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
    limit: int = Query(20, ge=1, le=100),
) -> list[BodyCompositionEvaluationRead]:
    evaluations = list_body_composition_evaluations(db, current_user.gym_id, member_id, limit=limit)
    return serialize_body_composition_evaluations(db, current_user.gym_id, member_id, evaluations)


@router.post("/{member_id}/body-composition/parse-image", response_model=BodyCompositionImageParseResultRead)
async def parse_body_composition_image_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
    file: UploadFile = File(...),
    supplemental_files: list[UploadFile] | None = File(default=None),
    device_profile: str = Form("tezewa_receipt_v1"),
    local_ocr_result: str | None = Form(default=None),
    evaluation_date: date | None = Form(default=None),
    capture_metadata: str | None = Form(default=None),
) -> BodyCompositionImageParseResultRead:
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    parsed_local_ocr = (
        BodyCompositionImageOcrPayload.model_validate_json(local_ocr_result) if local_ocr_result else None
    )
    previous_stmt = select(BodyCompositionEvaluation).where(
        BodyCompositionEvaluation.gym_id == current_user.gym_id,
        BodyCompositionEvaluation.member_id == member_id,
        BodyCompositionEvaluation.deleted_at.is_(None),
    )
    if evaluation_date is not None:
        previous_stmt = previous_stmt.where(BodyCompositionEvaluation.evaluation_date < evaluation_date)
    previous_evaluation = db.scalar(
        previous_stmt.order_by(
            BodyCompositionEvaluation.evaluation_date.desc(),
            BodyCompositionEvaluation.created_at.desc(),
        ).limit(1)
    )
    image_bytes = await file.read()
    received_supplemental_files = supplemental_files or []
    if received_supplemental_files and not settings.body_composition_multi_image_parse_v1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A captura em partes ainda nao esta habilitada para esta implantacao.",
        )
    if len(received_supplemental_files) > 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Envie no maximo tres imagens.")
    supplemental_images = [(await item.read(), item.content_type) for item in received_supplemental_files]
    total_size = len(image_bytes) + sum(len(content) for content, _media_type in supplemental_images)
    if total_size > 20 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="As imagens excedem o limite total de 20 MB.")
    parsed_capture_metadata = (
        BodyCompositionCaptureMetadata.model_validate_json(capture_metadata) if capture_metadata else None
    )
    return parse_body_composition_image(
        image_bytes=image_bytes,
        media_type=file.content_type,
        device_profile=device_profile,
        local_ocr_result=parsed_local_ocr,
        evaluation_date=evaluation_date,
        member_birthdate=getattr(member, "birthdate", None),
        member_sex=getattr(member, "sex_for_clinical_calculation", None),
        member_height_cm=getattr(member, "height_cm", None),
        previous_weight_kg=getattr(previous_evaluation, "weight_kg", None),
        capture_metadata=parsed_capture_metadata,
        supplemental_images=supplemental_images,
    )


@router.post("/{member_id}/body-composition/prepare-image")
async def prepare_body_composition_image_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER)),
    ],
    file: UploadFile = File(...),
    corners: str | None = Form(default=None),
) -> Response:
    """Rectify a receipt in memory and return only the transient JPEG."""
    get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Envie uma imagem JPEG ou PNG.",
        )
    image_bytes = await file.read(MAX_IMAGE_SIZE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="A imagem excede o limite de 8 MB.",
        )

    manual_corners: list[dict[str, float]] | None = None
    if corners:
        try:
            parsed_corners = json.loads(corners)
            if not isinstance(parsed_corners, list) or len(parsed_corners) != 4:
                raise ValueError
            manual_corners = [
                {"x": float(point["x"]), "y": float(point["y"])}
                for point in parsed_corners
                if isinstance(point, dict)
            ]
            if len(manual_corners) != 4 or any(
                point[axis] < 0 or point[axis] > 1
                for point in manual_corners
                for axis in ("x", "y")
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Os quatro cantos informados sao invalidos.",
            ) from exc

    prepared = preprocess_receipt_image(
        image_bytes,
        enabled=True,
        manual_corners=manual_corners,
    )
    if prepared is None or prepared.document_corners is None:
        logger.info(
            "Bioimpedance image preparation could not detect the receipt.",
            extra={"event": "bioimpedance_prepare_blocked", "reason": "document_not_detected"},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nao foi possivel detectar os quatro cantos do comprovante.",
        )

    metadata = {
        "method": prepared.method,
        "confidence": prepared.confidence,
        "corners": prepared.document_corners,
        "quality_codes": prepared.quality_codes,
        "quality_metrics": prepared.quality_metrics,
        "source_width": prepared.source_width,
        "source_height": prepared.source_height,
        "output_width": prepared.output_width,
        "output_height": prepared.output_height,
    }
    logger.info(
        "Bioimpedance image prepared in memory.",
        extra={
            "event": "bioimpedance_image_prepared",
            "method": prepared.method,
            "confidence": prepared.confidence,
            "quality_codes": prepared.quality_codes,
        },
    )
    return Response(
        content=prepared.image_bytes,
        media_type=prepared.media_type,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "X-Cordex-Scan-Metadata": json.dumps(metadata, separators=(",", ":")),
        },
    )


@router.post("/{member_id}/body-composition/capture-event", status_code=status.HTTP_204_NO_CONTENT)
def record_body_composition_capture_event_endpoint(
    member_id: UUID,
    payload: BodyCompositionCaptureEventInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER)),
    ],
) -> Response:
    get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    logger.info(
        "Bioimpedance scanner event.",
        extra={
            "event": f"bioimpedance_{payload.event}",
            "reason": payload.reason,
            "confidence": payload.confidence,
            "quality_codes": payload.quality_codes,
        },
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{member_id}/body-composition/parse-ocr", response_model=BodyCompositionImageParseResultRead)
async def parse_body_composition_ocr_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
    file: UploadFile = File(...),
    device_profile: str = Form("tezewa_receipt_v1"),
    local_ocr_result: str | None = Form(default=None),
    evaluation_date: date | None = Form(default=None),
    capture_metadata: str | None = Form(default=None),
) -> BodyCompositionImageParseResultRead:
    return await parse_body_composition_image_endpoint(
        member_id=member_id,
        db=db,
        current_user=current_user,
        file=file,
        device_profile=device_profile,
        local_ocr_result=local_ocr_result,
        evaluation_date=evaluation_date,
        capture_metadata=capture_metadata,
    )


@router.post("/{member_id}/body-composition", response_model=BodyCompositionEvaluationRead, status_code=status.HTTP_201_CREATED)
def create_body_composition_endpoint(
    member_id: UUID,
    payload: BodyCompositionEvaluationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
    sync_actuar: bool = Query(True),
    idempotency_key: Annotated[UUID | None, Header(alias="Idempotency-Key")] = None,
) -> BodyCompositionEvaluationRead:
    evaluation, _sync_job = create_body_composition_evaluation(
        db,
        current_user.gym_id,
        member_id,
        payload,
        reviewer_user_id=current_user.id,
        sync_actuar=sync_actuar,
        idempotency_key=idempotency_key,
    )
    db.commit()
    db.refresh(evaluation)
    return serialize_body_composition_evaluation(db, current_user.gym_id, member_id, evaluation)


@router.put("/{member_id}/body-composition/{evaluation_id}", response_model=BodyCompositionEvaluationRead)
def update_body_composition_endpoint(
    member_id: UUID,
    evaluation_id: UUID,
    payload: BodyCompositionEvaluationUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
    sync_actuar: bool = Query(True),
) -> BodyCompositionEvaluationRead:
    evaluation, _sync_job = update_body_composition_evaluation(
        db,
        current_user.gym_id,
        member_id,
        evaluation_id,
        payload,
        reviewer_user_id=current_user.id,
        sync_actuar=sync_actuar,
    )
    db.commit()
    db.refresh(evaluation)
    return serialize_body_composition_evaluation(db, current_user.gym_id, member_id, evaluation)


@router.patch("/{member_id}/body-composition/{evaluation_id}", response_model=BodyCompositionEvaluationRead)
def patch_body_composition_endpoint(
    member_id: UUID,
    evaluation_id: UUID,
    payload: BodyCompositionEvaluationUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
    sync_actuar: bool = Query(True),
) -> BodyCompositionEvaluationRead:
    return update_body_composition_endpoint(
        member_id=member_id,
        evaluation_id=evaluation_id,
        payload=payload,
        db=db,
        current_user=current_user,
        sync_actuar=sync_actuar,
    )


@router.get("/{member_id}/body-composition/{evaluation_id}", response_model=BodyCompositionEvaluationRead)
def get_body_composition_detail_endpoint(
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
) -> BodyCompositionEvaluationRead:
    evaluation = get_body_composition_evaluation_or_404(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )
    return serialize_body_composition_evaluation(db, current_user.gym_id, member_id, evaluation)


@router.delete("/{member_id}/body-composition/{evaluation_id}", response_model=APIMessage)
def delete_body_composition_endpoint(
    request: Request,
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.TRAINER))],
) -> APIMessage:
    evaluation = delete_body_composition_evaluation(
        db,
        current_user.gym_id,
        member_id,
        evaluation_id,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="body_composition_evaluation_deleted",
        entity="body_composition_evaluation",
        user=current_user,
        member_id=member_id,
        entity_id=evaluation_id,
        details={
            "evaluation_date": evaluation.evaluation_date.isoformat(),
            "source": evaluation.source,
            "recoverable": True,
            "deleted_at": evaluation.deleted_at.isoformat(),
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return APIMessage(message="Avaliacao de bioimpedancia excluida")


@router.post("/{member_id}/body-composition/{evaluation_id}/review", response_model=BodyCompositionEvaluationRead)
def review_body_composition_endpoint(
    member_id: UUID,
    evaluation_id: UUID,
    payload: BodyCompositionEvaluationReviewInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
    sync_actuar: bool = Query(True),
) -> BodyCompositionEvaluationRead:
    evaluation, _sync_job = review_body_composition_evaluation(
        db,
        current_user.gym_id,
        member_id,
        evaluation_id,
        payload,
        reviewer_user_id=current_user.id,
        sync_actuar=sync_actuar,
    )
    db.commit()
    db.refresh(evaluation)
    return serialize_body_composition_evaluation(db, current_user.gym_id, member_id, evaluation)


@router.get("/{member_id}/body-composition/{evaluation_id}/report", response_model=BodyCompositionReportRead)
def get_body_composition_report_endpoint(
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
) -> BodyCompositionReportRead:
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    evaluation = get_body_composition_evaluation_or_404(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )
    history = list_body_composition_evaluations(db, current_user.gym_id, member_id, limit=100)
    return build_body_composition_report_payload(member, evaluation, history=history)


@router.get("/{member_id}/body-composition/{evaluation_id}/pdf")
def export_body_composition_pdf_endpoint(
    request: Request,
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> Response:
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    evaluation = get_body_composition_evaluation_or_404(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )
    previous_evaluation = _get_previous_body_composition_evaluation(db, member_id=member_id, evaluation_id=evaluation_id)
    pdf_bytes, filename = generate_body_composition_pdf(member, evaluation, previous_evaluation)
    context = get_request_context(request)
    logger.info(
        "body_composition_pdf_export layout=%s kind=member_summary member_id=%s evaluation_id=%s bytes=%s filename=%s",
        BODY_COMPOSITION_PDF_LAYOUT_VERSION,
        member_id,
        evaluation_id,
        len(pdf_bytes),
        filename,
    )
    log_audit_event(
        db,
        action="body_composition_summary_pdf_exported",
        entity="body_composition",
        user=current_user,
        member_id=member_id,
        entity_id=evaluation_id,
        details={"filename": filename, "kind": "member_summary"},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Report-Layout-Version": BODY_COMPOSITION_PDF_LAYOUT_VERSION,
            "X-Report-Scope": "member_summary",
        },
    )


@router.get("/{member_id}/body-composition/{evaluation_id}/technical-pdf")
def export_body_composition_technical_pdf_endpoint(
    request: Request,
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> Response:
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    evaluation = get_body_composition_evaluation_or_404(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )
    previous_evaluation = _get_previous_body_composition_evaluation(db, member_id=member_id, evaluation_id=evaluation_id)
    pdf_bytes, filename = generate_body_composition_technical_pdf(member, evaluation, previous_evaluation)
    context = get_request_context(request)
    logger.info(
        "body_composition_pdf_export layout=%s kind=technical member_id=%s evaluation_id=%s bytes=%s filename=%s",
        BODY_COMPOSITION_PDF_LAYOUT_VERSION,
        member_id,
        evaluation_id,
        len(pdf_bytes),
        filename,
    )
    log_audit_event(
        db,
        action="body_composition_technical_pdf_exported",
        entity="body_composition",
        user=current_user,
        member_id=member_id,
        entity_id=evaluation_id,
        details={"filename": filename, "kind": "technical"},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Report-Layout-Version": BODY_COMPOSITION_PDF_LAYOUT_VERSION,
            "X-Report-Scope": "technical",
        },
    )


@router.post(
    "/{member_id}/body-composition/{evaluation_id}/actuar-sync",
    response_model=BodyCompositionActuarSyncStatusRead,
)
def enqueue_body_composition_actuar_sync_endpoint(
    request: Request,
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> BodyCompositionActuarSyncStatusRead:
    job = create_body_composition_sync_job(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
        created_by_user_id=current_user.id,
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sync Actuar desabilitado para esta academia ou ambiente.",
        )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="actuar_sync_job_requested",
        entity="body_composition",
        user=current_user,
        member_id=member_id,
        entity_id=evaluation_id,
        details={"job_id": str(job.id) if job else None},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return get_body_composition_sync_status(db, gym_id=current_user.gym_id, member_id=member_id, evaluation_id=evaluation_id)


@router.post(
    "/{member_id}/body-composition/{evaluation_id}/retry-actuar-sync",
    response_model=BodyCompositionActuarSyncStatusRead,
)
def retry_body_composition_actuar_sync_endpoint(
    request: Request,
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> BodyCompositionActuarSyncStatusRead:
    evaluation, job = schedule_body_composition_sync_retry(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="actuar_sync_job_requeued",
        entity="body_composition",
        user=current_user,
        member_id=member_id,
        entity_id=evaluation.id,
        details={"job_id": str(job.id)},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return get_body_composition_sync_status(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )


@router.get(
    "/{member_id}/body-composition/{evaluation_id}/actuar-sync-status",
    response_model=BodyCompositionActuarSyncStatusRead,
)
def get_body_composition_actuar_sync_status_endpoint(
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
) -> BodyCompositionActuarSyncStatusRead:
    return get_body_composition_sync_status(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )


@router.get(
    "/{member_id}/body-composition/{evaluation_id}/manual-sync-summary",
    response_model=BodyCompositionManualSyncSummaryRead,
)
def get_body_composition_manual_sync_summary_endpoint(
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
) -> BodyCompositionManualSyncSummaryRead:
    return get_body_composition_manual_sync_summary(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
    )


@router.post(
    "/{member_id}/body-composition/{evaluation_id}/send-whatsapp",
    response_model=BodyCompositionWhatsAppDispatchRead,
)
def send_body_composition_whatsapp_endpoint(
    request: Request,
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> BodyCompositionWhatsAppDispatchRead:
    try:
        log = send_body_composition_whatsapp_summary(
            db,
            gym_id=current_user.gym_id,
            member_id=member_id,
            evaluation_id=evaluation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    context = get_request_context(request)
    log_audit_event(
        db,
        action="body_composition_whatsapp_sent",
        entity="body_composition",
        user=current_user,
        member_id=member_id,
        entity_id=evaluation_id,
        details={"status": log.status, "pdf_filename": (log.extra_data or {}).get("file_name")},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(log)
    return BodyCompositionWhatsAppDispatchRead(
        log_id=log.id,
        member_id=member_id,
        evaluation_id=evaluation_id,
        status=log.status,
        recipient=log.recipient,
        pdf_filename=(log.extra_data or {}).get("file_name"),
        error_detail=log.error_detail,
    )


@router.post(
    "/{member_id}/body-composition/{evaluation_id}/send-kommo",
    response_model=BodyCompositionKommoDispatchRead,
)
def send_body_composition_kommo_endpoint(
    request: Request,
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> BodyCompositionKommoDispatchRead:
    try:
        outbound = send_body_composition_kommo_salesbot(
            db,
            gym_id=current_user.gym_id,
            member_id=member_id,
            evaluation_id=evaluation_id,
            pdf_kind="technical",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except KommoSalesbotDispatchError as exc:
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except KommoServiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if outbound.status not in {"queued", "sent"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=outbound.detail or "A Kommo nao recebeu o envio desta bioimpedancia.")

    context = get_request_context(request)
    log_audit_event(
        db,
        action="body_composition_kommo_salesbot_queued",
        entity="body_composition",
        user=current_user,
        member_id=member_id,
        entity_id=evaluation_id,
        details={
            "status": outbound.status,
            "lead_id": outbound.lead_id,
            "contact_id": outbound.contact_id,
            "salesbot_id": outbound.salesbot_id,
            "message_log_id": str(outbound.message_log_id) if outbound.message_log_id else None,
            "pdf_url": outbound.pdf_url,
            "kommo_file_uuid": outbound.kommo_file_uuid,
            "file_upload_status": outbound.file_upload_status,
            "file_attach_status": outbound.file_attach_status,
            "pdf_delivery_mode": outbound.pdf_delivery_mode,
            "route_kind": getattr(outbound, "route_kind", None),
            "trainer_user_id": str(outbound.trainer_user_id) if getattr(outbound, "trainer_user_id", None) else None,
            "route_fallback_reason": getattr(outbound, "route_fallback_reason", None),
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
        flush=False,
    )
    db.commit()
    return BodyCompositionKommoDispatchRead(
        member_id=member_id,
        evaluation_id=evaluation_id,
        status=outbound.status,
        lead_id=outbound.lead_id,
        contact_id=outbound.contact_id,
        task_id=None,
        detail=outbound.detail,
        delivery_mode=outbound.delivery_mode,
        salesbot_id=outbound.salesbot_id,
        message_log_id=outbound.message_log_id,
        pdf_url=outbound.pdf_url,
        kommo_file_uuid=outbound.kommo_file_uuid,
        file_upload_status=outbound.file_upload_status,
        file_attach_status=outbound.file_attach_status,
        pdf_delivery_mode=outbound.pdf_delivery_mode,
        fallback_available=outbound.fallback_available,
        route_kind=getattr(outbound, "route_kind", None),
        trainer_user_id=getattr(outbound, "trainer_user_id", None),
        route_fallback_reason=getattr(outbound, "route_fallback_reason", None),
    )


@router.post(
    "/{member_id}/body-composition/{evaluation_id}/prepare-kommo",
    response_model=BodyCompositionKommoDispatchRead,
)
def prepare_body_composition_kommo_endpoint(
    request: Request,
    member_id: UUID,
    evaluation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> BodyCompositionKommoDispatchRead:
    try:
        handoff = send_body_composition_kommo_handoff(
            db,
            gym_id=current_user.gym_id,
            member_id=member_id,
            evaluation_id=evaluation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except KommoServiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if handoff.status != "sent":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=handoff.detail or "A Kommo nao recebeu o handoff desta bioimpedancia.")

    context = get_request_context(request)
    log_audit_event(
        db,
        action="body_composition_kommo_handoff_prepared",
        entity="body_composition",
        user=current_user,
        member_id=member_id,
        entity_id=evaluation_id,
        details={
            "status": handoff.status,
            "lead_id": handoff.lead_id,
            "contact_id": handoff.contact_id,
            "task_id": handoff.task_id,
        },
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return BodyCompositionKommoDispatchRead(
        member_id=member_id,
        evaluation_id=evaluation_id,
        status=handoff.status,
        lead_id=handoff.lead_id,
        contact_id=handoff.contact_id,
        task_id=handoff.task_id,
        detail=handoff.detail,
        delivery_mode="handoff_task",
        fallback_available=False,
    )


@router.put("/{member_id}/actuar-link", response_model=ActuarMemberLinkRead)
def upsert_member_actuar_link_endpoint(
    request: Request,
    member_id: UUID,
    payload: ActuarMemberLinkUpsert,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> ActuarMemberLinkRead:
    link = upsert_body_composition_actuar_link(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        user_id=current_user.id,
        actuar_external_id=payload.actuar_external_id,
        actuar_search_name=payload.actuar_search_name,
        actuar_search_document=payload.actuar_search_document,
        actuar_search_birthdate=payload.actuar_search_birthdate,
        match_confidence=payload.match_confidence,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="actuar_member_link_upserted",
        entity="actuar_member_link",
        user=current_user,
        member_id=member_id,
        entity_id=link.id,
        details={"actuar_external_id": payload.actuar_external_id},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return ActuarMemberLinkRead.model_validate(link)


@router.post(
    "/{member_id}/body-composition/{evaluation_id}/manual-sync-confirm",
    response_model=BodyCompositionActuarSyncStatusRead,
)
def confirm_body_composition_manual_sync_endpoint(
    request: Request,
    member_id: UUID,
    evaluation_id: UUID,
    payload: ActuarManualSyncConfirmInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> BodyCompositionActuarSyncStatusRead:
    evaluation = confirm_manual_actuar_sync(
        db,
        gym_id=current_user.gym_id,
        member_id=member_id,
        evaluation_id=evaluation_id,
        confirmed_by_user_id=current_user.id,
        reason=payload.reason,
        note=payload.note,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="actuar_manual_sync_confirmed",
        entity="body_composition",
        user=current_user,
        member_id=member_id,
        entity_id=evaluation.id,
        details={"reason": payload.reason, "note": payload.note or ""},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return get_body_composition_sync_status(db, gym_id=current_user.gym_id, member_id=member_id, evaluation_id=evaluation_id)


def _get_previous_body_composition_evaluation(
    db: Session,
    *,
    member_id: UUID,
    evaluation_id: UUID,
) -> BodyCompositionEvaluation | None:
    return db.scalar(
        select(BodyCompositionEvaluation)
        .where(
            BodyCompositionEvaluation.member_id == member_id,
            BodyCompositionEvaluation.id != evaluation_id,
            BodyCompositionEvaluation.deleted_at.is_(None),
        )
        .order_by(desc(BodyCompositionEvaluation.evaluation_date), desc(BodyCompositionEvaluation.created_at))
        .limit(1)
    )


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
