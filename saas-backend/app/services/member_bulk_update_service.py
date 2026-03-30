from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Member
from app.schemas.member import (
    MemberBulkUpdateCommitInput,
    MemberBulkUpdatePreviewInput,
    MemberBulkUpdatePreviewMember,
    MemberBulkUpdatePreviewOut,
    MemberBulkUpdateResultOut,
)
from app.services.member_service import _build_member_filters, _scoped_statement

_SAMPLE_LIMIT = 8


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return float(value)
    return value


def _resolve_target_members(
    db: Session,
    *,
    gym_id: UUID,
    target_mode: str,
    selected_member_ids: list[UUID],
    filters,
) -> list[Member]:
    if target_mode == "selected":
        stmt = _scoped_statement(
            select(Member)
            .where(
                Member.deleted_at.is_(None),
                Member.gym_id == gym_id,
                Member.id.in_(selected_member_ids),
            )
            .order_by(Member.full_name.asc()),
            gym_id,
        )
        return db.scalars(stmt).all()

    base_filters, resolved_gym_id = _build_member_filters(
        gym_id=gym_id,
        search=filters.search,
        risk_level=filters.risk_level,
        status=filters.status,
        plan_cycle=filters.plan_cycle,
        min_days_without_checkin=filters.min_days_without_checkin,
        provisional_only=filters.provisional_only,
    )
    stmt = _scoped_statement(
        select(Member).where(and_(*base_filters)).order_by(Member.risk_score.desc(), Member.updated_at.desc()),
        resolved_gym_id,
    )
    return db.scalars(stmt).all()


def _build_changed_fields(changes) -> dict[str, Any]:
    return changes.model_dump(exclude_none=True)


def _has_effective_change(member: Member, changes: dict[str, Any]) -> bool:
    return any(getattr(member, field) != value for field, value in changes.items())


def _preview_member(member: Member, changes: dict[str, Any]) -> MemberBulkUpdatePreviewMember:
    current_values = {
        field: _serialize_value(getattr(member, field))
        for field in changes
    }
    next_values = {
        field: _serialize_value(changes[field])
        for field in changes
    }
    return MemberBulkUpdatePreviewMember(
        id=member.id,
        full_name=member.full_name,
        email=member.email,
        current_values=current_values,
        next_values=next_values,
    )


def _target_description(target_mode: str, total_candidates: int) -> str:
    if target_mode == "selected":
        return f"{total_candidates} membro(s) selecionado(s)"
    return f"{total_candidates} membro(s) do filtro atual"


def preview_member_bulk_update(
    db: Session,
    *,
    gym_id: UUID,
    payload: MemberBulkUpdatePreviewInput,
) -> MemberBulkUpdatePreviewOut:
    changes = _build_changed_fields(payload.changes)
    members = _resolve_target_members(
        db,
        gym_id=gym_id,
        target_mode=payload.target_mode,
        selected_member_ids=payload.selected_member_ids,
        filters=payload.filters,
    )
    if payload.target_mode == "selected" and not members:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum membro selecionado foi encontrado para esta academia.",
        )

    changed_members = [member for member in members if _has_effective_change(member, changes)]
    return MemberBulkUpdatePreviewOut(
        target_mode=payload.target_mode,
        target_description=_target_description(payload.target_mode, len(members)),
        total_candidates=len(members),
        would_update=len(changed_members),
        unchanged=max(len(members) - len(changed_members), 0),
        changed_fields=list(changes.keys()),
        sample_members=[_preview_member(member, changes) for member in changed_members[:_SAMPLE_LIMIT]],
    )


def apply_member_bulk_update(
    db: Session,
    *,
    gym_id: UUID,
    payload: MemberBulkUpdateCommitInput,
) -> MemberBulkUpdateResultOut:
    changes = _build_changed_fields(payload.changes)
    members = _resolve_target_members(
        db,
        gym_id=gym_id,
        target_mode=payload.target_mode,
        selected_member_ids=payload.selected_member_ids,
        filters=payload.filters,
    )
    if payload.target_mode == "selected" and not members:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum membro selecionado foi encontrado para esta academia.",
        )

    updated = 0
    unchanged = 0
    for member in members:
        if not _has_effective_change(member, changes):
            unchanged += 1
            continue
        for field, value in changes.items():
            setattr(member, field, value)
        db.add(member)
        updated += 1

    if updated:
        invalidate_dashboard_cache("members", "risk", "financial", gym_id=gym_id)

    return MemberBulkUpdateResultOut(
        target_mode=payload.target_mode,
        target_description=_target_description(payload.target_mode, len(members)),
        updated=updated,
        unchanged=unchanged,
        changed_fields=list(changes.keys()),
    )
