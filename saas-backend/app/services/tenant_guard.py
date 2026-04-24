from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lead, Member, User


def _not_found(entity: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} nao encontrado")


def _exists_in_gym(db: Session, model: type, obj_id: UUID, gym_id: UUID, entity: str) -> None:
    filters = [model.id == obj_id, model.gym_id == gym_id]
    if hasattr(model, "deleted_at"):
        filters.append(model.deleted_at.is_(None))
    found = db.scalar(select(model.id).where(*filters).execution_options(include_all_tenants=True))
    if not found:
        raise _not_found(entity)


def ensure_user_in_gym(db: Session, user_id: UUID, gym_id: UUID) -> None:
    _exists_in_gym(db, User, user_id, gym_id, "Usuario")


def ensure_member_in_gym(db: Session, member_id: UUID, gym_id: UUID) -> None:
    _exists_in_gym(db, Member, member_id, gym_id, "Membro")


def ensure_lead_in_gym(db: Session, lead_id: UUID, gym_id: UUID) -> None:
    _exists_in_gym(db, Lead, lead_id, gym_id, "Lead")


def ensure_optional_user_in_gym(db: Session, user_id: UUID | None, gym_id: UUID) -> None:
    if user_id:
        ensure_user_in_gym(db, user_id, gym_id)


def ensure_optional_member_in_gym(db: Session, member_id: UUID | None, gym_id: UUID) -> None:
    if member_id:
        ensure_member_in_gym(db, member_id, gym_id)


def ensure_optional_lead_in_gym(db: Session, lead_id: UUID | None, gym_id: UUID) -> None:
    if lead_id:
        ensure_lead_in_gym(db, lead_id, gym_id)
