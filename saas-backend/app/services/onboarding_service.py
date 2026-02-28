from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Task, TaskPriority, TaskStatus


def _detect_plan_type(plan_name: str | None) -> str:
    v = (plan_name or "").lower()
    if "anual" in v:
        return "anual"
    if "semestral" in v:
        return "semestral"
    return "mensal"


ONBOARDING_PLAYBOOK: list[tuple[int, str, str]] = [
    (0, "Conferir cadastro do aluno", "Verificar dados e documentos do aluno"),
    (1, "Conferir montagem do treino", "Confirmar que o treino foi configurado no sistema"),
    (3, "Primeiro check-in", "Realizar contato inicial com o aluno"),
    (7, "Avaliacao fisica", "Agendar ou registrar avaliacao fisica"),
    (15, "Revisao tecnica", "Revisao da execucao dos exercicios"),
    (30, "Fechamento do onboarding", "Coletar feedback do primeiro mes"),
]

PLAN_FOLLOWUP_PLAYBOOK: dict[str, list[tuple[int, str, str]]] = {
    "mensal": [
        (45, "Acompanhamento mensal 1", ""),
        (55, "Acompanhamento mensal 2", ""),
        (60, "Renovacao mensal", ""),
    ],
    "semestral": [
        (60, "Follow-up 60d", ""),
        (90, "Follow-up 90d", ""),
        (120, "Follow-up 120d", ""),
        (150, "Follow-up 150d", ""),
        (180, "Renovacao semestral", ""),
    ],
    "anual": [
        (60, "Follow-up 60d", ""),
        (90, "Follow-up 90d", ""),
        (180, "Follow-up 180d", ""),
        (270, "Follow-up 270d", ""),
        (360, "Renovacao anual", ""),
    ],
}


def create_onboarding_tasks_for_member(db: Session, member: object) -> None:
    base = datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)  # type: ignore[attr-defined]
    tasks = [
        Task(
            gym_id=member.gym_id,  # type: ignore[attr-defined]
            member_id=member.id,  # type: ignore[attr-defined]
            title=title,
            description=desc or None,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            kanban_column="todo",
            due_date=base + timedelta(days=d),
            extra_data={"source": "onboarding", "onboarding_phase": "initial", "day_offset": d},
        )
        for d, title, desc in ONBOARDING_PLAYBOOK
    ]
    db.add_all(tasks)
    db.commit()


def create_plan_followup_tasks_for_member(db: Session, member: object) -> None:
    plan_type = _detect_plan_type(member.plan_name)  # type: ignore[attr-defined]
    steps = PLAN_FOLLOWUP_PLAYBOOK.get(plan_type, [])
    if not steps:
        return
    base = datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)  # type: ignore[attr-defined]
    tasks = [
        Task(
            gym_id=member.gym_id,  # type: ignore[attr-defined]
            member_id=member.id,  # type: ignore[attr-defined]
            title=title,
            description=desc or None,
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            kanban_column="todo",
            due_date=base + timedelta(days=d),
            extra_data={"source": "plan_followup", "plan_type": plan_type, "day_offset": d},
        )
        for d, title, desc in steps
    ]
    db.add_all(tasks)
    db.commit()
