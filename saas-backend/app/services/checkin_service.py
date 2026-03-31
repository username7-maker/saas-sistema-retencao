from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Checkin, Member
from app.schemas import CheckinCreate
from app.services.preferred_shift_service import sync_preferred_shifts_from_checkins


def create_checkin(db: Session, payload: CheckinCreate, *, commit: bool = True) -> Checkin:
    member = db.scalar(select(Member).where(Member.id == payload.member_id, Member.deleted_at.is_(None)))
    if not member:
        raise ValueError("Membro nao encontrado")

    checkin_at = payload.checkin_at
    if checkin_at.tzinfo is None:
        checkin_at = checkin_at.replace(tzinfo=timezone.utc)
    duplicate = db.scalar(
        select(Checkin).where(Checkin.member_id == payload.member_id, Checkin.checkin_at == checkin_at)
    )
    if duplicate:
        raise ValueError("Check-in duplicado")

    checkin = Checkin(
        member_id=payload.member_id,
        checkin_at=checkin_at,
        source=payload.source,
        hour_bucket=checkin_at.hour,
        weekday=checkin_at.weekday(),
        extra_data=payload.extra_data,
    )
    member.last_checkin_at = checkin_at
    db.add(checkin)
    db.add(member)
    db.flush()
    sync_preferred_shifts_from_checkins(db, member_ids={member.id}, commit=False, flush=False)
    if commit:
        db.commit()
    db.refresh(checkin)
    invalidate_dashboard_cache("checkins")
    return checkin
