from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AutopilotAction, AutopilotEvent, Gym, Member, MemberStatus, MessageLog, MovementVideoReview
from app.schemas.student_personal_ai import (
    StudentPersonalAiDraftOut,
    StudentPersonalAiPrepareResultOut,
    StudentPersonalAiSettingsOut,
    StudentPersonalAiSettingsUpdate,
)
from app.services.autopilot_event_service import record_event
from app.services.autopilot_settings_service import get_or_create_autopilot_settings
from app.services.compliance_service import current_consent_status_map
from app.services.kommo_service import handoff_member_to_kommo, is_kommo_ready
from app.services.personal_ai_service import (
    _build_personal_ai_reply,
    _requires_active_member_for_personal_ai,
    build_personal_ai_context,
    classify_personal_ai_request,
)

STUDENT_PERSONAL_AI_EXTRA_KEY = "student_personal_ai"
STUDENT_PERSONAL_AI_ACTION_TYPE = "student_personal_ai_kommo_draft"
STUDENT_PERSONAL_AI_DRAFT_READY = "draft_ready"

DEFAULT_STUDENT_PERSONAL_AI_SETTINGS = {
    "enabled": False,
    "mode": "draft_only",
    "auto_send_enabled": False,
    "kommo_required": True,
    "personal_ai_enabled": True,
    "movement_video_enabled": True,
    "require_member_match": True,
    "require_communication_consent": True,
    "require_image_consent_for_video": True,
    "sensitive_escalation_enabled": True,
    "max_drafts_per_day": 50,
    "human_recent_activity_cooldown_hours": 24,
    "allowed_domains": [
        "training_guidance",
        "routine_support",
        "assessment_explanation",
        "body_composition_explanation",
        "movement_video",
    ],
}

TECHNICAL_TERMS = (
    "treino",
    "exercicio",
    "exercÃ­cio",
    "carga",
    "serie",
    "sÃ©rie",
    "avaliacao",
    "avaliaÃ§Ã£o",
    "bioimpedancia",
    "bioimpedÃ¢ncia",
    "gordura",
    "massa muscular",
    "imc",
    "rotina",
    "professor",
    "personal",
    "video",
    "vÃ­deo",
)
VIDEO_MEDIA_TYPES = {"video/mp4", "video/quicktime", "video/webm", "video/mov"}
VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".m4v")
STUDENT_OPT_OUT_TERMS = ("parar", "remover", "sair da lista", "nao autorizo", "nÃ£o autorizo", "sem mensagem", "opt-out")
STUDENT_HUMAN_TERMS = ("humano", "gerente", "responsavel", "responsÃ¡vel", "atendente", "falar com alguem", "falar com alguÃ©m")
STUDENT_FINANCE_DISPUTE_TERMS = ("ja paguei", "jÃ¡ paguei", "cobranca indevida", "cobranÃ§a indevida", "chargeback", "nao reconheco")


@dataclass(frozen=True)
class KommoMediaReference:
    media_url: str | None
    media_type: str | None
    file_size_bytes: int | None
    duration_seconds: int | None
    caption: str | None
    provider_media_id: str | None
    is_video: bool


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def get_student_personal_ai_settings(db: Session, *, gym_id: UUID) -> StudentPersonalAiSettingsOut:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    payload = _merge_settings((settings.extra_data or {}).get(STUDENT_PERSONAL_AI_EXTRA_KEY))
    return StudentPersonalAiSettingsOut(**payload)


def update_student_personal_ai_settings(
    db: Session,
    *,
    gym_id: UUID,
    payload: StudentPersonalAiSettingsUpdate,
) -> StudentPersonalAiSettingsOut:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    current = _merge_settings((settings.extra_data or {}).get(STUDENT_PERSONAL_AI_EXTRA_KEY))
    updates = payload.model_dump(exclude_unset=True)
    updates["auto_send_enabled"] = False
    updates["mode"] = "draft_only"
    current.update(updates)
    current = _merge_settings(current)

    extra = dict(settings.extra_data or {})
    extra[STUDENT_PERSONAL_AI_EXTRA_KEY] = current
    settings.extra_data = extra
    db.add(settings)
    db.flush()
    return StudentPersonalAiSettingsOut(**current)


def process_kommo_inbound_for_student_personal_ai(
    db: Session,
    *,
    gym_id: UUID,
    member: Member,
    message_text: str,
    event: AutopilotEvent,
    payload: dict[str, Any] | None = None,
    message_log_id: UUID | None = None,
    kommo_contact_id: str | None = None,
    kommo_lead_id: str | None = None,
    flush: bool = True,
) -> StudentPersonalAiDraftOut | None:
    media = extract_kommo_media_reference(payload or {}, fallback_caption=message_text)
    if not media.is_video and not is_student_personal_ai_candidate(message_text):
        return None

    settings = get_student_personal_ai_settings(db, gym_id=gym_id)
    if not settings.enabled:
        return None
    if media.is_video:
        return _process_video_message(
            db,
            gym_id=gym_id,
            member=member,
            message_text=message_text,
            event=event,
            media=media,
            settings=settings,
            message_log_id=message_log_id,
            kommo_contact_id=kommo_contact_id,
            kommo_lead_id=kommo_lead_id,
            flush=flush,
        )
    return _process_text_message(
        db,
        gym_id=gym_id,
        member=member,
        message_text=message_text,
        event=event,
        settings=settings,
        message_log_id=message_log_id,
        kommo_contact_id=kommo_contact_id,
        kommo_lead_id=kommo_lead_id,
        flush=flush,
    )


def is_student_personal_ai_candidate(message_text: str) -> bool:
    normalized = _normalize_text(message_text)
    return bool(normalized) and any(term in normalized for term in TECHNICAL_TERMS)


def list_student_personal_ai_drafts(
    db: Session,
    *,
    gym_id: UUID,
    status_filter: str | None = None,
    member_id: UUID | None = None,
    limit: int = 50,
) -> list[StudentPersonalAiDraftOut]:
    query = select(AutopilotAction).where(
        AutopilotAction.gym_id == gym_id,
        AutopilotAction.action_type == STUDENT_PERSONAL_AI_ACTION_TYPE,
    )
    if status_filter:
        query = query.where(AutopilotAction.status == status_filter)
    if member_id:
        query = query.where(AutopilotAction.member_id == member_id)
    actions = db.scalars(query.order_by(AutopilotAction.created_at.desc()).limit(limit)).all()
    return [serialize_student_personal_ai_draft(action) for action in actions]


def prepare_student_personal_ai_draft_in_kommo(
    db: Session,
    *,
    gym_id: UUID,
    draft_id: UUID,
    flush: bool = True,
) -> StudentPersonalAiPrepareResultOut:
    action = _get_action_or_404(db, gym_id=gym_id, draft_id=draft_id)
    if action.status != STUDENT_PERSONAL_AI_DRAFT_READY:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este rascunho do aluno nao esta pronto para Kommo.")
    member = db.get(Member, action.member_id) if action.member_id else None
    if member is None or member.gym_id != gym_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno do rascunho nao encontrado.")

    metadata = dict(action.metadata_json or {})
    summary = "\n".join(
        [
            "Personal IA do aluno via Kommo V1 - revisar antes de responder.",
            f"Mensagem do aluno: {metadata.get('received_message') or '-'}",
            f"Resumo: {metadata.get('summary') or '-'}",
            f"Resposta sugerida: {action.message_body or metadata.get('draft_reply') or '-'}",
            f"Proxima acao: {metadata.get('next_action') or '-'}",
            f"Evidencias: {', '.join(metadata.get('evidence') or []) or '-'}",
            f"Review de video: {metadata.get('movement_video_review_id') or '-'}",
        ]
    )
    result = handoff_member_to_kommo(
        db,
        gym_id=gym_id,
        member=member,
        title=f"Responder Personal IA - {member.full_name}"[:120],
        summary=summary,
        source="student_personal_ai",
        due_in_hours=4,
    )
    if result.status != "sent":
        action.status = "failed"
        action.failure_reason = result.detail or result.status
        db.add(action)
        record_event(
            db,
            gym_id=gym_id,
            event_type="student_personal_ai_prepare_kommo_failed",
            source="student_personal_ai",
            member_id=member.id,
            autopilot_action_id=action.id,
            metadata={"status": result.status, "detail": result.detail},
            flush=False,
        )
        if flush:
            db.flush()
        return StudentPersonalAiPrepareResultOut(draft=serialize_student_personal_ai_draft(action), detail=result.detail or result.status)

    metadata.update(
        {
            "kommo_contact_id": result.contact_id,
            "kommo_lead_id": result.lead_id,
            "kommo_task_id": result.task_id,
            "prepared_at": _now().isoformat(),
            "student_personal_ai_state": "waiting_human_review",
        }
    )
    action.status = "awaiting_outcome"
    action.metadata_json = metadata
    db.add(action)
    _record_kommo_handoff_log(db, action=action, member=member, result=result)
    record_event(
        db,
        gym_id=gym_id,
        event_type="student_personal_ai_prepared_kommo",
        source="student_personal_ai",
        member_id=member.id,
        autopilot_action_id=action.id,
        metadata={
            "kommo_contact_id": result.contact_id,
            "kommo_lead_id": result.lead_id,
            "kommo_task_id": result.task_id,
        },
        flush=False,
    )
    if flush:
        db.flush()
    return StudentPersonalAiPrepareResultOut(
        draft=serialize_student_personal_ai_draft(action),
        detail="Rascunho do aluno preparado na Kommo para revisao humana.",
        kommo_contact_id=result.contact_id,
        kommo_lead_id=result.lead_id,
        kommo_task_id=result.task_id,
    )


def reject_student_personal_ai_draft(
    db: Session,
    *,
    gym_id: UUID,
    draft_id: UUID,
    reason: str,
    flush: bool = True,
) -> StudentPersonalAiDraftOut:
    action = _get_action_or_404(db, gym_id=gym_id, draft_id=draft_id)
    metadata = dict(action.metadata_json or {})
    metadata["rejection_reason"] = reason
    metadata["student_personal_ai_state"] = "rejected"
    action.status = "cancelled"
    action.outcome = "rejected"
    action.completed_at = _now()
    action.metadata_json = metadata
    db.add(action)
    record_event(
        db,
        gym_id=gym_id,
        event_type="student_personal_ai_draft_rejected",
        source="student_personal_ai",
        member_id=action.member_id,
        autopilot_action_id=action.id,
        metadata={"reason": reason},
        flush=False,
    )
    if flush:
        db.flush()
    return serialize_student_personal_ai_draft(action)


def serialize_student_personal_ai_draft(action: AutopilotAction) -> StudentPersonalAiDraftOut:
    metadata = dict(action.metadata_json or {})
    return StudentPersonalAiDraftOut(
        id=action.id,
        status=action.status,
        gym_id=action.gym_id,
        member_id=action.member_id,
        lead_id=action.lead_id,
        intent=str(metadata.get("intent") or action.domain or "routine_support"),
        sensitivity=str(metadata.get("sensitivity") or "normal"),
        summary=str(metadata.get("summary") or action.policy_key),
        draft_reply=action.message_body or metadata.get("draft_reply"),
        next_action=str(metadata.get("next_action") or "Professor revisa e responde pela Kommo."),
        recommended_owner_role=str(metadata.get("recommended_owner_role") or "coach"),
        blocked_reasons=list(metadata.get("blocked_reasons") or []),
        evidence=list(metadata.get("evidence") or []),
        received_message=metadata.get("received_message"),
        source_event_id=metadata.get("source_event_id"),
        message_log_id=metadata.get("message_log_id"),
        movement_video_review_id=metadata.get("movement_video_review_id"),
        kommo_contact_id=metadata.get("kommo_contact_id"),
        kommo_lead_id=metadata.get("kommo_lead_id"),
        kommo_task_id=metadata.get("kommo_task_id"),
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


def extract_kommo_media_reference(payload: dict[str, Any], *, fallback_caption: str | None = None) -> KommoMediaReference:
    media_type = _first_nested_string(payload, {"media_type", "mime_type", "mimetype", "content_type", "file_type", "type"})
    media_url = _first_nested_string(payload, {"media_url", "file_url", "attachment_url", "video_url", "url", "link", "download_url"})
    provider_media_id = _first_nested_string(payload, {"media_id", "file_id", "attachment_id", "provider_media_id", "uuid"})
    caption = _first_nested_string(payload, {"caption", "message", "text", "body", "comment"}) or fallback_caption
    file_size = _first_nested_int(payload, {"file_size", "file_size_bytes", "size", "bytes"})
    duration = _first_nested_int(payload, {"duration", "duration_seconds", "video_duration"})
    normalized_type = (media_type or "").lower()
    normalized_url = (media_url or "").lower()
    is_video = (
        normalized_type.startswith("video/")
        or normalized_type in VIDEO_MEDIA_TYPES
        or normalized_url.endswith(VIDEO_EXTENSIONS)
        or bool(_first_nested_value(payload, {"video", "videos"}))
    )
    return KommoMediaReference(
        media_url=media_url,
        media_type=media_type,
        file_size_bytes=file_size,
        duration_seconds=duration,
        caption=caption,
        provider_media_id=provider_media_id,
        is_video=is_video,
    )


def _process_text_message(
    db: Session,
    *,
    gym_id: UUID,
    member: Member,
    message_text: str,
    event: AutopilotEvent,
    settings: StudentPersonalAiSettingsOut,
    message_log_id: UUID | None,
    kommo_contact_id: str | None,
    kommo_lead_id: str | None,
    flush: bool,
) -> StudentPersonalAiDraftOut:
    idempotency_key = f"student-personal-ai:kommo-inbound:{event.id}:text"
    existing = _get_existing_action(db, gym_id=gym_id, idempotency_key=idempotency_key)
    if existing:
        return serialize_student_personal_ai_draft(existing)

    gym = db.get(Gym, gym_id)
    classification = classify_personal_ai_request(message_text)
    sensitive_override = _student_sensitive_override(message_text)
    intent = sensitive_override[0] if sensitive_override else classification.intent
    sensitivity = "sensitive" if sensitive_override else classification.sensitivity
    summary = sensitive_override[1] if sensitive_override else classification.summary
    next_action = sensitive_override[2] if sensitive_override else classification.next_action
    owner_role = sensitive_override[3] if sensitive_override else classification.recommended_owner_role
    context = build_personal_ai_context(db, gym_id=gym_id, member_id=member.id)
    blocked_reasons = list(classification.blocked_reasons)
    if sensitive_override:
        blocked_reasons.append(f"sensitive_{intent}")
    blocked_reasons.extend(
        _common_blocked_reasons(
            db,
            gym=gym,
            member=member,
            settings=settings,
            require_communication_consent=True,
        )
    )
    if not settings.personal_ai_enabled:
        blocked_reasons.append("student_personal_ai_text_disabled")
    if intent not in settings.allowed_domains and sensitivity != "sensitive":
        blocked_reasons.append("domain_disabled")
    if member.status != MemberStatus.ACTIVE and _requires_active_member_for_personal_ai(intent):
        blocked_reasons.append("member_not_active")
    if intent in {"training_guidance", "routine_support"} and not context.active_training_plan:
        blocked_reasons.append("missing_active_training_plan")
    if intent in {"training_guidance", "assessment_explanation", "body_composition_explanation"} and (
        not context.latest_assessment and not context.latest_body_composition
    ):
        blocked_reasons.append("missing_technical_baseline")
    if _drafts_created_today(db, gym_id=gym_id) >= settings.max_drafts_per_day:
        blocked_reasons.append("daily_draft_limit_reached")

    status_value = "escalated" if sensitivity == "sensitive" else STUDENT_PERSONAL_AI_DRAFT_READY
    if blocked_reasons:
        status_value = "escalated" if sensitivity == "sensitive" else "blocked"
    draft_reply = None if blocked_reasons or sensitivity == "sensitive" else _build_personal_ai_reply(
        member=member,
        context=context,
        intent=intent,
    )
    metadata = {
        "student_personal_ai_state": status_value,
        "intent": intent,
        "sensitivity": sensitivity,
        "summary": summary,
        "draft_reply": draft_reply,
        "next_action": next_action,
        "recommended_owner_role": owner_role,
        "blocked_reasons": sorted(set(blocked_reasons)),
        "evidence": sorted(set([*classification.evidence, *context.evidence, "kommo_inbound", "student_message"])),
        "received_message": message_text,
        "source_event_id": str(event.id),
        "message_log_id": str(message_log_id) if message_log_id else None,
        "kommo_contact_id": kommo_contact_id,
        "kommo_lead_id": kommo_lead_id,
        "context_snapshot": context.model_dump(mode="json"),
        "mode": "draft_only",
        "auto_send_enabled": False,
    }
    action = AutopilotAction(
        gym_id=gym_id,
        policy_key=f"student_personal_ai_{intent}",
        domain="trainer",
        action_type=STUDENT_PERSONAL_AI_ACTION_TYPE,
        status=status_value,
        member_id=member.id,
        channel="kommo",
        template_key=f"student_personal_ai_{intent}",
        message_body=draft_reply,
        timeout_at=_now() + timedelta(hours=48),
        max_attempts=1,
        idempotency_key=idempotency_key,
        failure_reason=",".join(sorted(set(blocked_reasons))) if blocked_reasons else None,
        escalation_reason=summary if status_value == "escalated" else None,
        metadata_json=metadata,
    )
    db.add(action)
    db.flush()
    _record_student_action_event(db, action=action, event_type=status_value, source_event_id=event.id)
    if flush:
        db.flush()
    return serialize_student_personal_ai_draft(action)


def _process_video_message(
    db: Session,
    *,
    gym_id: UUID,
    member: Member,
    message_text: str,
    event: AutopilotEvent,
    media: KommoMediaReference,
    settings: StudentPersonalAiSettingsOut,
    message_log_id: UUID | None,
    kommo_contact_id: str | None,
    kommo_lead_id: str | None,
    flush: bool,
) -> StudentPersonalAiDraftOut:
    idempotency_key = f"student-personal-ai:kommo-inbound:{event.id}:video"
    existing = _get_existing_action(db, gym_id=gym_id, idempotency_key=idempotency_key)
    if existing:
        return serialize_student_personal_ai_draft(existing)

    gym = db.get(Gym, gym_id)
    blocked_reasons = _common_blocked_reasons(
        db,
        gym=gym,
        member=member,
        settings=settings,
        require_communication_consent=True,
    )
    if not settings.movement_video_enabled:
        blocked_reasons.append("student_personal_ai_video_disabled")
    if "movement_video" not in settings.allowed_domains:
        blocked_reasons.append("domain_disabled")
    if settings.require_image_consent_for_video:
        consent_map = current_consent_status_map(db, member.id, gym_id=gym_id)
        if consent_map.get("image") is not True:
            blocked_reasons.append("missing_image_consent")
    if not media.media_url:
        blocked_reasons.append("needs_media_retrieval")

    status_value = "blocked" if blocked_reasons else STUDENT_PERSONAL_AI_DRAFT_READY
    review = _create_student_video_review(
        db,
        gym_id=gym_id,
        member=member,
        media=media,
        status_value=status_value,
        blocked_reasons=sorted(set(blocked_reasons)),
        source_event_id=event.id,
        message_log_id=message_log_id,
        kommo_contact_id=kommo_contact_id,
        kommo_lead_id=kommo_lead_id,
    )
    first_name = ((member.full_name or "").split(" ")[0] or "aluno").strip()
    draft_reply = None if blocked_reasons else (
        f"Oi, {first_name}! Recebi seu video. Vou pedir para o professor revisar sua execucao e te devolver "
        "um feedback seguro por aqui. Se sentir dor ou desconforto forte, pare o exercicio e chame a equipe."
    )
    metadata = {
        "student_personal_ai_state": status_value,
        "intent": "movement_video",
        "sensitivity": "normal",
        "summary": "Aluno enviou video pela Kommo para revisao tecnica supervisionada.",
        "draft_reply": draft_reply,
        "next_action": "Professor revisa o video e prepara feedback antes de responder na Kommo.",
        "recommended_owner_role": "coach",
        "blocked_reasons": sorted(set(blocked_reasons)),
        "evidence": ["kommo_inbound", "student_video", "movement_video_review"],
        "received_message": message_text or media.caption,
        "source_event_id": str(event.id),
        "message_log_id": str(message_log_id) if message_log_id else None,
        "movement_video_review_id": str(review.id),
        "kommo_contact_id": kommo_contact_id,
        "kommo_lead_id": kommo_lead_id,
        "provider_media_id": media.provider_media_id,
        "media_url_available": bool(media.media_url),
        "mode": "draft_only",
        "auto_send_enabled": False,
    }
    action = AutopilotAction(
        gym_id=gym_id,
        policy_key="student_personal_ai_movement_video",
        domain="trainer",
        action_type=STUDENT_PERSONAL_AI_ACTION_TYPE,
        status=status_value,
        member_id=member.id,
        channel="kommo",
        template_key="student_personal_ai_movement_video",
        message_body=draft_reply,
        timeout_at=_now() + timedelta(hours=48),
        max_attempts=1,
        idempotency_key=idempotency_key,
        failure_reason=",".join(sorted(set(blocked_reasons))) if blocked_reasons else None,
        metadata_json=metadata,
    )
    db.add(action)
    db.flush()
    _record_student_action_event(db, action=action, event_type=status_value, source_event_id=event.id)
    if flush:
        db.flush()
    return serialize_student_personal_ai_draft(action)


def _create_student_video_review(
    db: Session,
    *,
    gym_id: UUID,
    member: Member,
    media: KommoMediaReference,
    status_value: str,
    blocked_reasons: list[str],
    source_event_id: UUID,
    message_log_id: UUID | None,
    kommo_contact_id: str | None,
    kommo_lead_id: str | None,
) -> MovementVideoReview:
    now = _now()
    review_status = "blocked" if blocked_reasons else "pending_review"
    if "needs_media_retrieval" in blocked_reasons and len(blocked_reasons) == 1:
        review_status = "needs_media_retrieval"
    review = MovementVideoReview(
        id=uuid.uuid4(),
        gym_id=gym_id,
        member_id=member.id,
        trainer_user_id=None,
        exercise_name=_exercise_name_from_caption(media.caption),
        video_asset_url=media.media_url,
        video_asset_hash=None,
        media_type=media.media_type,
        file_size_bytes=media.file_size_bytes,
        duration_seconds=media.duration_seconds,
        original_video_stored=False,
        status=review_status,
        analysis_status="blocked" if blocked_reasons else "not_started",
        safety_level="blocked" if blocked_reasons else "coach_review",
        summary=(
            "Video recebido via Kommo; professor deve revisar no contexto original antes de responder."
            if not blocked_reasons
            else "Video recebido via Kommo, mas bloqueado/pendente por guardrails."
        ),
        detected_points=[],
        suggested_feedback=None,
        coach_feedback=None,
        blocked_reasons=blocked_reasons,
        metadata_json={
            "source": "student_kommo",
            "student_personal_ai": True,
            "source_event_id": str(source_event_id),
            "message_log_id": str(message_log_id) if message_log_id else None,
            "kommo_contact_id": kommo_contact_id,
            "kommo_lead_id": kommo_lead_id,
            "provider_media_id": media.provider_media_id,
            "needs_media_retrieval": "needs_media_retrieval" in blocked_reasons,
            "caption": media.caption,
            "status_from_action": status_value,
        },
        created_at=now,
        updated_at=now,
    )
    db.add(review)
    db.flush()
    record_event(
        db,
        gym_id=gym_id,
        event_type="student_personal_ai_video_received",
        source="student_personal_ai",
        member_id=member.id,
        metadata={
            "review_id": str(review.id),
            "status": review.status,
            "blocked_reasons": blocked_reasons,
            "source_event_id": str(source_event_id),
        },
        flush=False,
    )
    return review


def _common_blocked_reasons(
    db: Session,
    *,
    gym: Gym | None,
    member: Member,
    settings: StudentPersonalAiSettingsOut,
    require_communication_consent: bool,
) -> list[str]:
    reasons: list[str] = []
    if settings.auto_send_enabled:
        reasons.append("auto_send_not_allowed_v1")
    if settings.kommo_required and (gym is None or getattr(gym, "primary_message_channel", None) != "kommo"):
        reasons.append("kommo_not_primary_channel")
    if settings.kommo_required and (gym is None or not is_kommo_ready(gym)):
        reasons.append("kommo_not_ready")
    if require_communication_consent and settings.require_communication_consent and not _member_has_communication_consent(db, member):
        reasons.append("missing_communication_consent")
    if _member_is_vip(member):
        reasons.append("vip_member_requires_human")
    if _has_recent_human_kommo_activity(
        db,
        gym_id=member.gym_id,
        member_id=member.id,
        hours=settings.human_recent_activity_cooldown_hours,
    ):
        reasons.append("recent_human_activity")
    return reasons


def _record_student_action_event(
    db: Session,
    *,
    action: AutopilotAction,
    event_type: str,
    source_event_id: UUID,
) -> None:
    resolved_event_type = {
        STUDENT_PERSONAL_AI_DRAFT_READY: "student_personal_ai_draft_created",
        "blocked": "student_personal_ai_blocked",
        "escalated": "human_intervention_required",
    }.get(event_type, "student_personal_ai_event_recorded")
    record_event(
        db,
        gym_id=action.gym_id,
        event_type=resolved_event_type,
        source="student_personal_ai",
        member_id=action.member_id,
        autopilot_action_id=action.id,
        metadata={
            "intent": (action.metadata_json or {}).get("intent"),
            "status": action.status,
            "blocked_reasons": (action.metadata_json or {}).get("blocked_reasons") or [],
            "source_event_id": str(source_event_id),
        },
        flush=False,
    )


def _record_kommo_handoff_log(db: Session, *, action: AutopilotAction, member: Member, result) -> None:
    db.add(
        MessageLog(
            gym_id=action.gym_id,
            member_id=member.id,
            lead_id=None,
            channel="kommo",
            recipient=(member.phone or member.email or str(member.id)),
            template_name=action.template_key,
            content=action.message_body or "",
            status="sent",
            direction="outbound",
            event_type="student_personal_ai_kommo_draft",
            provider_message_id=result.task_id,
            extra_data={
                "autopilot_action_id": str(action.id),
                "source": "student_personal_ai",
                "kommo_contact_id": result.contact_id,
                "kommo_lead_id": result.lead_id,
                "kommo_task_id": result.task_id,
                "operator_review_required": True,
            },
        )
    )


def _get_action_or_404(db: Session, *, gym_id: UUID, draft_id: UUID) -> AutopilotAction:
    action = db.scalar(
        select(AutopilotAction).where(
            AutopilotAction.gym_id == gym_id,
            AutopilotAction.id == draft_id,
            AutopilotAction.action_type == STUDENT_PERSONAL_AI_ACTION_TYPE,
        )
    )
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rascunho do Personal IA do aluno nao encontrado.")
    return action


def _get_existing_action(db: Session, *, gym_id: UUID, idempotency_key: str) -> AutopilotAction | None:
    return db.scalar(
        select(AutopilotAction).where(
            AutopilotAction.gym_id == gym_id,
            AutopilotAction.idempotency_key == idempotency_key,
        )
    )


def _drafts_created_today(db: Session, *, gym_id: UUID) -> int:
    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    value = db.scalar(
        select(func.count(AutopilotAction.id)).where(
            AutopilotAction.gym_id == gym_id,
            AutopilotAction.action_type == STUDENT_PERSONAL_AI_ACTION_TYPE,
            AutopilotAction.created_at >= today_start,
        )
    )
    return int(value or 0)


def _member_has_communication_consent(db: Session, member: Member) -> bool:
    try:
        consent_map = current_consent_status_map(db, member.id, gym_id=member.gym_id)
        return consent_map.get("communication") is True
    except Exception:
        extra = getattr(member, "extra_data", None) or {}
        consents = extra.get("consents") if isinstance(extra.get("consents"), dict) else {}
        return bool(
            consents.get("communication") is True
            or consents.get("whatsapp_consent") is True
            or extra.get("communication_consent") is True
            or extra.get("whatsapp_consent") is True
        )


def _has_recent_human_kommo_activity(db: Session, *, gym_id: UUID, member_id: UUID, hours: int) -> bool:
    if hours <= 0:
        return False
    since = _now() - timedelta(hours=hours)
    recent = db.scalar(
        select(MessageLog.id)
        .where(
            MessageLog.gym_id == gym_id,
            MessageLog.member_id == member_id,
            MessageLog.channel == "kommo",
            MessageLog.direction == "outbound",
            MessageLog.created_at >= since,
            MessageLog.event_type.in_(["kommo_human_reply", "kommo_operator_manual", "kommo_manual_reply"]),
        )
        .limit(1)
    )
    return recent is not None


def _member_is_vip(member: Member) -> bool:
    return bool(getattr(member, "is_vip", False))


def _student_sensitive_override(message_text: str) -> tuple[str, str, str, str] | None:
    normalized = _normalize_text(message_text)
    if any(term in normalized for term in STUDENT_OPT_OUT_TERMS):
        return ("opt_out", "Aluno pediu para pausar ou remover comunicacoes.", "Registrar opt-out e humano assumir.", "manager")
    if any(term in normalized for term in STUDENT_FINANCE_DISPUTE_TERMS):
        return ("finance_dispute", "Aluno sinalizou contestacao financeira.", "Escalar para gestor/financeiro.", "manager")
    if any(term in normalized for term in STUDENT_HUMAN_TERMS):
        return ("human_request", "Aluno pediu atendimento humano.", "Humano deve assumir a conversa.", "reception")
    return None


def _merge_settings(raw: dict | None) -> dict:
    merged = dict(DEFAULT_STUDENT_PERSONAL_AI_SETTINGS)
    if isinstance(raw, dict):
        merged.update(raw)
    merged["mode"] = "draft_only"
    merged["auto_send_enabled"] = False
    merged["enabled"] = bool(merged.get("enabled"))
    merged["kommo_required"] = bool(merged.get("kommo_required", True))
    merged["personal_ai_enabled"] = bool(merged.get("personal_ai_enabled", True))
    merged["movement_video_enabled"] = bool(merged.get("movement_video_enabled", True))
    merged["require_member_match"] = True
    merged["require_communication_consent"] = bool(merged.get("require_communication_consent", True))
    merged["require_image_consent_for_video"] = bool(merged.get("require_image_consent_for_video", True))
    merged["sensitive_escalation_enabled"] = bool(merged.get("sensitive_escalation_enabled", True))
    merged["max_drafts_per_day"] = max(0, min(int(merged.get("max_drafts_per_day") or 50), 500))
    merged["human_recent_activity_cooldown_hours"] = max(
        0,
        min(int(merged.get("human_recent_activity_cooldown_hours") or 24), 168),
    )
    if not isinstance(merged.get("allowed_domains"), list):
        merged["allowed_domains"] = list(DEFAULT_STUDENT_PERSONAL_AI_SETTINGS["allowed_domains"])
    return merged


def _exercise_name_from_caption(caption: str | None) -> str:
    text = (caption or "").strip()
    if not text:
        return "Video enviado pelo aluno"
    return text[:120]


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _first_nested_string(value: Any, keys: set[str]) -> str | None:
    found = _first_nested_value(value, keys)
    if found is None:
        return None
    text = str(found).strip()
    return text or None


def _first_nested_int(value: Any, keys: set[str]) -> int | None:
    found = _first_nested_value(value, keys)
    if found is None:
        return None
    try:
        return int(found)
    except (TypeError, ValueError):
        return None


def _first_nested_value(value: Any, keys: set[str]) -> Any | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in keys and child is not None and child != "":
                return child
            found = _first_nested_value(child, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _first_nested_value(child, keys)
            if found is not None:
                return found
    return None
