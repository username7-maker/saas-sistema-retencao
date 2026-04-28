from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import FinancialEntry, Member, MemberStatus, Task, TaskPriority, TaskStatus, User
from app.schemas import (
    DelinquencyItemOut,
    DelinquencyMaterializeResultOut,
    DelinquencyStageSummaryOut,
    DelinquencySummaryOut,
    PaginatedResponse,
)
from app.services.task_event_service import record_task_event


@dataclass(frozen=True)
class DelinquencyStageRule:
    stage: str
    label: str
    severity: str
    priority: TaskPriority
    action_label: str
    owner_role: str


STAGE_RULES = {
    "d1": DelinquencyStageRule("d1", "D+1", "medium", TaskPriority.MEDIUM, "Enviar lembrete amigavel", "reception"),
    "d3": DelinquencyStageRule("d3", "D+3", "high", TaskPriority.HIGH, "Regularizar via WhatsApp", "reception"),
    "d7": DelinquencyStageRule("d7", "D+7", "high", TaskPriority.HIGH, "Contato ativo e oferta de ajuda", "reception"),
    "d15": DelinquencyStageRule("d15", "D+15", "critical", TaskPriority.URGENT, "Escalar para gerente", "manager"),
    "d30": DelinquencyStageRule("d30", "D+30", "critical", TaskPriority.URGENT, "Revisar permanencia com gerente", "manager"),
}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _today() -> date:
    return _now().date()


def _stage_for_days(days_overdue: int) -> DelinquencyStageRule:
    if days_overdue >= 30:
        return STAGE_RULES["d30"]
    if days_overdue >= 15:
        return STAGE_RULES["d15"]
    if days_overdue >= 7:
        return STAGE_RULES["d7"]
    if days_overdue >= 3:
        return STAGE_RULES["d3"]
    return STAGE_RULES["d1"]


def _money(value: Decimal | float) -> str:
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _first_name(name: str) -> str:
    return (name or "aluno").strip().split(" ")[0] or "aluno"


def _suggested_message(member_name: str, amount: Decimal, days_overdue: int, stage: str) -> str:
    first_name = _first_name(member_name)
    amount_label = _money(amount)
    if stage == "d1":
        return (
            f"Oi {first_name}, tudo bem? Identificamos uma mensalidade em aberto no valor de {amount_label}. "
            "Pode confirmar para a recepcao a melhor forma de regularizar?"
        )
    if stage == "d3":
        return (
            f"Oi {first_name}, passando para lembrar que existe um valor em aberto de {amount_label}. "
            "Podemos te ajudar a regularizar hoje?"
        )
    if stage == "d7":
        return (
            f"Oi {first_name}, seu cadastro esta com {days_overdue} dias de atraso e valor em aberto de {amount_label}. "
            "Me chama por aqui para combinarmos a regularizacao ou entender se precisa de ajuda."
        )
    if stage == "d15":
        return (
            f"Oi {first_name}, precisamos alinhar a pendencia financeira de {amount_label}. "
            "Vou encaminhar para a gerencia acompanhar e ajudar na melhor solucao."
        )
    return (
        f"Oi {first_name}, sua pendencia financeira chegou a {days_overdue} dias e soma {amount_label}. "
        "Precisamos revisar seu plano com a gerencia para evitar bloqueios ou cancelamento."
    )


def _task_due_for_stage(rule: DelinquencyStageRule) -> datetime:
    hour = 11 if rule.owner_role == "reception" else 10
    return datetime.combine(_today(), time(hour=hour, minute=0), tzinfo=timezone.utc)


def _entry_ids(entries: list[FinancialEntry]) -> list[str]:
    return [str(entry.id) for entry in entries]


def _open_delinquency_task(db: Session, *, gym_id: UUID, member_id: UUID) -> Task | None:
    return db.scalar(
        select(Task)
        .options(joinedload(Task.member), joinedload(Task.lead))
        .where(
            Task.gym_id == gym_id,
            Task.member_id == member_id,
            Task.deleted_at.is_(None),
            Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
            Task.extra_data["source"].astext == "delinquency",
        )
        .order_by(Task.created_at.desc())
    )


def _active_overdue_entries(db: Session, *, gym_id: UUID, normalize_status: bool = False) -> tuple[list[FinancialEntry], int]:
    today = _today()
    entries = list(
        db.scalars(
            select(FinancialEntry)
            .options(joinedload(FinancialEntry.member))
            .where(
                FinancialEntry.gym_id == gym_id,
                FinancialEntry.deleted_at.is_(None),
                FinancialEntry.entry_type == "receivable",
                FinancialEntry.member_id.isnot(None),
                FinancialEntry.status.in_(["open", "overdue"]),
                FinancialEntry.due_date.isnot(None),
                FinancialEntry.due_date < today,
            )
            .order_by(FinancialEntry.due_date.asc())
        )
        .unique()
        .all()
    )
    normalized = 0
    valid_entries: list[FinancialEntry] = []
    for entry in entries:
        member = entry.member
        if not member or member.deleted_at is not None or member.status != MemberStatus.ACTIVE:
            continue
        if normalize_status and entry.status == "open":
            entry.status = "overdue"
            db.add(entry)
            normalized += 1
        valid_entries.append(entry)
    return valid_entries, normalized


def _group_entries_by_member(entries: list[FinancialEntry]) -> dict[UUID, list[FinancialEntry]]:
    grouped: dict[UUID, list[FinancialEntry]] = {}
    for entry in entries:
        if entry.member_id is None:
            continue
        grouped.setdefault(entry.member_id, []).append(entry)
    return grouped


def _build_item(db: Session, *, gym_id: UUID, member: Member, entries: list[FinancialEntry]) -> DelinquencyItemOut:
    oldest_due_date = min(entry.due_date for entry in entries if entry.due_date is not None)
    days_overdue = max(1, (_today() - oldest_due_date).days)
    amount = sum((entry.amount for entry in entries), Decimal("0"))
    rule = _stage_for_days(days_overdue)
    open_task = _open_delinquency_task(db, gym_id=gym_id, member_id=member.id)
    return DelinquencyItemOut(
        member_id=member.id,
        member_name=member.full_name,
        member_phone=member.phone,
        member_email=member.email,
        plan_name=member.plan_name,
        preferred_shift=member.preferred_shift,
        overdue_amount=float(amount),
        overdue_entries_count=len(entries),
        oldest_due_date=oldest_due_date,
        days_overdue=days_overdue,
        stage=rule.stage,  # type: ignore[arg-type]
        severity=rule.severity,
        primary_action_label=rule.action_label,
        suggested_message=_suggested_message(member.full_name, amount, days_overdue, rule.stage),
        open_task_id=open_task.id if open_task else None,
    )


def list_delinquency_items(
    db: Session,
    *,
    gym_id: UUID,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[DelinquencyItemOut]:
    entries, _ = _active_overdue_entries(db, gym_id=gym_id)
    grouped = _group_entries_by_member(entries)
    items = []
    for member_entries in grouped.values():
        member = member_entries[0].member
        if member:
            items.append(_build_item(db, gym_id=gym_id, member=member, entries=member_entries))
    items.sort(key=lambda item: (item.severity == "critical", item.days_overdue, item.overdue_amount), reverse=True)
    start = (page - 1) * page_size
    return PaginatedResponse(items=items[start : start + page_size], total=len(items), page=page, page_size=page_size)


def get_delinquency_summary(db: Session, *, gym_id: UUID) -> DelinquencySummaryOut:
    items_response = list_delinquency_items(db, gym_id=gym_id, page=1, page_size=1000)
    items = items_response.items
    open_task_count = (
        db.scalar(
            select(func.count()).select_from(Task).where(
                Task.gym_id == gym_id,
                Task.deleted_at.is_(None),
                Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
                Task.extra_data["source"].astext == "delinquency",
            )
        )
        or 0
    )
    since = _now() - timedelta(days=30)
    recovered_30d = (
        db.scalar(
            select(func.coalesce(func.sum(FinancialEntry.amount), Decimal("0"))).where(
                FinancialEntry.gym_id == gym_id,
                FinancialEntry.deleted_at.is_(None),
                FinancialEntry.entry_type == "receivable",
                FinancialEntry.status == "paid",
                FinancialEntry.paid_at.isnot(None),
                FinancialEntry.paid_at >= since,
                FinancialEntry.due_date.isnot(None),
                FinancialEntry.due_date < func.date(FinancialEntry.paid_at),
            )
        )
        or Decimal("0")
    )
    by_stage = []
    for stage, rule in STAGE_RULES.items():
        stage_items = [item for item in items if item.stage == stage]
        by_stage.append(
            DelinquencyStageSummaryOut(
                stage=stage,  # type: ignore[arg-type]
                label=rule.label,
                members_count=len(stage_items),
                overdue_amount=round(sum(item.overdue_amount for item in stage_items), 2),
            )
        )
    return DelinquencySummaryOut(
        overdue_amount=round(sum(item.overdue_amount for item in items), 2),
        delinquent_members_count=len(items),
        open_task_count=open_task_count,
        recovered_30d=float(recovered_30d),
        by_stage=by_stage,
        generated_at=_now(),
    )


def _task_extra_for_item(item: DelinquencyItemOut, entries: list[FinancialEntry], rule: DelinquencyStageRule) -> dict:
    return {
        "source": "delinquency",
        "domain": "finance",
        "owner_role": rule.owner_role,
        "delinquency_stage": item.stage,
        "overdue_amount": item.overdue_amount,
        "days_overdue": item.days_overdue,
        "financial_entry_ids": _entry_ids(entries),
        "oldest_due_date": item.oldest_due_date.isoformat(),
        "overdue_entries_count": item.overdue_entries_count,
        "primary_action_label": item.primary_action_label,
        "materialized_at": _now().isoformat(),
    }


def _task_description(item: DelinquencyItemOut) -> str:
    return (
        f"{item.member_name} esta com {item.overdue_entries_count} recebivel(is) vencido(s), "
        f"total de {_money(item.overdue_amount)}, {item.days_overdue} dia(s) em atraso. "
        f"Estagio da regua: {item.stage.upper()}."
    )


def materialize_delinquency_tasks_for_gym(
    db: Session,
    *,
    gym_id: UUID,
    current_user: User | None = None,
    commit: bool = True,
) -> DelinquencyMaterializeResultOut:
    entries, normalized = _active_overdue_entries(db, gym_id=gym_id, normalize_status=True)
    grouped = _group_entries_by_member(entries)
    result = DelinquencyMaterializeResultOut(normalized_entries_count=normalized, items_count=len(grouped))
    for member_id, member_entries in grouped.items():
        member = member_entries[0].member
        if not member:
            result.skipped_count += 1
            continue
        item = _build_item(db, gym_id=gym_id, member=member, entries=member_entries)
        rule = STAGE_RULES[item.stage]
        extra = _task_extra_for_item(item, member_entries, rule)
        open_task = _open_delinquency_task(db, gym_id=gym_id, member_id=member_id)
        if open_task:
            old_extra = dict(open_task.extra_data or {})
            old_stage = old_extra.get("delinquency_stage")
            old_amount = old_extra.get("overdue_amount")
            open_task.title = f"Inadimplencia {rule.label} - {member.full_name}"
            open_task.description = _task_description(item)
            open_task.priority = rule.priority
            open_task.due_date = _task_due_for_stage(rule)
            open_task.suggested_message = item.suggested_message
            open_task.extra_data = {**old_extra, **extra}
            db.add(open_task)
            result.updated_count += 1
            if old_stage != item.stage or float(old_amount or 0) != float(item.overdue_amount):
                record_task_event(
                    db,
                    task=open_task,
                    current_user=current_user,
                    event_type="delinquency_stage_updated",
                    note=f"Regua atualizada para {rule.label}: {_money(item.overdue_amount)} em aberto.",
                    metadata_json={
                        "source": "delinquency_ladder",
                        "old_stage": old_stage,
                        "new_stage": item.stage,
                        "old_amount": old_amount,
                        "new_amount": item.overdue_amount,
                    },
                    flush=False,
                )
            continue
        task = Task(
            gym_id=gym_id,
            member_id=member.id,
            assigned_to_user_id=None,
            title=f"Inadimplencia {rule.label} - {member.full_name}",
            description=_task_description(item),
            priority=rule.priority,
            status=TaskStatus.TODO,
            kanban_column=TaskStatus.TODO.value,
            due_date=_task_due_for_stage(rule),
            suggested_message=item.suggested_message,
            extra_data=extra,
        )
        db.add(task)
        db.flush()
        record_task_event(
            db,
            task=task,
            current_user=current_user,
            event_type="status_changed",
            note=f"Task de inadimplencia criada no estagio {rule.label}.",
            metadata_json={"source": "delinquency_ladder", "stage": item.stage},
            flush=False,
        )
        result.created_count += 1
    if commit:
        db.commit()
    else:
        db.flush()
    return result
