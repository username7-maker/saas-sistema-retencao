import re
import unicodedata
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.cache import invalidate_dashboard_cache
from app.models import AuditLog, Member, RetentionExclusion, RiskAlert, Task, TaskStatus, User
from app.schemas.retention_exclusion import RetentionExclusionCreate, RetentionExclusionListOut, RetentionExclusionOut
from app.services.audit_service import log_audit_event


_PLAN_ACCENTED = "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑáàâãäéèêëíìîïóòôõöúùûüçñ"
_PLAN_ASCII = "AAAAAEEEEIIIIOOOOOUUUUCNaaaaaeeeeiiiiooooouuuucn"
_RETENTION_TASK_SOURCES = ("retention_intelligence", "retention_automation")


def normalize_plan_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents).strip().lower()


def normalized_plan_sql(column):
    translated = func.translate(func.trim(column), _PLAN_ACCENTED, _PLAN_ASCII)
    return func.lower(func.regexp_replace(translated, r"\s+", " ", "g"))


def retention_eligible_condition(*, gym_id: UUID | None = None):
    exclusion = aliased(RetentionExclusion)
    conditions = [exclusion.revoked_at.is_(None)]
    if gym_id is not None:
        conditions.append(exclusion.gym_id == gym_id)
    conditions.append(
        or_(
            and_(exclusion.scope == "member", exclusion.member_id == Member.id),
            and_(
                exclusion.scope == "plan",
                exclusion.normalized_plan_name == normalized_plan_sql(Member.plan_name),
            ),
        )
    )
    return ~exists(select(exclusion.id).where(and_(*conditions)))


def is_member_retention_excluded(db: Session, member: Member) -> bool:
    return bool(
        db.scalar(
            select(
                exists().where(
                    RetentionExclusion.revoked_at.is_(None),
                    or_(
                        and_(RetentionExclusion.scope == "member", RetentionExclusion.member_id == member.id),
                        and_(
                            RetentionExclusion.scope == "plan",
                            RetentionExclusion.normalized_plan_name == normalize_plan_name(member.plan_name),
                        ),
                    ),
                )
            )
        )
    )


def _member_ids_for_exclusion(db: Session, exclusion: RetentionExclusion) -> list[UUID]:
    stmt = select(Member.id).where(Member.deleted_at.is_(None))
    if exclusion.scope == "member":
        stmt = stmt.where(Member.id == exclusion.member_id)
    else:
        stmt = stmt.where(normalized_plan_sql(Member.plan_name) == exclusion.normalized_plan_name)
    return list(db.scalars(stmt).all())


def _archive_retention_work(db: Session, member_ids: list[UUID], *, user: User, reason: str) -> None:
    if not member_ids:
        return
    now = datetime.now(tz=timezone.utc)
    alerts = list(
        db.scalars(select(RiskAlert).where(RiskAlert.member_id.in_(member_ids), RiskAlert.resolved.is_(False))).all()
    )
    for alert in alerts:
        history = list(alert.action_history or [])
        history.append({"type": "automatic_resolution", "timestamp": now.isoformat(), "reason": "retention_exclusion"})
        alert.action_history = history
        alert.resolved = True
        alert.resolved_at = now
        alert.resolved_by_user_id = None

    tasks = list(
        db.scalars(
            select(Task).where(
                Task.member_id.in_(member_ids),
                Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
                Task.deleted_at.is_(None),
                Task.extra_data["source"].astext.in_(_RETENTION_TASK_SOURCES),
                func.coalesce(Task.extra_data["operational_archive"]["archived_at"].astext, "") == "",
            )
        ).all()
    )
    for task in tasks:
        extra = dict(task.extra_data or {})
        extra["operational_archive"] = {
            "archived_at": now.isoformat(),
            "archived_by_user_id": str(user.id),
            "reason": reason,
            "source": "retention_exclusion",
        }
        task.extra_data = extra


def create_retention_exclusion(
    db: Session, *, payload: RetentionExclusionCreate, current_user: User
) -> RetentionExclusionOut:
    member = None
    plan_name = None
    normalized_plan = None
    if payload.scope == "member":
        member = db.scalar(select(Member).where(Member.id == payload.member_id, Member.deleted_at.is_(None)))
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno nao encontrado")
        target_filter = RetentionExclusion.member_id == member.id
    else:
        plan_name = (payload.plan_name or "").strip()
        normalized_plan = normalize_plan_name(plan_name)
        target_filter = RetentionExclusion.normalized_plan_name == normalized_plan

    existing = db.scalar(
        select(RetentionExclusion).where(
            RetentionExclusion.scope == payload.scope,
            RetentionExclusion.revoked_at.is_(None),
            target_filter,
        )
    )
    if existing is not None:
        return _to_out(existing, member_name=member.full_name if member else None, created_by_name=current_user.full_name)

    exclusion = RetentionExclusion(
        gym_id=current_user.gym_id,
        scope=payload.scope,
        member_id=member.id if member else None,
        plan_name=plan_name,
        normalized_plan_name=normalized_plan,
        reason=(payload.reason or "").strip() or None,
        created_by_user_id=current_user.id,
    )
    db.add(exclusion)
    db.flush()
    member_ids = _member_ids_for_exclusion(db, exclusion)
    _archive_retention_work(
        db,
        member_ids,
        user=current_user,
        reason=payload.reason or "Removido da operacao de retencao",
    )
    log_audit_event(
        db,
        action="retention_exclusion_created",
        entity="retention_exclusion",
        entity_id=exclusion.id,
        member_id=member.id if member else None,
        user=current_user,
        details={"scope": payload.scope, "plan_name": plan_name, "affected_members": len(member_ids), "reason": payload.reason},
    )
    db.commit()
    db.refresh(exclusion)
    invalidate_dashboard_cache("retention", "tasks", gym_id=current_user.gym_id)
    return _to_out(exclusion, member_name=member.full_name if member else None, created_by_name=current_user.full_name)


def list_retention_exclusions(db: Session, *, current_user: User, search: str | None = None) -> RetentionExclusionListOut:
    creator = aliased(User)
    stmt = (
        select(RetentionExclusion, Member.full_name, creator.full_name)
        .outerjoin(Member, Member.id == RetentionExclusion.member_id)
        .join(creator, creator.id == RetentionExclusion.created_by_user_id)
        .where(RetentionExclusion.revoked_at.is_(None))
        .order_by(RetentionExclusion.created_at.desc())
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(Member.full_name.ilike(term), RetentionExclusion.plan_name.ilike(term)))
    rows = list(db.execute(stmt).all())
    return RetentionExclusionListOut(
        items=[_to_out(item, member_name=member_name, created_by_name=creator_name) for item, member_name, creator_name in rows],
        total=len(rows),
    )


def revoke_retention_exclusion(db: Session, *, exclusion_id: UUID, current_user: User) -> None:
    exclusion = db.scalar(
        select(RetentionExclusion).where(RetentionExclusion.id == exclusion_id, RetentionExclusion.revoked_at.is_(None))
    )
    if exclusion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exclusao de retencao nao encontrada")
    member_ids = _member_ids_for_exclusion(db, exclusion)
    exclusion.revoked_at = datetime.now(tz=timezone.utc)
    exclusion.revoked_by_user_id = current_user.id
    db.flush()

    # Rebuild only the current situation; archived alerts/tasks are never restored.
    if member_ids:
        from app.services.risk import sync_retention_alerts_from_member_activity

        sync_retention_alerts_from_member_activity(db, member_ids=member_ids)
    log_audit_event(
        db,
        action="retention_exclusion_revoked",
        entity="retention_exclusion",
        entity_id=exclusion.id,
        member_id=exclusion.member_id,
        user=current_user,
        details={"scope": exclusion.scope, "plan_name": exclusion.plan_name},
    )
    db.commit()
    invalidate_dashboard_cache("retention", "tasks", gym_id=current_user.gym_id)


def _to_out(
    exclusion: RetentionExclusion, *, member_name: str | None, created_by_name: str
) -> RetentionExclusionOut:
    return RetentionExclusionOut(
        id=exclusion.id,
        scope=exclusion.scope,
        member_id=exclusion.member_id,
        member_name=member_name,
        plan_name=exclusion.plan_name,
        reason=exclusion.reason,
        created_by_name=created_by_name,
        created_at=exclusion.created_at,
    )
