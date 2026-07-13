import os
import uuid
from collections.abc import Callable

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Gym, Member, RoleEnum, Task, TaskEvent, TaskPriority, TaskStatus, User, WorkQueueClaim
from app.schemas.work_queue import WorkQueueOutcomeInput
from app.services.work_queue_service import update_work_queue_outcome


DATABASE_URL = os.getenv("WORK_QUEUE_TEST_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="PostgreSQL concurrency harness requires WORK_QUEUE_TEST_DATABASE_URL or TEST_DATABASE_URL",
)


@pytest.fixture()
def postgres_session_factory():
    if not DATABASE_URL:
        pytest.skip("PostgreSQL concurrency harness requires WORK_QUEUE_TEST_DATABASE_URL or TEST_DATABASE_URL")
    schema = f"wq_concurrency_{uuid.uuid4().hex}"
    admin_engine = create_engine(DATABASE_URL, future=True)
    with admin_engine.begin() as connection:
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    engine = create_engine(
        DATABASE_URL,
        future=True,
        connect_args={"options": f"-csearch_path={schema},public"},
    )
    try:
        Base.metadata.create_all(engine)
        yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        admin_engine.dispose()


def _seed_subject(session_factory: Callable[[], Session]) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    session = session_factory()
    gym_id = uuid.uuid4()
    user_id = uuid.uuid4()
    member_id = uuid.uuid4()
    try:
        gym = Gym(id=gym_id, name="Gym Concurrency", slug=f"gym-{gym_id.hex[:12]}")
        user = User(
            id=user_id,
            gym_id=gym_id,
            full_name="Operador Concurrency",
            email=f"operator-{user_id.hex[:12]}@example.invalid",
            hashed_password="synthetic",
            role=RoleEnum.RECEPTIONIST,
        )
        member = Member(
            id=member_id,
            gym_id=gym_id,
            full_name="Aluno Concurrency",
            phone="11999999999",
        )
        session.add_all([gym, user, member])
        session.commit()
        return gym_id, user_id, member_id
    finally:
        session.close()


def test_postgres_active_work_dedupe_key_has_single_winner(postgres_session_factory):
    gym_id, _user_id, member_id = _seed_subject(postgres_session_factory)
    dedupe_key = f"{gym_id}:{member_id}:onboarding:member"
    session_a = postgres_session_factory()
    session_b = postgres_session_factory()
    try:
        assert session_a is not session_b
        session_a.add(
            Task(
                gym_id=gym_id,
                member_id=member_id,
                title="Criar tarefa canonica",
                description="Primeira task ativa",
                priority=TaskPriority.HIGH,
                status=TaskStatus.TODO,
                work_dedupe_key=dedupe_key,
                extra_data={"source": "ai_triage", "source_domain": "onboarding"},
            )
        )
        session_a.commit()

        session_b.add(
            Task(
                gym_id=gym_id,
                member_id=member_id,
                title="Criar tarefa duplicada",
                description="Segunda task ativa",
                priority=TaskPriority.HIGH,
                status=TaskStatus.TODO,
                work_dedupe_key=dedupe_key,
                extra_data={"source": "ai_triage", "source_domain": "onboarding"},
            )
        )
        with pytest.raises(IntegrityError):
            session_b.commit()
        session_b.rollback()

        session_b.add(
            Task(
                gym_id=gym_id,
                member_id=member_id,
                title="Historico encerrado permitido",
                description="Task done nao participa da unique ativa",
                priority=TaskPriority.HIGH,
                status=TaskStatus.DONE,
                work_dedupe_key=dedupe_key,
                extra_data={"source": "ai_triage", "source_domain": "onboarding"},
            )
        )
        session_b.commit()

        active_count = session_b.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.gym_id == gym_id, Task.work_dedupe_key == dedupe_key, Task.status.in_((TaskStatus.TODO, TaskStatus.DOING)))
        )
        assert active_count == 1
    finally:
        session_a.close()
        session_b.close()


def test_postgres_claim_outcome_has_one_winner_and_stale_409(postgres_session_factory):
    gym_id, user_id, member_id = _seed_subject(postgres_session_factory)
    seed_session = postgres_session_factory()
    task_id = uuid.uuid4()
    try:
        seed_session.add(
            Task(
                id=task_id,
                gym_id=gym_id,
                member_id=member_id,
                title="Registrar resultado",
                description="Task de concorrencia",
                priority=TaskPriority.HIGH,
                status=TaskStatus.DOING,
                kanban_column=TaskStatus.DOING.value,
                suggested_message="Mensagem sintetica",
                extra_data={"domain": "retention"},
            )
        )
        seed_session.commit()
    finally:
        seed_session.close()

    session_a = postgres_session_factory()
    session_b = postgres_session_factory()
    try:
        user_a = session_a.get(User, user_id)
        user_b = session_b.get(User, user_id)
        result = update_work_queue_outcome(
            session_a,
            current_user=user_a,
            source_type="task",
            source_id=task_id,
            payload=WorkQueueOutcomeInput(outcome="no_response", expected_version=1, contact_channel="call"),
        )
        session_a.commit()

        assert result.item.claim_version == 2
        with pytest.raises(HTTPException) as exc_info:
            update_work_queue_outcome(
                session_b,
                current_user=user_b,
                source_type="task",
                source_id=task_id,
                payload=WorkQueueOutcomeInput(outcome="no_response", expected_version=1, contact_channel="call"),
            )
        assert getattr(exc_info.value, "status_code", None) == 409
        session_b.rollback()

        verification = postgres_session_factory()
        try:
            claim = verification.scalar(
                select(WorkQueueClaim).where(
                    WorkQueueClaim.gym_id == gym_id,
                    WorkQueueClaim.source_type == "task",
                    WorkQueueClaim.source_id == task_id,
                )
            )
            event_count = verification.scalar(
                select(func.count())
                .select_from(TaskEvent)
                .where(TaskEvent.gym_id == gym_id, TaskEvent.task_id == task_id, TaskEvent.event_type == "outcome_recorded")
            )
            assert claim is not None
            assert claim.version == 2
            assert event_count == 1
        finally:
            verification.close()
    finally:
        session_a.close()
        session_b.close()
