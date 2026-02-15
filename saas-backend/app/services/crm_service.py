from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import Lead, LeadStage, Member, Task, TaskPriority, TaskStatus
from app.schemas import LeadCreate, LeadUpdate, PaginatedResponse
from app.utils.email import send_email


def create_lead(db: Session, payload: LeadCreate) -> Lead:
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def list_leads(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    stage: LeadStage | None = None,
) -> PaginatedResponse:
    filters = [Lead.deleted_at.is_(None)]
    if stage:
        filters.append(Lead.stage == stage)

    stmt = select(Lead).where(and_(*filters)).order_by(Lead.updated_at.desc())
    total = db.scalar(select(func.count()).select_from(Lead).where(and_(*filters))) or 0
    offset = (page - 1) * page_size
    items = db.scalars(stmt.offset(offset).limit(page_size)).all()
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


def update_lead(db: Session, lead_id: UUID, payload: LeadUpdate) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead or lead.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead nao encontrado")

    previous_stage = lead.stage
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(lead, key, value)
    if payload.stage and payload.stage != previous_stage:
        lead.last_contact_at = datetime.now(tz=timezone.utc)

    if lead.stage == LeadStage.WON and not lead.converted_member_id:
        member = Member(
            full_name=lead.full_name,
            email=lead.email,
            phone=lead.phone,
            plan_name="Plano Base",
            monthly_fee=lead.estimated_value,
        )
        db.add(member)
        db.flush()
        lead.converted_member_id = member.id
        if lead.email:
            send_email(lead.email, "Bem-vindo a academia", "Sua matricula foi confirmada. Bem-vindo!")

    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def run_followup_automation(db: Session) -> int:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=2)
    leads = db.scalars(
        select(Lead).where(
            Lead.deleted_at.is_(None),
            Lead.stage.notin_([LeadStage.WON, LeadStage.LOST]),
            or_(Lead.last_contact_at.is_(None), Lead.last_contact_at < cutoff),
        )
    ).all()

    created = 0
    for lead in leads:
        existing_task = db.scalar(
            select(Task).where(
                Task.lead_id == lead.id,
                Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
                Task.deleted_at.is_(None),
                Task.title.ilike("%follow-up%"),
            )
        )
        if existing_task:
            continue

        task = Task(
            lead_id=lead.id,
            assigned_to_user_id=lead.owner_id,
            title=f"Follow-up lead {lead.full_name}",
            description="Lead sem contato ha 2 dias.",
            priority=TaskPriority.HIGH,
            status=TaskStatus.TODO,
            kanban_column=TaskStatus.TODO.value,
        )
        db.add(task)
        created += 1

    db.commit()
    return created


def calculate_cac(db: Session) -> float:
    won_count = db.scalar(
        select(func.count()).select_from(Lead).where(Lead.stage == LeadStage.WON, Lead.deleted_at.is_(None))
    ) or 0
    total_cost = db.scalar(
        select(func.coalesce(func.sum(Lead.acquisition_cost), Decimal("0"))).where(Lead.deleted_at.is_(None))
    ) or Decimal("0")
    if won_count == 0:
        return 0.0
    return float(total_cost / won_count)
