from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Member, Task, TaskPriority, TaskStatus
from app.models.assessment import Assessment


def build_actions(member: Member, latest_assessment: Assessment | None, *, diagnosis: dict, forecast: dict) -> list[dict]:
    actions: list[dict] = []

    if diagnosis["primary_bottleneck"] == "consistency":
        actions.append(
            _action(
                key="consistency_recovery",
                title=f"Ativar frequencia de {member.full_name}",
                owner_role="reception",
                priority="high",
                reason="Baixa consistencia de treino nas primeiras semanas.",
                due_in_days=1,
                suggested_message="Vamos reorganizar sua rotina para destravar a frequencia desta semana?",
            )
        )

    if diagnosis["frustration_risk"] >= 70:
        actions.append(
            _action(
                key="expectation_reset",
                title=f"Realinhar expectativa com {member.full_name}",
                owner_role="manager",
                priority="urgent",
                reason="Risco alto de frustracao por distancia entre meta e progresso percebido.",
                due_in_days=1,
                suggested_message="Quero te mostrar onde voce ja evoluiu e o que precisa mudar para acelerar o resultado.",
            )
        )

    if diagnosis["primary_bottleneck"] == "restriction":
        actions.append(
            _action(
                key="coach_review",
                title=f"Professor revisar restricoes de {member.full_name}",
                owner_role="coach",
                priority="high",
                reason="Dor, restricao ou historico clinico estao limitando a progressao.",
                due_in_days=2,
                suggested_message="Vamos ajustar sua experiencia para manter progresso com seguranca.",
            )
        )

    if forecast["probability_60d"] < 45:
        actions.append(
            _action(
                key="goal_review",
                title=f"Revisar meta de {member.full_name}",
                owner_role="manager",
                priority="high",
                reason="Probabilidade atual de meta baixa no horizonte de 60 dias.",
                due_in_days=3,
                suggested_message="Sua meta e possivel, mas precisamos corrigir alguns pontos para chegar com previsibilidade.",
            )
        )

    if not actions:
        actions.append(
            _action(
                key="maintain_momentum",
                title=f"Reforcar progresso de {member.full_name}",
                owner_role="coach",
                priority="medium",
                reason="Aluno em curva saudavel; reforcar percepcao de valor e proxima meta.",
                due_in_days=5,
                suggested_message="Seu progresso esta dentro da curva esperada. Vamos manter ritmo e clareza de meta.",
            )
        )

    return actions


def sync_assessment_tasks(
    db: Session,
    member: Member,
    latest_assessment: Assessment | None,
    *,
    actions: list[dict],
    commit: bool = True,
) -> None:
    now = datetime.now(tz=timezone.utc)
    created_any = False
    for action in actions:
        existing = db.scalar(
            select(Task).where(
                Task.member_id == member.id,
                Task.deleted_at.is_(None),
                Task.status.in_((TaskStatus.TODO, TaskStatus.DOING)),
                Task.title == action["title"],
            )
        )
        if existing:
            continue

        task = Task(
            gym_id=member.gym_id,
            member_id=member.id,
            title=action["title"],
            description=action["reason"],
            priority=_priority_enum(action["priority"]),
            status=TaskStatus.TODO,
            kanban_column=TaskStatus.TODO.value,
            due_date=now + timedelta(days=action["due_in_days"]),
            suggested_message=action["suggested_message"],
            extra_data={
                "source": "assessment_intelligence",
                "action_key": action["key"],
                "owner_role": action["owner_role"],
                "assessment_id": str(latest_assessment.id) if latest_assessment else None,
            },
        )
        db.add(task)
        created_any = True

    if created_any:
        if commit:
            db.commit()
        else:
            db.flush()
        invalidate_dashboard_cache("tasks")


def _action(
    *,
    key: str,
    title: str,
    owner_role: str,
    priority: str,
    reason: str,
    due_in_days: int,
    suggested_message: str,
) -> dict:
    return {
        "key": key,
        "title": title,
        "owner_role": owner_role,
        "priority": priority,
        "reason": reason,
        "due_in_days": due_in_days,
        "suggested_message": suggested_message,
    }


def _priority_enum(value: str) -> TaskPriority:
    mapping = {
        "low": TaskPriority.LOW,
        "medium": TaskPriority.MEDIUM,
        "high": TaskPriority.HIGH,
        "urgent": TaskPriority.URGENT,
    }
    return mapping.get(value, TaskPriority.MEDIUM)
