from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database import get_db
from app.models import MemberStatus, RiskLevel, RoleEnum, User
from app.schemas import APIMessage, MemberCreate, MemberOut, MemberUpdate, PaginatedResponse
from app.services.member_service import create_member, list_members, soft_delete_member, update_member
from app.services.risk import run_daily_risk_processing


router = APIRouter(prefix="/members", tags=["members"])


@router.post("/", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def create_member_endpoint(
    payload: MemberCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> MemberOut:
    return create_member(db, payload)


@router.get("/", response_model=PaginatedResponse[MemberOut])
def list_members_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST, RoleEnum.SALESPERSON))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    risk_level: RiskLevel | None = None,
    status: MemberStatus | None = None,
    min_days_without_checkin: int | None = Query(default=None, ge=0),
) -> PaginatedResponse[MemberOut]:
    return list_members(
        db,
        page=page,
        page_size=page_size,
        search=search,
        risk_level=risk_level,
        status=status,
        min_days_without_checkin=min_days_without_checkin,
    )


@router.patch("/{member_id}", response_model=MemberOut)
def update_member_endpoint(
    member_id: UUID,
    payload: MemberUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.RECEPTIONIST))],
) -> MemberOut:
    return update_member(db, member_id, payload)


@router.delete("/{member_id}", response_model=APIMessage)
def delete_member_endpoint(
    member_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> APIMessage:
    soft_delete_member(db, member_id)
    return APIMessage(message="Membro removido com soft delete")


@router.post("/recalculate-risk", response_model=dict[str, int])
def recalculate_risk_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> dict[str, int]:
    return run_daily_risk_processing(db)
