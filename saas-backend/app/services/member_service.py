from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Member, MemberStatus, RiskLevel
from app.schemas import MemberCreate, MemberUpdate, PaginatedResponse
from app.utils.encryption import encrypt_cpf


def create_member(db: Session, payload: MemberCreate) -> Member:
    if payload.email:
        existing = db.scalar(
            select(Member).where(Member.email == payload.email, Member.deleted_at.is_(None))
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email de membro ja cadastrado")

    member = Member(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        cpf_encrypted=encrypt_cpf(payload.cpf) if payload.cpf else None,
        plan_name=payload.plan_name,
        monthly_fee=payload.monthly_fee,
        join_date=payload.join_date,
        preferred_shift=payload.preferred_shift,
        assigned_user_id=payload.assigned_user_id,
        loyalty_months=payload.loyalty_months,
        extra_data=payload.extra_data,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    invalidate_dashboard_cache("members")
    return member


def list_members(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    risk_level: RiskLevel | None = None,
    status: MemberStatus | None = None,
    min_days_without_checkin: int | None = None,
) -> PaginatedResponse:
    base_filters = [Member.deleted_at.is_(None)]
    if search:
        base_filters.append(
            or_(Member.full_name.ilike(f"%{search}%"), Member.email.ilike(f"%{search}%"))
        )
    if risk_level:
        base_filters.append(Member.risk_level == risk_level)
    if status:
        base_filters.append(Member.status == status)
    if min_days_without_checkin is not None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=min_days_without_checkin)
        base_filters.append(Member.last_checkin_at.is_not(None))
        base_filters.append(Member.last_checkin_at < cutoff)

    stmt = select(Member).where(and_(*base_filters)).order_by(Member.risk_score.desc(), Member.updated_at.desc())
    total = db.scalar(select(func.count()).select_from(Member).where(and_(*base_filters))) or 0

    offset = (page - 1) * page_size
    items = db.scalars(stmt.offset(offset).limit(page_size)).all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


def get_member_or_404(db: Session, member_id: UUID) -> Member:
    member = db.scalar(select(Member).where(Member.id == member_id, Member.deleted_at.is_(None)))
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")
    return member


def update_member(db: Session, member_id: UUID, payload: MemberUpdate) -> Member:
    member = get_member_or_404(db, member_id)
    data = payload.model_dump(exclude_unset=True)
    cpf = data.pop("cpf", None)
    if cpf:
        member.cpf_encrypted = encrypt_cpf(cpf)
    for key, value in data.items():
        setattr(member, key, value)
    db.add(member)
    db.commit()
    db.refresh(member)
    invalidate_dashboard_cache("members", "nps", "risk")
    return member


def soft_delete_member(db: Session, member_id: UUID) -> None:
    member = get_member_or_404(db, member_id)
    member.deleted_at = datetime.now(tz=timezone.utc)
    member.status = MemberStatus.CANCELLED
    db.add(member)
    db.commit()
    invalidate_dashboard_cache("members", "risk")
