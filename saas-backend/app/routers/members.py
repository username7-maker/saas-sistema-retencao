import logging
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.core.cache import invalidate_dashboard_cache
from app.database import get_db
from app.models import BodyCompositionEvaluation, MemberStatus, RiskLevel, RoleEnum, User
from app.schemas import (
    APIMessage,
    MemberCreate,
    MemberOut,
    MemberUpdate,
    OnboardingScoreSnapshotOut,
    OnboardingScoreOut,
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
    BodyCompositionImageOcrPayload,
    BodyCompositionImageParseResultRead,
    BodyCompositionKommoDispatchRead,
    BodyCompositionManualSyncSummaryRead,
    BodyCompositionReportRead,
    BodyCompositionWhatsAppDispatchRead,
    BodyCompositionEvaluationUpdate,
)
from app.services.audit_service import log_audit_event
from app.services.body_composition_actuar_sync_service import (
    confirm_manual_actuar_sync,
    create_body_composition_sync_job,
    get_body_composition_evaluation_or_404,
    get_body_composition_sync_status,
    get_body_composition_manual_sync_summary,
    schedule_body_composition_sync_retry,
    upsert_body_composition_actuar_link,
)
from app.services.body_composition_image_parse_service import parse_body_composition_image
from app.services.body_composition_delivery_service import (
    build_body_composition_report_payload,
    generate_body_composition_pdf,
    generate_body_composition_technical_pdf,
    send_body_composition_kommo_handoff,
    send_body_composition_whatsapp_summary,
)
from app.services.body_composition_service import (
    create_body_composition_evaluation,
    list_body_composition_evaluations,
    review_body_composition_evaluation,
    serialize_body_composition_evaluation,
    serialize_body_composition_evaluations,
    update_body_composition_evaluation,
)
from app.services.ai_assistant_service import build_onboarding_assistant
from app.services.kommo_service import KommoServiceError
from app.services.member_service import create_member, get_member_or_404, list_member_index, list_members, soft_delete_member, update_member
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
BODY_COMPOSITION_PDF_LAYOUT_VERSION = "clinical-a4-sidebar-fit-2026-04-15b"


class PreferredShiftSyncResult(BaseModel):
    updated_count: int
    message: str


@router.post("/", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def create_member_endpoint(
    request: Request,
    payload: MemberCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
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
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    risk_level: RiskLevel | None = None,
    status: MemberStatus | None = None,
    plan_cycle: Literal["monthly", "semiannual", "annual"] | None = None,
    preferred_shift: Literal["morning", "afternoon", "evening"] | None = None,
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
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
    search: str | None = None,
    risk_level: RiskLevel | None = None,
    status: MemberStatus | None = None,
    plan_cycle: Literal["monthly", "semiannual", "annual"] | None = None,
    preferred_shift: Literal["morning", "afternoon", "evening"] | None = None,
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
    members = list_member_index(
        db,
        gym_id=current_user.gym_id,
        status=MemberStatus.ACTIVE,
    )
    payload: list[OnboardingScoreSnapshotOut] = []
    for member in members:
        join_date = getattr(member, "join_date", None)
        onboarding_status = getattr(member, "onboarding_status", None)
        if join_date is None:
            continue
        days_since_join = (datetime.now().date() - join_date).days
        if days_since_join < 0 or days_since_join > 30:
            continue
        if onboarding_status not in {"active", "at_risk"}:
            continue
        score_payload = calculate_onboarding_score(db, member)
        payload.append(
            OnboardingScoreSnapshotOut(
                member_id=member.id,
                score=int(score_payload["score"]),
                status=str(score_payload["status"]),
            )
        )
    return payload


@router.get("/{member_id}", response_model=MemberOut)
def get_member_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON, RoleEnum.TRAINER))],
) -> MemberOut:
    return get_member_or_404(db, member_id, gym_id=current_user.gym_id)


@router.patch("/{member_id}", response_model=MemberOut)
def update_member_endpoint(
    request: Request,
    member_id: UUID,
    payload: MemberUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
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
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> OnboardingScoreOut:
    member = get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    payload = calculate_onboarding_score(db, member)
    return OnboardingScoreOut(**payload, assistant=build_onboarding_assistant(member, payload))


@router.get("/{member_id}/timeline")
def member_timeline_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
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
    device_profile: str = Form("tezewa_receipt_v1"),
    local_ocr_result: str | None = Form(default=None),
) -> BodyCompositionImageParseResultRead:
    get_member_or_404(db, member_id, gym_id=current_user.gym_id)
    parsed_local_ocr = BodyCompositionImageOcrPayload.model_validate_json(local_ocr_result) if local_ocr_result else None
    image_bytes = await file.read()
    return parse_body_composition_image(
        image_bytes=image_bytes,
        media_type=file.content_type,
        device_profile=device_profile,
        local_ocr_result=parsed_local_ocr,
    )


@router.post("/{member_id}/body-composition/parse-ocr", response_model=BodyCompositionImageParseResultRead)
async def parse_body_composition_ocr_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
    file: UploadFile = File(...),
    device_profile: str = Form("tezewa_receipt_v1"),
    local_ocr_result: str | None = Form(default=None),
) -> BodyCompositionImageParseResultRead:
    return await parse_body_composition_image_endpoint(
        member_id=member_id,
        db=db,
        current_user=current_user,
        file=file,
        device_profile=device_profile,
        local_ocr_result=local_ocr_result,
    )


@router.post("/{member_id}/body-composition", response_model=BodyCompositionEvaluationRead, status_code=status.HTTP_201_CREATED)
def create_body_composition_endpoint(
    member_id: UUID,
    payload: BodyCompositionEvaluationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> BodyCompositionEvaluationRead:
    evaluation, _sync_job = create_body_composition_evaluation(
        db,
        current_user.gym_id,
        member_id,
        payload,
        reviewer_user_id=current_user.id,
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
) -> BodyCompositionEvaluationRead:
    evaluation, _sync_job = update_body_composition_evaluation(
        db,
        current_user.gym_id,
        member_id,
        evaluation_id,
        payload,
        reviewer_user_id=current_user.id,
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
) -> BodyCompositionEvaluationRead:
    return update_body_composition_endpoint(
        member_id=member_id,
        evaluation_id=evaluation_id,
        payload=payload,
        db=db,
        current_user=current_user,
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


@router.post("/{member_id}/body-composition/{evaluation_id}/review", response_model=BodyCompositionEvaluationRead)
def review_body_composition_endpoint(
    member_id: UUID,
    evaluation_id: UUID,
    payload: BodyCompositionEvaluationReviewInput,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.TRAINER))],
) -> BodyCompositionEvaluationRead:
    evaluation, _sync_job = review_body_composition_evaluation(
        db,
        current_user.gym_id,
        member_id,
        evaluation_id,
        payload,
        reviewer_user_id=current_user.id,
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
        action="body_composition_kommo_sent",
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
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
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
