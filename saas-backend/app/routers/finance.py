from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_request_context, require_roles
from app.database import get_db
from app.models import RoleEnum, User
from app.schemas import (
    APIMessage,
    FinanceFoundationSummaryOut,
    FinancialEntryCreate,
    FinancialEntryOut,
    FinancialEntryUpdate,
    PaginatedResponse,
)
from app.services.audit_service import log_audit_event
from app.services.finance_service import (
    create_financial_entry,
    delete_financial_entry,
    get_finance_foundation_summary,
    list_financial_entries,
    update_financial_entry,
)


router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/entries", response_model=PaginatedResponse[FinancialEntryOut])
def list_entries_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    entry_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
) -> PaginatedResponse[FinancialEntryOut]:
    return list_financial_entries(
        db,
        gym_id=current_user.gym_id,
        page=page,
        page_size=page_size,
        entry_type=entry_type,
        status_filter=status_filter,
        from_date=from_date,
        to_date=to_date,
    )


@router.post("/entries", response_model=FinancialEntryOut, status_code=status.HTTP_201_CREATED)
def create_entry_endpoint(
    request: Request,
    payload: FinancialEntryCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> FinancialEntryOut:
    entry = create_financial_entry(
        db,
        payload,
        gym_id=current_user.gym_id,
        actor_user_id=current_user.id,
        commit=False,
    )
    context = get_request_context(request)
    log_audit_event(
        db,
        action="financial_entry_created",
        entity="financial_entry",
        user=current_user,
        entity_id=entry.id,
        member_id=entry.member_id,
        details={"entry_type": entry.entry_type, "status": entry.status, "amount": float(entry.amount)},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(entry)
    return FinancialEntryOut.model_validate(entry)


@router.patch("/entries/{entry_id}", response_model=FinancialEntryOut)
def update_entry_endpoint(
    request: Request,
    entry_id: UUID,
    payload: FinancialEntryUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> FinancialEntryOut:
    entry = update_financial_entry(db, entry_id, payload, gym_id=current_user.gym_id, commit=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="financial_entry_updated",
        entity="financial_entry",
        user=current_user,
        entity_id=entry.id,
        member_id=entry.member_id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys()), "status": entry.status},
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    db.refresh(entry)
    return FinancialEntryOut.model_validate(entry)


@router.delete("/entries/{entry_id}", response_model=APIMessage)
def delete_entry_endpoint(
    request: Request,
    entry_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> APIMessage:
    delete_financial_entry(db, entry_id, gym_id=current_user.gym_id, commit=False)
    context = get_request_context(request)
    log_audit_event(
        db,
        action="financial_entry_deleted",
        entity="financial_entry",
        user=current_user,
        entity_id=entry_id,
        ip_address=context["ip_address"],
        user_agent=context["user_agent"],
    )
    db.commit()
    return APIMessage(message="Lancamento financeiro removido.")


@router.get("/summary", response_model=FinanceFoundationSummaryOut)
def summary_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleEnum.OWNER, RoleEnum.MANAGER))],
) -> FinanceFoundationSummaryOut:
    return get_finance_foundation_summary(db, gym_id=current_user.gym_id)
