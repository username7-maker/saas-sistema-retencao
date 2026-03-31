from __future__ import annotations

import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import desc, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import include_all_tenants
from app.models import ActuarBridgeDevice, ActuarMemberLink, ActuarSyncAttempt, ActuarSyncJob, BodyCompositionEvaluation, Member
from app.schemas.actuar_bridge import (
    ActuarBridgeClaimedJobRead,
    ActuarBridgeDeviceRead,
    ActuarBridgeHeartbeatResponse,
    ActuarBridgeJobCompleteInput,
    ActuarBridgeJobFailInput,
    ActuarBridgePairingCodeRead,
    ActuarBridgePairRequest,
    ActuarBridgePairResponse,
)
from app.services.actuar_member_link_service import get_actuar_member_link, resolve_member_document_for_actuar, upsert_actuar_member_link
from app.services.body_composition_actuar_mapping_service import build_manual_sync_summary


def list_actuar_bridge_devices(db: Session, *, gym_id: UUID) -> list[ActuarBridgeDeviceRead]:
    devices = list(
        db.scalars(
            include_all_tenants(
                select(ActuarBridgeDevice)
                .where(ActuarBridgeDevice.gym_id == gym_id)
                .order_by(desc(ActuarBridgeDevice.created_at)),
                reason="actuar_bridge.list_devices",
            )
        ).all()
    )
    return [_serialize_device(device) for device in devices]


def count_online_actuar_bridge_devices(db: Session, *, gym_id: UUID) -> int:
    return sum(1 for device in list_actuar_bridge_devices(db, gym_id=gym_id) if device.status == "online")


def issue_actuar_bridge_pairing_code(
    db: Session,
    *,
    gym_id: UUID,
    created_by_user_id: UUID | None,
) -> ActuarBridgePairingCodeRead:
    raw_code = _generate_pairing_code()
    expires_at = _now() + timedelta(minutes=settings.actuar_bridge_pairing_code_ttl_minutes)
    device = ActuarBridgeDevice(
        gym_id=gym_id,
        device_name="Nova estacao Actuar",
        status="pairing",
        pairing_code_hash=_hash_secret(raw_code),
        pairing_code_expires_at=expires_at,
        created_by_user_id=created_by_user_id,
    )
    db.add(device)
    db.flush()
    return ActuarBridgePairingCodeRead(device_id=device.id or uuid4(), pairing_code=raw_code, expires_at=expires_at)


def revoke_actuar_bridge_device(
    db: Session,
    *,
    gym_id: UUID,
    device_id: UUID,
) -> ActuarBridgeDeviceRead:
    device = _get_device_for_gym_or_404(db, gym_id=gym_id, device_id=device_id)
    device.status = "revoked"
    device.revoked_at = _now()
    device.auth_token_hash = None
    device.pairing_code_hash = None
    device.pairing_code_expires_at = None
    device.last_error_code = None
    device.last_error_message = None
    db.add(device)
    db.flush()
    return _serialize_device(device)


def pair_actuar_bridge_device(db: Session, *, payload: ActuarBridgePairRequest) -> ActuarBridgePairResponse:
    device = db.scalar(
        include_all_tenants(
            select(ActuarBridgeDevice).where(
                ActuarBridgeDevice.pairing_code_hash == _hash_secret(payload.pairing_code.strip().upper()),
                ActuarBridgeDevice.status == "pairing",
                ActuarBridgeDevice.pairing_code_expires_at.is_not(None),
                ActuarBridgeDevice.pairing_code_expires_at > _now(),
            ),
            reason="actuar_bridge.pair_device",
        )
    )
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Codigo de pareamento invalido ou expirado")

    raw_token = secrets.token_urlsafe(48)
    device.device_name = payload.device_name.strip()
    device.bridge_version = _normalize_optional(payload.bridge_version)
    device.browser_name = _normalize_optional(payload.browser_name)
    device.status = "offline"
    device.paired_at = _now()
    device.auth_token_hash = _hash_secret(raw_token)
    device.pairing_code_hash = None
    device.pairing_code_expires_at = None
    device.last_error_code = None
    device.last_error_message = None
    db.add(device)
    db.flush()
    return ActuarBridgePairResponse(
        device_token=raw_token,
        api_base_url=(settings.public_backend_url or "").strip() or None,
        poll_interval_seconds=settings.actuar_bridge_poll_seconds,
        device=_serialize_device(device),
    )


def authenticate_actuar_bridge_device(db: Session, *, device_token: str) -> ActuarBridgeDevice:
    normalized_token = (device_token or "").strip()
    if not normalized_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token da estacao ausente")

    device = db.scalar(
        include_all_tenants(
            select(ActuarBridgeDevice).where(ActuarBridgeDevice.auth_token_hash == _hash_secret(normalized_token)),
            reason="actuar_bridge.authenticate_device",
        )
    )
    if not device or device.status == "revoked" or device.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token da estacao invalido")
    return device


def heartbeat_actuar_bridge_device(
    db: Session,
    *,
    device: ActuarBridgeDevice,
    bridge_version: str | None = None,
    browser_name: str | None = None,
) -> ActuarBridgeHeartbeatResponse:
    device.status = "online"
    device.last_seen_at = _now()
    if bridge_version is not None:
        device.bridge_version = _normalize_optional(bridge_version)
    if browser_name is not None:
        device.browser_name = _normalize_optional(browser_name)
    db.add(device)
    db.flush()
    return ActuarBridgeHeartbeatResponse(device=_serialize_device(device), poll_interval_seconds=settings.actuar_bridge_poll_seconds)


def claim_next_actuar_bridge_job(
    db: Session,
    *,
    device: ActuarBridgeDevice,
) -> ActuarBridgeClaimedJobRead | None:
    now = _now()
    row = db.execute(
        include_all_tenants(
            select(ActuarSyncJob, BodyCompositionEvaluation, Member, ActuarMemberLink)
            .join(BodyCompositionEvaluation, BodyCompositionEvaluation.id == ActuarSyncJob.body_composition_evaluation_id)
            .join(Member, Member.id == ActuarSyncJob.member_id)
            .outerjoin(
                ActuarMemberLink,
                (ActuarMemberLink.member_id == Member.id) & (ActuarMemberLink.gym_id == Member.gym_id),
            )
            .where(
                ActuarSyncJob.gym_id == device.gym_id,
                BodyCompositionEvaluation.actuar_sync_mode == "local_bridge",
                or_(
                    ActuarSyncJob.status == "pending",
                    (
                        (ActuarSyncJob.status == "failed")
                        & (ActuarSyncJob.next_retry_at.is_not(None))
                        & (ActuarSyncJob.next_retry_at <= now)
                        & (ActuarSyncJob.retry_count < ActuarSyncJob.max_retries)
                    ),
                ),
            )
            .order_by(ActuarSyncJob.created_at.asc())
            .limit(1),
            reason="actuar_bridge.claim_next_job",
        )
    ).first()
    if not row:
        return None

    job, evaluation, member, member_link = row
    current_status = job.status
    locked_by = f"bridge:{device.id}"
    result = db.execute(
        update(ActuarSyncJob)
        .where(ActuarSyncJob.id == job.id, ActuarSyncJob.status == current_status)
        .values(status="processing", locked_at=now, locked_by=locked_by)
        .execution_options(include_all_tenants=True, tenant_bypass_reason="actuar_bridge.claim_job_lock")
    )
    if not result.rowcount:
        db.rollback()
        return None

    device.status = "online"
    device.last_seen_at = now
    device.last_job_claimed_at = now
    device.last_error_code = None
    device.last_error_message = None
    _start_bridge_attempt(db, job=job, evaluation=evaluation, worker_id=locked_by)

    manual_summary = build_manual_sync_summary(member, evaluation)
    return ActuarBridgeClaimedJobRead(
        job_id=job.id,
        evaluation_id=evaluation.id,
        member_id=member.id,
        sync_mode=evaluation.actuar_sync_mode,
        member_name=member.full_name,
        member_email=member.email,
        member_birthdate=member.birthdate,
        member_document=resolve_member_document_for_actuar(member, member_link),
        actuar_external_id=member_link.actuar_external_id if member_link else None,
        payload_json=job.payload_json,
        mapped_fields_json=job.mapped_fields_json,
        critical_fields_json=job.critical_fields_json,
        non_critical_fields_json=job.non_critical_fields_json,
        manual_summary_text=manual_summary["summary_text"],
    )


def complete_actuar_bridge_job(
    db: Session,
    *,
    device: ActuarBridgeDevice,
    job_id: UUID,
    payload: ActuarBridgeJobCompleteInput,
) -> None:
    job, evaluation, attempt = _load_claimed_job_triplet(db, device=device, job_id=job_id)
    now = _now()
    device.status = "online"
    device.last_seen_at = now
    device.last_job_completed_at = now
    device.last_error_code = None
    device.last_error_message = None

    action_log = list(payload.action_log_json or [])
    if payload.note:
        action_log.append({"event": "bridge_note", "note": payload.note})
    _finalize_bridge_success(
        db,
        job=job,
        evaluation=evaluation,
        attempt=attempt,
        external_id=payload.external_id,
        action_log=action_log,
    )
    _persist_member_link_from_bridge_success(db, job=job, external_id=payload.external_id)


def fail_actuar_bridge_job(
    db: Session,
    *,
    device: ActuarBridgeDevice,
    job_id: UUID,
    payload: ActuarBridgeJobFailInput,
) -> None:
    _load_claimed_job_triplet(db, device=device, job_id=job_id)
    now = _now()
    device.status = "online"
    device.last_seen_at = now
    device.last_job_completed_at = now
    device.last_error_code = payload.error_code
    device.last_error_message = payload.error_message
    db.add(device)
    _finalize_bridge_failure(
        db,
        job_id=job_id,
        worker_id=f"bridge:{device.id}",
        error_code=payload.error_code,
        error_message=payload.error_message,
        retryable=payload.retryable,
        manual_fallback=payload.manual_fallback,
    )


def _start_bridge_attempt(db: Session, *, job: ActuarSyncJob, evaluation: BodyCompositionEvaluation, worker_id: str) -> None:
    from app.services.body_composition_actuar_sync_service import _start_attempt

    _start_attempt(db, job=job, evaluation=evaluation, worker_id=worker_id)


def _finalize_bridge_success(
    db: Session,
    *,
    job: ActuarSyncJob,
    evaluation: BodyCompositionEvaluation,
    attempt: ActuarSyncAttempt,
    external_id: str | None,
    action_log: list[dict] | list,
) -> None:
    from app.services.body_composition_actuar_sync_service import _finalize_sync_success

    _finalize_sync_success(
        db,
        job=job,
        evaluation=evaluation,
        attempt=attempt,
        external_id=external_id,
        action_log=action_log,
        screenshot_path=None,
        page_html_path=None,
    )


def _finalize_bridge_failure(
    db: Session,
    *,
    job_id: UUID,
    worker_id: str,
    error_code: str,
    error_message: str,
    retryable: bool,
    manual_fallback: bool,
) -> None:
    from app.services.body_composition_actuar_sync_service import ActuarSyncServiceError, _finalize_sync_failure

    _finalize_sync_failure(
        db,
        job_id=job_id,
        worker_id=worker_id,
        error=ActuarSyncServiceError(
            error_code,
            error_message,
            retryable=retryable,
            manual_fallback=manual_fallback,
        ),
        provider=None,
    )


def _persist_member_link_from_bridge_success(db: Session, *, job: ActuarSyncJob, external_id: str | None) -> None:
    normalized_external_id = (external_id or "").strip()
    if not normalized_external_id:
        return

    member = db.scalar(
        include_all_tenants(
            select(Member).where(Member.id == job.member_id),
            reason="actuar_bridge.persist_member_link.member",
        )
    )
    if member is None:
        return

    current_link = get_actuar_member_link(db, gym_id=job.gym_id, member_id=job.member_id)
    if current_link is not None:
        current_link.actuar_external_id = normalized_external_id
        current_link.actuar_search_name = current_link.actuar_search_name or member.full_name
        current_link.actuar_search_document = resolve_member_document_for_actuar(member, current_link)
        current_link.actuar_search_birthdate = member.birthdate
        current_link.linked_at = _now()
        current_link.linked_by_user_id = None
        current_link.match_confidence = 1.0
        current_link.is_active = True
        db.add(current_link)
        db.flush()
        return

    upsert_actuar_member_link(
        db,
        gym_id=job.gym_id,
        member_id=job.member_id,
        user_id=None,
        actuar_external_id=normalized_external_id,
        actuar_search_name=(current_link.actuar_search_name if current_link else None) or member.full_name,
        actuar_search_document=resolve_member_document_for_actuar(member, current_link),
        actuar_search_birthdate=member.birthdate,
        match_confidence=1.0,
    )


def _load_claimed_job_triplet(
    db: Session,
    *,
    device: ActuarBridgeDevice,
    job_id: UUID,
) -> tuple[ActuarSyncJob, BodyCompositionEvaluation, ActuarSyncAttempt]:
    job = db.scalar(
        include_all_tenants(
            select(ActuarSyncJob).where(
                ActuarSyncJob.id == job_id,
                ActuarSyncJob.gym_id == device.gym_id,
                ActuarSyncJob.status == "processing",
                ActuarSyncJob.locked_by == f"bridge:{device.id}",
            ),
            reason="actuar_bridge.load_claimed_job",
        )
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job do Actuar nao encontrado para esta estacao")

    evaluation = db.scalar(
        include_all_tenants(
            select(BodyCompositionEvaluation).where(BodyCompositionEvaluation.id == job.body_composition_evaluation_id),
            reason="actuar_bridge.load_evaluation",
        )
    )
    attempt = db.scalar(
        include_all_tenants(
            select(ActuarSyncAttempt)
            .where(ActuarSyncAttempt.sync_job_id == job.id)
            .order_by(desc(ActuarSyncAttempt.started_at))
            .limit(1),
            reason="actuar_bridge.load_attempt",
        )
    )
    if not evaluation or not attempt:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Estado do job do Actuar inconsistente para a estacao local")
    return job, evaluation, attempt


def _get_device_for_gym_or_404(db: Session, *, gym_id: UUID, device_id: UUID) -> ActuarBridgeDevice:
    device = db.scalar(
        include_all_tenants(
            select(ActuarBridgeDevice).where(ActuarBridgeDevice.id == device_id, ActuarBridgeDevice.gym_id == gym_id),
            reason="actuar_bridge.get_device_for_gym",
        )
    )
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estacao Actuar nao encontrada")
    return device


def _serialize_device(device: ActuarBridgeDevice) -> ActuarBridgeDeviceRead:
    status = _derived_device_status(device)
    return ActuarBridgeDeviceRead(
        id=device.id,
        gym_id=device.gym_id,
        device_name=device.device_name,
        status=status,
        bridge_version=device.bridge_version,
        browser_name=device.browser_name,
        paired_at=device.paired_at,
        last_seen_at=device.last_seen_at,
        last_job_claimed_at=device.last_job_claimed_at,
        last_job_completed_at=device.last_job_completed_at,
        last_error_code=device.last_error_code,
        last_error_message=device.last_error_message,
        revoked_at=device.revoked_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


def _derived_device_status(device: ActuarBridgeDevice) -> str:
    if device.status == "revoked" or device.revoked_at is not None:
        return "revoked"
    if device.status == "pairing":
        return "pairing"
    if device.last_seen_at and (_now() - device.last_seen_at).total_seconds() <= settings.actuar_bridge_device_stale_seconds:
        return "online"
    return "offline"


def _generate_pairing_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    raw = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_optional(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _now() -> datetime:
    return datetime.now(timezone.utc)
