from datetime import date, datetime, time, timedelta, timezone
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Task, TaskPriority, TaskStatus


def _detect_plan_type(plan_name: str | None) -> str:
    v = (plan_name or "").lower()
    if "anual" in v:
        return "anual"
    if "semestral" in v:
        return "semestral"
    return "mensal"


class PlaybookStep(NamedTuple):
    days: int
    title: str
    description: str
    suggested_message: str
    priority: TaskPriority


ONBOARDING_PLAYBOOK: list[PlaybookStep] = [
    PlaybookStep(
        days=0,
        title="Conferir cadastro do aluno",
        description="Verificar dados pessoais, documentos e configuracoes iniciais do aluno no sistema.",
        suggested_message=(
            "Ola, {name}! Seja muito bem-vindo(a) a nossa academia! "
            "Confirme se recebeu nosso e-mail de boas-vindas e se conseguiu acessar o app. "
            "Qualquer duvida, pode me chamar!"
        ),
        priority=TaskPriority.HIGH,
    ),
    PlaybookStep(
        days=1,
        title="Conferir montagem do treino",
        description="Confirmar que o treino personalizado foi configurado no sistema e apresentado ao aluno.",
        suggested_message=(
            "Oi, {name}! Seu treino ja esta montado e disponivel no app. "
            "Precisa de qualquer ajuda para comecar, pode contar comigo!"
        ),
        priority=TaskPriority.HIGH,
    ),
    PlaybookStep(
        days=3,
        title="Contato pos primeiro treino",
        description="Realizar contato inicial para saber como foram os primeiros treinos e resolver duvidas.",
        suggested_message=(
            "Oi, {name}! Ja esta se adaptando bem? "
            "Conta pra mim como foram seus primeiros treinos — fico feliz em saber!"
        ),
        priority=TaskPriority.HIGH,
    ),
    PlaybookStep(
        days=7,
        title="Agendar avaliacao fisica",
        description="Agendar ou registrar a primeira avaliacao fisica do aluno na primeira semana.",
        suggested_message=(
            "Ola, {name}! Ja faz uma semana que voce esta com a gente! "
            "Vamos agendar sua avaliacao fisica? Me fala qual horario e melhor para voce."
        ),
        priority=TaskPriority.MEDIUM,
    ),
    PlaybookStep(
        days=15,
        title="Revisao tecnica de execucao",
        description="Revisar a execucao dos exercicios para garantir seguranca e eficiencia no treino.",
        suggested_message=(
            "Oi, {name}! Ja esta na metade do seu primeiro mes! "
            "Que tal marcarmos uma revisao da sua execucao dos exercicios? "
            "Quero garantir que voce esta treinando com seguranca e eficiencia!"
        ),
        priority=TaskPriority.MEDIUM,
    ),
    PlaybookStep(
        days=30,
        title="Fechamento do onboarding — feedback do 1o mes",
        description="Coletar feedback sobre a experiencia do primeiro mes, registrar satisfacao e fidelizar o aluno.",
        suggested_message=(
            "Parabens, {name}! Voce completou seu primeiro mes com a gente! "
            "Como foi essa experiencia? Me conta o que gostou e o que podemos melhorar para voce. "
            "Sua opiniao e muito importante!"
        ),
        priority=TaskPriority.HIGH,
    ),
]

PLAN_FOLLOWUP_PLAYBOOK: dict[str, list[PlaybookStep]] = {
    "mensal": [
        PlaybookStep(
            days=45,
            title="Acompanhamento mensal — semana 6",
            description="Verificar engajamento, frequencia e satisfacao antes da metade do ciclo.",
            suggested_message=(
                "Oi, {name}! Como estao os treinos? "
                "Qualquer ajuste que precisar no seu treino, e so me avisar!"
            ),
            priority=TaskPriority.MEDIUM,
        ),
        PlaybookStep(
            days=55,
            title="Alerta de renovacao — 5 dias antes",
            description="Contato proativo para renovacao do plano mensal antes do vencimento.",
            suggested_message=(
                "Ola, {name}! Seu plano vence em breve. "
                "Ja garantimos sua renovacao para voce continuar treinando sem interrupcao. "
                "Posso te ajudar com alguma coisa?"
            ),
            priority=TaskPriority.HIGH,
        ),
        PlaybookStep(
            days=60,
            title="Renovacao mensal — confirmacao",
            description="Confirmar renovacao ou entender motivo de saida caso o plano nao tenha sido renovado.",
            suggested_message=(
                "Oi, {name}! Seu plano mensal venceu hoje. "
                "Posso ja renovar para voce? Ou prefere conversar sobre alguma outra opcao?"
            ),
            priority=TaskPriority.HIGH,
        ),
    ],
    "semestral": [
        PlaybookStep(
            days=60,
            title="Follow-up 60 dias — check de evolucao",
            description="Verificar evolucao, ajustar treino se necessario e reforcar compromisso com os resultados.",
            suggested_message=(
                "Ola, {name}! Ja sao 2 meses de treino — parabens pela dedicacao! "
                "Como esta se sentindo? Vamos revisar suas metas juntos?"
            ),
            priority=TaskPriority.MEDIUM,
        ),
        PlaybookStep(
            days=90,
            title="Follow-up 90 dias — avaliacao de resultados",
            description="Agendar nova avaliacao fisica para mostrar evolucao dos 3 primeiros meses.",
            suggested_message=(
                "Oi, {name}! 3 meses de treino! "
                "Vamos agendar uma nova avaliacao fisica para medir sua evolucao? "
                "Tenho certeza que voce vai se surpreender!"
            ),
            priority=TaskPriority.MEDIUM,
        ),
        PlaybookStep(
            days=120,
            title="Follow-up 120 dias — engajamento",
            description="Reforcar engajamento, verificar frequencia e oferecer novidades ou servicos adicionais.",
            suggested_message=(
                "Oi, {name}! Voce esta indo muito bem! "
                "Tem alguma modalidade nova ou servico que gostaria de experimentar? "
                "Pode me contar!"
            ),
            priority=TaskPriority.LOW,
        ),
        PlaybookStep(
            days=150,
            title="Alerta de renovacao semestral — 30 dias antes",
            description="Contato antecipado para garantir renovacao e oferecer condicoes especiais.",
            suggested_message=(
                "Ola, {name}! Falta um mes para o seu semestral vencer. "
                "Que tal ja garantirmos a renovacao? Temos condicoes especiais para alunos fieis como voce!"
            ),
            priority=TaskPriority.HIGH,
        ),
        PlaybookStep(
            days=180,
            title="Renovacao semestral — confirmacao",
            description="Confirmar renovacao semestral ou iniciar plano de retencao caso necessario.",
            suggested_message=(
                "Oi, {name}! Seu plano semestral esta chegando ao fim. "
                "Foi incrivel ter voce esses 6 meses! "
                "Vamos continuar essa jornada juntos? Posso ajudar com a renovacao agora mesmo."
            ),
            priority=TaskPriority.HIGH,
        ),
    ],
    "anual": [
        PlaybookStep(
            days=60,
            title="Follow-up 60 dias — check inicial",
            description="Verificar adaptacao, frequencia e satisfacao nos primeiros 2 meses.",
            suggested_message=(
                "Ola, {name}! 2 meses de treino — voce esta arrasando! "
                "Como esta se sentindo? Tem alguma coisa que podemos melhorar para voce?"
            ),
            priority=TaskPriority.MEDIUM,
        ),
        PlaybookStep(
            days=90,
            title="Follow-up 90 dias — avaliacao trimestral",
            description="Agendar avaliacao fisica trimestral para medir e motivar com resultados concretos.",
            suggested_message=(
                "Oi, {name}! Ja sao 3 meses! "
                "Hora de medir sua evolucao com uma nova avaliacao fisica. "
                "Quando voce prefere agendar?"
            ),
            priority=TaskPriority.MEDIUM,
        ),
        PlaybookStep(
            days=180,
            title="Avaliacao de meio de ano",
            description="Check-in na metade do plano anual — resultados, metas, satisfacao geral.",
            suggested_message=(
                "Parabens, {name}! Metade do seu plano anual ja concluida! "
                "Vamos fazer um balanco dos seus resultados e ajustar as metas para o segundo semestre?"
            ),
            priority=TaskPriority.MEDIUM,
        ),
        PlaybookStep(
            days=270,
            title="Follow-up 9 meses — retencao preventiva",
            description="Contato estrategico a 3 meses do vencimento para garantir renovacao e reforcar valor.",
            suggested_message=(
                "Oi, {name}! 9 meses de dedicacao — isso e incrivel! "
                "Faltam 3 meses para o fim do seu plano anual. "
                "Ja pensou em renovar? Tenho uma condicao especial para voce!"
            ),
            priority=TaskPriority.HIGH,
        ),
        PlaybookStep(
            days=360,
            title="Renovacao anual — confirmacao",
            description="Confirmar renovacao anual com oferta personalizada e celebrar 1 ano de aluno.",
            suggested_message=(
                "Parabens, {name}! Um ano inteiro transformando sua vida! "
                "Foi uma honra ter voce conosco. "
                "Vamos celebrar com a renovacao? Preparamos uma condicao especial para voce!"
            ),
            priority=TaskPriority.HIGH,
        ),
    ],
}

_IMPORT_PLAYBOOK_GRACE_DAYS = 7
_IMPORT_PLAYBOOK_LOOKAHEAD_DAYS = 7


def create_onboarding_tasks_for_member(db: Session, member: object, *, commit: bool = True) -> None:
    existing_count = db.scalar(
        select(func.count(Task.id)).where(
            Task.member_id == member.id,  # type: ignore[attr-defined]
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "onboarding",
        )
    ) or 0
    if existing_count > 0:
        return

    base = datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)  # type: ignore[attr-defined]
    tasks = [
        Task(
            gym_id=member.gym_id,  # type: ignore[attr-defined]
            member_id=member.id,  # type: ignore[attr-defined]
            title=step.title,
            description=step.description,
            suggested_message=step.suggested_message,
            status=TaskStatus.TODO,
            priority=step.priority,
            kanban_column="todo",
            due_date=base + timedelta(days=step.days),
            extra_data={"source": "onboarding", "onboarding_phase": "initial", "day_offset": step.days},
        )
        for step in ONBOARDING_PLAYBOOK
    ]
    db.add_all(tasks)
    if commit:
        db.commit()
    else:
        db.flush()


def create_plan_followup_tasks_for_member(db: Session, member: object, *, commit: bool = True) -> None:
    plan_type = _detect_plan_type(member.plan_name)  # type: ignore[attr-defined]
    steps = PLAN_FOLLOWUP_PLAYBOOK.get(plan_type, [])
    if not steps:
        return

    existing_count = db.scalar(
        select(func.count(Task.id)).where(
            Task.member_id == member.id,  # type: ignore[attr-defined]
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "plan_followup",
        )
    ) or 0
    if existing_count > 0:
        return

    base = datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)  # type: ignore[attr-defined]
    tasks = [
        Task(
            gym_id=member.gym_id,  # type: ignore[attr-defined]
            member_id=member.id,  # type: ignore[attr-defined]
            title=step.title,
            description=step.description,
            suggested_message=step.suggested_message,
            status=TaskStatus.TODO,
            priority=step.priority,
            kanban_column="todo",
            due_date=base + timedelta(days=step.days),
            extra_data={"source": "plan_followup", "plan_type": plan_type, "day_offset": step.days},
        )
        for step in steps
    ]
    db.add_all(tasks)
    if commit:
        db.commit()
    else:
        db.flush()


def _select_import_playbook_step(
    steps: list[PlaybookStep],
    *,
    join_date: date,
    now: datetime,
    grace_days: int = _IMPORT_PLAYBOOK_GRACE_DAYS,
    lookahead_days: int = _IMPORT_PLAYBOOK_LOOKAHEAD_DAYS,
) -> PlaybookStep | None:
    days_since_join = max(0, (now.date() - join_date).days)

    due_candidates = [
        step
        for step in steps
        if step.days <= days_since_join and (days_since_join - step.days) <= grace_days
    ]
    if due_candidates:
        return due_candidates[-1]

    upcoming_candidates = [
        step
        for step in steps
        if step.days > days_since_join and (step.days - days_since_join) <= lookahead_days
    ]
    if upcoming_candidates:
        return upcoming_candidates[0]

    return None


def _create_playbook_task(
    db: Session,
    *,
    member: object,
    step: PlaybookStep,
    extra_data: dict,
) -> None:
    base = datetime.combine(member.join_date, time.min, tzinfo=timezone.utc)  # type: ignore[attr-defined]
    task = Task(
        gym_id=member.gym_id,  # type: ignore[attr-defined]
        member_id=member.id,  # type: ignore[attr-defined]
        title=step.title,
        description=step.description,
        suggested_message=step.suggested_message,
        status=TaskStatus.TODO,
        priority=step.priority,
        kanban_column="todo",
        due_date=base + timedelta(days=step.days),
        extra_data=extra_data,
    )
    db.add(task)


def create_import_playbook_tasks_for_member(
    db: Session,
    member: object,
    *,
    commit: bool = True,
    now: datetime | None = None,
) -> dict[str, int]:
    now = now or datetime.now(tz=timezone.utc)
    created = {"onboarding": 0, "plan_followup": 0}

    onboarding_existing = db.scalar(
        select(func.count(Task.id)).where(
            Task.member_id == member.id,  # type: ignore[attr-defined]
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "onboarding",
        )
    ) or 0
    if onboarding_existing == 0:
        onboarding_step = _select_import_playbook_step(ONBOARDING_PLAYBOOK, join_date=member.join_date, now=now)  # type: ignore[attr-defined]
        if onboarding_step is not None:
            _create_playbook_task(
                db,
                member=member,
                step=onboarding_step,
                extra_data={
                    "source": "onboarding",
                    "onboarding_phase": "initial",
                    "day_offset": onboarding_step.days,
                    "materialization": "import_next_action",
                },
            )
            created["onboarding"] = 1

    plan_type = _detect_plan_type(member.plan_name)  # type: ignore[attr-defined]
    plan_steps = PLAN_FOLLOWUP_PLAYBOOK.get(plan_type, [])
    plan_existing = db.scalar(
        select(func.count(Task.id)).where(
            Task.member_id == member.id,  # type: ignore[attr-defined]
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "plan_followup",
        )
    ) or 0
    if plan_existing == 0 and plan_steps:
        plan_step = _select_import_playbook_step(plan_steps, join_date=member.join_date, now=now)  # type: ignore[attr-defined]
        if plan_step is not None:
            _create_playbook_task(
                db,
                member=member,
                step=plan_step,
                extra_data={
                    "source": "plan_followup",
                    "plan_type": plan_type,
                    "day_offset": plan_step.days,
                    "materialization": "import_next_action",
                },
            )
            created["plan_followup"] = 1

    if commit and (created["onboarding"] or created["plan_followup"]):
        db.commit()
    elif created["onboarding"] or created["plan_followup"]:
        db.flush()

    return created
