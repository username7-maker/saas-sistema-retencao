from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Member, MemberConsentRecord
from app.schemas.compliance import (
    MemberConsentCurrentOut,
    MemberConsentRecordCreate,
    MemberConsentSummaryOut,
)

CONSENT_TYPES = ("lgpd", "communication", "image", "contract")


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _get_member_or_404(db: Session, member_id: UUID, gym_id: UUID) -> Member:
    member = db.scalar(
        select(Member).where(
            Member.id == member_id,
            Member.gym_id == gym_id,
            Member.deleted_at.is_(None),
        )
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")
    return member


def _is_expired(record: MemberConsentRecord | None, now: datetime) -> bool:
    if record is None or record.expires_at is None:
        return False
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < now


def _current_item(consent_type: str, record: MemberConsentRecord | None, now: datetime) -> MemberConsentCurrentOut:
    if record is None:
        return MemberConsentCurrentOut(
            consent_type=consent_type,
            status="missing",
            accepted=False,
            missing=True,
        )

    expired = _is_expired(record, now)
    status_value = "expired" if expired and record.status == "accepted" else record.status
    accepted = status_value == "accepted"
    return MemberConsentCurrentOut(
        consent_type=consent_type,
        status=status_value,
        accepted=accepted,
        source=record.source,
        document_title=record.document_title,
        document_version=record.document_version,
        signed_at=record.signed_at,
        revoked_at=record.revoked_at,
        expires_at=record.expires_at,
        record_id=record.id,
        missing=False,
        expired=expired,
    )


def list_member_consent_records(db: Session, member_id: UUID, *, gym_id: UUID) -> MemberConsentSummaryOut:
    _get_member_or_404(db, member_id, gym_id)
    records = db.scalars(
        select(MemberConsentRecord)
        .where(MemberConsentRecord.gym_id == gym_id, MemberConsentRecord.member_id == member_id)
        .order_by(MemberConsentRecord.created_at.desc())
    ).all()

    latest_by_type: dict[str, MemberConsentRecord] = {}
    for record in records:
        latest_by_type.setdefault(record.consent_type, record)

    now = _now()
    current = [_current_item(consent_type, latest_by_type.get(consent_type), now) for consent_type in CONSENT_TYPES]
    missing = [item.consent_type for item in current if item.missing]
    expired = [item.consent_type for item in current if item.expired]
    latest_update = records[0].created_at if records else now
    return MemberConsentSummaryOut(
        member_id=member_id,
        current=current,
        records=records,
        missing=missing,
        expired=expired,
        updated_at=latest_update,
    )


def record_member_consent(
    db: Session,
    member_id: UUID,
    payload: MemberConsentRecordCreate,
    *,
    gym_id: UUID,
    actor_user_id: UUID | None = None,
    commit: bool = True,
) -> MemberConsentRecord:
    _get_member_or_404(db, member_id, gym_id)
    now = _now()
    signed_at = payload.signed_at or (now if payload.status == "accepted" else None)
    revoked_at = now if payload.status == "revoked" else None
    record = MemberConsentRecord(
        gym_id=gym_id,
        member_id=member_id,
        consent_type=payload.consent_type,
        status=payload.status,
        source=payload.source,
        document_title=payload.document_title,
        document_version=payload.document_version,
        evidence_ref=payload.evidence_ref,
        notes=payload.notes,
        signed_at=signed_at,
        revoked_at=revoked_at,
        expires_at=payload.expires_at,
        extra_data={**payload.extra_data, "actor_user_id": str(actor_user_id) if actor_user_id else None},
    )
    db.add(record)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(record)
    return record


def current_consent_status_map(db: Session, member_id: UUID, *, gym_id: UUID) -> dict[str, bool | None]:
    summary = list_member_consent_records(db, member_id, gym_id=gym_id)
    return {item.consent_type: (item.accepted if not item.missing else None) for item in summary.current}
