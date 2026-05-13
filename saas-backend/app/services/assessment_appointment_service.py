from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import AssessmentAppointment, Member, RoleEnum, Task, TaskEvent, TaskPriority, TaskStatus, User
from app.schemas import PaginatedResponse
from app.schemas.assessment_appointment import (
    AssessmentAppointmentCreate,
    AssessmentAppointmentOut,
    AssessmentAppointmentUpdate,
)

APPOINTMENT_STATUSES = {"scheduled", "confirmed", "attended", "no_show", "cancelled", "rescheduled", "completed"}
PAYMENT_STATUSES = {"unknown", "pending", "paid", "waived", "not_required"}
HISTORICAL_COVERAGE_STATUSES = {"attended", "completed"}


def normalize_appointment_status(raw_value: str | None) -> str:
    key = _normalize_key(raw_value or "")
    mapping = {
        "scheduled": "scheduled",
        "agendado": "scheduled",
        "marcado": "scheduled",
        "confirmed": "confirmed",
        "confirmado": "confirmed",
        "confirmada": "confirmed",
        "attended": "attended",
        "compareceu": "attended",
        "presente": "attended",
        "sim": "attended",
        "ok": "attended",
        "realizada": "completed",
        "realizado": "completed",
        "concluida": "completed",
        "concluido": "completed",
        "completed": "completed",
        "no_show": "no_show",
        "faltou": "no_show",
        "falta": "no_show",
        "ausente": "no_show",
        "nao_compareceu": "no_show",
        "nao": "no_show",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "cancelado": "cancelled",
        "cancelada": "cancelled",
        "rescheduled": "rescheduled",
        "remarcado": "rescheduled",
        "remarcada": "rescheduled",
    }
    return mapping.get(key, "scheduled")


def normalize_payment_status(raw_value: str | None) -> str:
    key = _normalize_key(raw_value or "")
    mapping = {
        "unknown": "unknown",
        "": "unknown",
        "pendente": "pending",
        "pending": "pending",
        "em_aberto": "pending",
        "aberto": "pending",
        "nao_pago": "pending",
        "nao_paga": "pending",
        "falta_pagar": "pending",
        "pago": "paid",
        "paga": "paid",
        "paid": "paid",
        "quitado": "paid",
        "recebido": "paid",
        "sim": "paid",
        "isento": "waived",
        "cortesia": "waived",
        "waived": "waived",
        "nao_se_aplica": "not_required",
        "sem_cobranca": "not_required",
        "not_required": "not_required",
    }
    return mapping.get(key, "unknown")


def list_assessment_appointments(
    db: Session,
    *,
    gym_id: UUID,
    page: int = 1,
    page_size: int = 50,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    payment_status: str | None = None,
    evaluator_user_id: UUID | None = None,
    search: str | None = None,
) -> PaginatedResponse[AssessmentAppointmentOut]:
    filters = [AssessmentAppointment.gym_id == gym_id, AssessmentAppointment.deleted_at.is_(None)]
    if date_from:
        filters.append(AssessmentAppointment.scheduled_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        filters.append(AssessmentAppointment.scheduled_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    if status:
        filters.append(AssessmentAppointment.status == normalize_appointment_status(status))
    if payment_status:
        normalized_payment = normalize_payment_status(payment_status)
        if normalized_payment in PAYMENT_STATUSES:
            filters.append(AssessmentAppointment.payment_status == normalized_payment)
    if evaluator_user_id:
        filters.append(AssessmentAppointment.evaluator_user_id == evaluator_user_id)
    if search:
        value = f"%{search.strip()}%"
        filters.append(
            or_(
                Member.full_name.ilike(value),
                Member.email.ilike(value),
                AssessmentAppointment.evaluator_name_raw.ilike(value),
                AssessmentAppointment.notes.ilike(value),
            )
        )

    total_stmt = (
        select(func.count(AssessmentAppointment.id))
        .select_from(AssessmentAppointment)
        .join(Member, Member.id == AssessmentAppointment.member_id)
        .where(and_(*filters))
    )
    total = int(db.scalar(total_stmt) or 0)
    rows = db.execute(
        select(AssessmentAppointment, Member, User)
        .join(Member, Member.id == AssessmentAppointment.member_id)
        .outerjoin(User, User.id == AssessmentAppointment.evaluator_user_id)
        .where(and_(*filters))
        .order_by(AssessmentAppointment.scheduled_at.asc(), Member.full_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return PaginatedResponse(
        items=[_appointment_out(appointment, member=member, evaluator=user) for appointment, member, user in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_assessment_appointment(
    db: Session,
    *,
    gym_id: UUID,
    payload: AssessmentAppointmentCreate,
    created_by_user_id: UUID | None = None,
    commit: bool = True,
) -> AssessmentAppointment:
    member = _get_member(db, gym_id, payload.member_id)
    evaluator = _resolve_evaluator(db, gym_id=gym_id, evaluator_user_id=payload.evaluator_user_id, evaluator_name=payload.evaluator_name_raw)
    appointment = AssessmentAppointment(
        gym_id=gym_id,
        member_id=member.id,
        scheduled_at=_ensure_tz(payload.scheduled_at),
        assessment_type=(payload.assessment_type or "physical_assessment").strip()[:60],
        status=normalize_appointment_status(payload.status),
        payment_status=normalize_payment_status(payload.payment_status),
        evaluator_user_id=evaluator.id if evaluator else payload.evaluator_user_id,
        evaluator_name_raw=(payload.evaluator_name_raw or (evaluator.full_name if evaluator else "") or None),
        notes=payload.notes,
        source=payload.source or "manual",
        external_reference=(payload.external_reference or None),
        metadata_json=dict(payload.metadata_json or {}),
    )
    db.add(appointment)
    db.flush()
    apply_assessment_appointment_operational_effects(db, appointment, created_by_user_id=created_by_user_id)
    if commit:
        db.commit()
        db.refresh(appointment)
    return appointment


def update_assessment_appointment(
    db: Session,
    *,
    appointment_id: UUID,
    gym_id: UUID,
    payload: AssessmentAppointmentUpdate,
    updated_by_user_id: UUID | None = None,
    commit: bool = True,
) -> AssessmentAppointment:
    appointment = db.scalar(
        select(AssessmentAppointment).where(
            AssessmentAppointment.id == appointment_id,
            AssessmentAppointment.gym_id == gym_id,
            AssessmentAppointment.deleted_at.is_(None),
        )
    )
    if not appointment:
        raise ValueError("Agendamento de avaliacao nao encontrado.")

    data = payload.model_dump(exclude_unset=True)
    if "scheduled_at" in data and data["scheduled_at"] is not None:
        appointment.scheduled_at = _ensure_tz(data["scheduled_at"])
    if "assessment_type" in data and data["assessment_type"] is not None:
        appointment.assessment_type = str(data["assessment_type"]).strip()[:60] or "physical_assessment"
    if "status" in data and data["status"] is not None:
        appointment.status = normalize_appointment_status(data["status"])
    if "payment_status" in data and data["payment_status"] is not None:
        appointment.payment_status = normalize_payment_status(data["payment_status"])
    if "evaluator_user_id" in data:
        appointment.evaluator_user_id = data["evaluator_user_id"]
    if "evaluator_name_raw" in data:
        appointment.evaluator_name_raw = (data["evaluator_name_raw"] or None)
    if "notes" in data:
        appointment.notes = data["notes"]
    if "source" in data and data["source"] is not None:
        appointment.source = str(data["source"]).strip()[:60] or "manual"
    if "external_reference" in data:
        appointment.external_reference = data["external_reference"] or None
    if "metadata_json" in data and data["metadata_json"] is not None:
        appointment.metadata_json = dict(data["metadata_json"] or {})

    if appointment.evaluator_user_id is None and appointment.evaluator_name_raw:
        evaluator = _resolve_evaluator(db, gym_id=gym_id, evaluator_name=appointment.evaluator_name_raw)
        if evaluator:
            appointment.evaluator_user_id = evaluator.id

    db.add(appointment)
    db.flush()
    apply_assessment_appointment_operational_effects(db, appointment, created_by_user_id=updated_by_user_id)
    if commit:
        db.commit()
        db.refresh(appointment)
    return appointment


def apply_assessment_appointment_operational_effects(
    db: Session,
    appointment: AssessmentAppointment,
    *,
    created_by_user_id: UUID | None = None,
) -> None:
    member = appointment.member or db.get(Member, appointment.member_id)
    if not member:
        return
    if appointment.status == "no_show":
        _ensure_operational_task(
            db,
            appointment=appointment,
            member=member,
            source="assessment_appointment_no_show",
            title=f"Remarcar avaliacao de {member.full_name}",
            description=(
                "Aluno faltou na avaliacao agendada. Confirmar motivo, remarcar horario e registrar resultado."
            ),
            priority=TaskPriority.HIGH,
            created_by_user_id=created_by_user_id,
            event_note="Task criada automaticamente por falta em avaliacao agendada.",
        )
    if appointment.payment_status == "pending":
        _ensure_operational_task(
            db,
            appointment=appointment,
            member=member,
            source="assessment_appointment_payment_pending",
            title=f"Regularizar pagamento da avaliacao de {member.full_name}",
            description=(
                "Avaliacao marcada/importada com pagamento pendente. Verificar cobranca com recepcao/gestao."
            ),
            priority=TaskPriority.MEDIUM,
            created_by_user_id=created_by_user_id,
            event_note="Task criada automaticamente por pagamento pendente da avaliacao.",
        )


def serialize_assessment_appointment(appointment: AssessmentAppointment) -> AssessmentAppointmentOut:
    return _appointment_out(appointment, member=appointment.member, evaluator=appointment.evaluator_user)


def _ensure_operational_task(
    db: Session,
    *,
    appointment: AssessmentAppointment,
    member: Member,
    source: str,
    title: str,
    description: str,
    priority: TaskPriority,
    created_by_user_id: UUID | None,
    event_note: str,
) -> Task:
    existing = db.scalar(
        select(Task).where(
            Task.gym_id == appointment.gym_id,
            Task.member_id == appointment.member_id,
            Task.deleted_at.is_(None),
            Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
            Task.extra_data["source"].astext == source,
            Task.extra_data["assessment_appointment_id"].astext == str(appointment.id),
        )
    )
    if existing:
        return existing

    task = Task(
        gym_id=appointment.gym_id,
        member_id=appointment.member_id,
        title=title[:160],
        description=description,
        priority=priority,
        status=TaskStatus.TODO,
        kanban_column=TaskStatus.TODO.value,
        due_date=datetime.now(tz=timezone.utc),
        suggested_message=None,
        extra_data={
            "source": source,
            "domain": "assessment",
            "owner_role": "reception",
            "assessment_appointment_id": str(appointment.id),
            "assessment_appointment_status": appointment.status,
            "assessment_payment_status": appointment.payment_status,
            "preferred_shift": member.preferred_shift,
            "evaluator_name": appointment.evaluator_name_raw,
        },
    )
    db.add(task)
    db.flush()
    db.add(
        TaskEvent(
            gym_id=task.gym_id,
            task_id=task.id,
            member_id=task.member_id,
            user_id=created_by_user_id,
            event_type="status_changed",
            note=event_note,
            metadata_json={
                "source": source,
                "assessment_appointment_id": str(appointment.id),
                "appointment_status": appointment.status,
                "payment_status": appointment.payment_status,
            },
        )
    )
    return task


def _appointment_out(appointment: AssessmentAppointment, *, member: Member | None, evaluator: User | None) -> AssessmentAppointmentOut:
    evaluator_name = evaluator.full_name if evaluator else appointment.evaluator_name_raw
    return AssessmentAppointmentOut(
        id=appointment.id,
        gym_id=appointment.gym_id,
        member_id=appointment.member_id,
        member_name=member.full_name if member else None,
        scheduled_at=appointment.scheduled_at,
        assessment_type=appointment.assessment_type,
        status=appointment.status,
        payment_status=appointment.payment_status,
        evaluator_user_id=appointment.evaluator_user_id,
        evaluator_name=evaluator_name,
        evaluator_name_raw=appointment.evaluator_name_raw,
        notes=appointment.notes,
        source=appointment.source,
        external_reference=appointment.external_reference,
        metadata_json=appointment.metadata_json or {},
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
    )


def _get_member(db: Session, gym_id: UUID, member_id: UUID) -> Member:
    member = db.scalar(
        select(Member).where(Member.id == member_id, Member.gym_id == gym_id, Member.deleted_at.is_(None))
    )
    if not member:
        raise ValueError("Aluno nao encontrado para agenda de avaliacao.")
    return member


def _resolve_evaluator(
    db: Session,
    *,
    gym_id: UUID,
    evaluator_user_id: UUID | None = None,
    evaluator_name: str | None = None,
) -> User | None:
    if evaluator_user_id:
        return db.scalar(
            select(User).where(
                User.id == evaluator_user_id,
                User.gym_id == gym_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        )
    name_key = _normalize_key(evaluator_name or "")
    if not name_key:
        return None
    users = list(
        db.scalars(
            select(User).where(
                User.gym_id == gym_id,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.role == RoleEnum.TRAINER,
            )
        ).all()
    )
    for user in users:
        if _normalize_key(user.full_name) == name_key:
            return user
    return None


def _ensure_tz(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_key(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
