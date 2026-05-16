from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    AutopilotAction,
    AutopilotEvent,
    FinancialEntry,
    Member,
    MemberStatus,
    MessageLog,
    Task,
    TaskPriority,
    TaskStatus,
    User,
)
from app.services.autopilot_safety_service import contains_sensitive_text


def _days_since(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    now = datetime.now(tz=timezone.utc)
    value = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return max((now - value).days, 0)


def _priority_rank(priority: TaskPriority | str | None) -> int:
    value = priority.value if hasattr(priority, "value") else str(priority or "")
    return {"urgent": 4, "high": 3, "medium": 2, "low": 1}.get(value, 0)


def _task_is_open(task: Task) -> bool:
    return task.status in {TaskStatus.TODO, TaskStatus.DOING}


def build_member_next_best_action(
    db: Session,
    *,
    member: Member,
    current_user: User,
    permissions: dict,
    open_tasks: list[Task],
) -> dict:
    sensitive_event = _latest_sensitive_event(db, member)
    if sensitive_event:
        return {
            "key": "sensitive_intervention_required",
            "domain": "relationship",
            "title": "Intervencao humana obrigatoria",
            "reason": "Foi detectada resposta sensivel ou pedido de humano. Nao trate como follow-up simples.",
            "priority": "urgent",
            "owner_role": "manager",
            "can_autopilot": False,
            "autopilot_mode": "blocked",
            "blocked_reasons": ["sensitive_message"],
            "evidence": ["autopilot_event", "message_log"],
            "context_path": f"/members/{member.id}/timeline",
        }

    awaiting_action = _latest_awaiting_autopilot_action(db, member)
    if awaiting_action:
        return {
            "key": "autopilot_waiting_response",
            "domain": awaiting_action.domain,
            "title": "Aguardar resposta do aluno",
            "reason": "Ja existe uma acao do Autopilot aguardando retorno. Evite novo contato antes do timeout.",
            "priority": "medium",
            "owner_role": _owner_role_for_domain(awaiting_action.domain),
            "can_autopilot": False,
            "autopilot_mode": "awaiting_outcome",
            "blocked_reasons": ["awaiting_outcome"],
            "evidence": ["autopilot_action"],
            "context_path": f"/tasks?member_id={member.id}",
        }

    overdue_financial = _open_financial_amount(db, member)
    if overdue_financial and permissions.get("can_view_financial"):
        return {
            "key": "finance_open_overdue",
            "domain": "finance",
            "title": "Regularizar pendencia financeira",
            "reason": f"Existe saldo financeiro aberto/vencido de R$ {overdue_financial:.2f}.",
            "priority": "high",
            "owner_role": "reception",
            "can_autopilot": False,
            "autopilot_mode": "manual",
            "blocked_reasons": [],
            "evidence": ["financial_entries"],
            "context_path": "/dashboard/financial",
        }

    due_task = _top_due_task(open_tasks)
    if due_task:
        return {
            "key": "open_task_due",
            "domain": str((due_task.extra_data or {}).get("domain") or (due_task.extra_data or {}).get("source") or "operation"),
            "title": due_task.title,
            "reason": due_task.description or "Existe tarefa operacional aberta para este aluno.",
            "priority": due_task.priority.value if hasattr(due_task.priority, "value") else str(due_task.priority),
            "owner_role": str((due_task.extra_data or {}).get("owner_role") or "operation"),
            "can_autopilot": bool((due_task.extra_data or {}).get("autopilot_action_id")),
            "autopilot_mode": str((due_task.extra_data or {}).get("autopilot_state") or "human_task"),
            "blocked_reasons": [],
            "evidence": ["task"],
            "task_id": str(due_task.id),
            "context_path": f"/tasks?member_id={member.id}",
        }

    days_without_checkin = _days_since(member.last_checkin_at)
    if member.status == MemberStatus.ACTIVE and days_without_checkin is not None and days_without_checkin >= 14:
        stage = member.retention_stage or "recovery"
        return {
            "key": f"retention_{stage}",
            "domain": "retention",
            "title": "Executar playbook de recuperacao",
            "reason": f"Aluno esta ha {days_without_checkin} dias sem check-in e precisa de acao de retomada.",
            "priority": "high" if days_without_checkin < 30 else "urgent",
            "owner_role": "reception",
            "can_autopilot": True,
            "autopilot_mode": "send_and_wait" if permissions.get("can_use_autopilot") else "assisted",
            "blocked_reasons": [] if permissions.get("can_use_autopilot") else ["role_without_autopilot"],
            "evidence": ["last_checkin_at", "retention_stage", "risk_level"],
            "context_path": "/dashboard/retention",
        }

    if (member.onboarding_status or "active") in {"active", "at_risk"} and (member.onboarding_score or 0) < 70:
        return {
            "key": "onboarding_next_action",
            "domain": "onboarding",
            "title": "Conferir proxima etapa do onboarding",
            "reason": "Aluno ainda esta no ciclo inicial e o score indica que falta evidencia de ativacao.",
            "priority": "medium",
            "owner_role": "reception",
            "can_autopilot": True,
            "autopilot_mode": "auto_close_only",
            "blocked_reasons": [],
            "evidence": ["onboarding_status", "onboarding_score"],
            "context_path": "/tasks?view=onboarding",
        }

    if permissions.get("can_view_clinical"):
        return {
            "key": "coach_review",
            "domain": "trainer",
            "title": "Revisar treino e evolucao",
            "reason": "Sem pendencia critica no momento; mantenha o acompanhamento tecnico do aluno.",
            "priority": "low",
            "owner_role": "coach",
            "can_autopilot": False,
            "autopilot_mode": "manual",
            "blocked_reasons": [],
            "evidence": ["profile360"],
            "context_path": f"/assessments/profile/{member.id}",
        }

    return {
        "key": "relationship_maintenance",
        "domain": "relationship",
        "title": "Manter acompanhamento",
        "reason": "Nao ha pendencia critica detectada neste momento.",
        "priority": "low",
        "owner_role": "operation",
        "can_autopilot": False,
        "autopilot_mode": "none",
        "blocked_reasons": [],
        "evidence": ["member_status", "risk_level"],
        "context_path": f"/members/{member.id}",
    }


def _latest_sensitive_event(db: Session, member: Member) -> AutopilotEvent | MessageLog | None:
    event = db.scalar(
        select(AutopilotEvent)
        .where(AutopilotEvent.gym_id == member.gym_id, AutopilotEvent.member_id == member.id)
        .order_by(desc(AutopilotEvent.created_at))
        .limit(1)
    )
    if event and contains_sensitive_text(str(event.metadata_json or "")):
        return event

    message = db.scalar(
        select(MessageLog)
        .where(MessageLog.gym_id == member.gym_id, MessageLog.member_id == member.id, MessageLog.direction == "inbound")
        .order_by(desc(MessageLog.created_at))
        .limit(1)
    )
    if message and contains_sensitive_text(message.content or ""):
        return message
    return None


def _latest_awaiting_autopilot_action(db: Session, member: Member) -> AutopilotAction | None:
    return db.scalar(
        select(AutopilotAction)
        .where(
            AutopilotAction.gym_id == member.gym_id,
            AutopilotAction.member_id == member.id,
            AutopilotAction.status == "awaiting_outcome",
        )
        .order_by(desc(AutopilotAction.created_at))
        .limit(1)
    )


def _open_financial_amount(db: Session, member: Member) -> float | None:
    rows = db.scalars(
        select(FinancialEntry).where(
            FinancialEntry.gym_id == member.gym_id,
            FinancialEntry.member_id == member.id,
            FinancialEntry.entry_type == "receivable",
            FinancialEntry.status.in_(["open", "overdue"]),
        )
    ).all()
    total = sum((row.amount or Decimal("0")) for row in rows)
    return float(total) if total > 0 else None


def _top_due_task(open_tasks: list[Task]) -> Task | None:
    candidates = [task for task in open_tasks if _task_is_open(task)]
    if not candidates:
        return None
    now = datetime.now(tz=timezone.utc)
    return sorted(
        candidates,
        key=lambda task: (
            0 if task.due_date and (task.due_date if task.due_date.tzinfo else task.due_date.replace(tzinfo=timezone.utc)) <= now else 1,
            -_priority_rank(task.priority),
            task.due_date or task.created_at,
        ),
    )[0]


def _owner_role_for_domain(domain: str) -> str:
    return {
        "retention": "reception",
        "onboarding": "reception",
        "finance": "reception",
        "commercial": "sales",
        "assessment": "coach",
        "trainer": "coach",
    }.get(domain, "operation")
