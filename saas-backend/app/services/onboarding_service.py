from datetime import datetime, time, timedelta, timezone

from app.core.cache import invalidate_dashboard_cache
from app.models import Member, Task, TaskPriority, TaskStatus
from sqlalchemy.orm import Session


ONBOARDING_PLAYBOOK: list[dict[str, int | str | None]] = [
    {"day_offset": 0, "title": "Conferir cadastro do aluno", "description": "Validar dados de contato e plano contratado."},
    {"day_offset": 1, "title": "Conferir se o treino foi montado", "description": "Confirmar com a equipe tecnica se o treino inicial foi criado."},
    {"day_offset": 3, "title": "Primeiro check-in", "description": "Verificar se o aluno realizou o primeiro check-in."},
    {"day_offset": 7, "title": "Avaliacao fisica", "description": "Agendar ou confirmar avaliacao fisica inicial."},
    {"day_offset": 15, "title": "Revisao tecnica", "description": "Revisar adaptacao do aluno e ajustar orientacoes."},
    {"day_offset": 30, "title": "Fechamento do onboarding", "description": "Concluir ciclo inicial e registrar feedback."},
]

PLAN_FOLLOWUP_PLAYBOOK: dict[str, list[int]] = {
    "mensal": [45, 55, 60],
    "semestral": [60, 90, 120, 150, 180],
    "anual": [60, 90, 180, 270, 360],
}


def _detect_plan_type(plan_name: str | None) -> str:
    plan_text = (plan_name or "").lower()
    if "anual" in plan_text:
        return "anual"
    if "semestral" in plan_text:
        return "semestral"
    return "mensal"


def create_onboarding_tasks_for_member(db: Session, member: Member) -> list[Task]:
    base_date = datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)
    tasks: list[Task] = []

    for step in ONBOARDING_PLAYBOOK:
        day_offset = int(step["day_offset"])
        task = Task(
            gym_id=member.gym_id,
            member_id=member.id,
            title=str(step["title"]),
            description=str(step["description"]) if step.get("description") else None,
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.TODO,
            kanban_column=TaskStatus.TODO.value,
            due_date=base_date + timedelta(days=day_offset),
            extra_data={
                "source": "onboarding",
                "onboarding_phase": "initial",
                "day_offset": day_offset,
            },
        )
        tasks.append(task)

    if tasks:
        db.add_all(tasks)
        db.commit()
        invalidate_dashboard_cache("tasks")
    return tasks


def create_plan_followup_tasks_for_member(db: Session, member: Member) -> list[Task]:
    plan_type = _detect_plan_type(member.plan_name)
    steps = PLAN_FOLLOWUP_PLAYBOOK.get(plan_type, [])
    base_date = datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)
    tasks: list[Task] = []

    for day_offset in steps:
        task = Task(
            gym_id=member.gym_id,
            member_id=member.id,
            title=f"Follow-up do plano ({plan_type}) - D+{day_offset}",
            description="Acompanhamento programado do plano do aluno.",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.TODO,
            kanban_column=TaskStatus.TODO.value,
            due_date=base_date + timedelta(days=day_offset),
            extra_data={
                "source": "plan_followup",
                "plan_type": plan_type,
                "day_offset": day_offset,
            },
        )
        tasks.append(task)

    if tasks:
        db.add_all(tasks)
        db.commit()
        invalidate_dashboard_cache("tasks")
    return tasks
