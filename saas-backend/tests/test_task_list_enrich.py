"""Tests for task_service list_tasks and _enrich."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models import TaskPriority, TaskStatus
from app.schemas import TaskOut


TASK_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _task_ns(**overrides):
    defaults = dict(
        id=TASK_ID, gym_id=GYM_ID, title="Task", description="desc",
        status=TaskStatus.TODO, kanban_column="todo",
        priority=TaskPriority.MEDIUM, completed_at=None, deleted_at=None,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
        due_date=None, suggested_message=None, extra_data={},
        member=None, lead=None, member_id=None, lead_id=None,
        assigned_to_user_id=None, source="MANUAL",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestEnrich:
    def test_no_relations(self):
        from app.services.task_service import _enrich
        task = _task_ns()
        result = _enrich(task)
        assert isinstance(result, TaskOut)
        assert result.member_name is None
        assert result.lead_name is None

    def test_with_member(self):
        from app.services.task_service import _enrich
        task = _task_ns(member=SimpleNamespace(full_name="Joao"))
        result = _enrich(task)
        assert result.member_name == "Joao"

    def test_with_lead(self):
        from app.services.task_service import _enrich
        task = _task_ns(lead=SimpleNamespace(full_name="Maria"))
        result = _enrich(task)
        assert result.lead_name == "Maria"


class TestListTasks:
    def test_lists_all(self):
        task = _task_ns()
        db = MagicMock()
        db.scalar.return_value = 1
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value = mock_scalars
        mock_scalars.all.return_value = [task]
        db.scalars.return_value = mock_scalars

        from app.services.task_service import list_tasks
        result = list_tasks(db)
        assert result.total == 1
        assert len(result.items) == 1

    def test_lists_with_status_filter(self):
        db = MagicMock()
        db.scalar.return_value = 0
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value = mock_scalars
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars

        from app.services.task_service import list_tasks
        result = list_tasks(db, status=TaskStatus.DONE)
        assert result.total == 0

    def test_lists_with_assigned_filter(self):
        user_id = uuid.uuid4()
        db = MagicMock()
        db.scalar.return_value = 0
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value = mock_scalars
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars

        from app.services.task_service import list_tasks
        result = list_tasks(db, assigned_to_user_id=user_id)
        assert result.total == 0

    def test_hides_retention_tasks_by_default(self):
        manual_task = _task_ns(id=uuid.uuid4(), title="Ligar para lead", extra_data={"source": "manual"})
        retention_task = _task_ns(id=uuid.uuid4(), title="Escalar churn - Ana", extra_data={"source": "retention_intelligence"})
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value = mock_scalars
        mock_scalars.all.return_value = [manual_task, retention_task]
        db.scalars.return_value = mock_scalars

        from app.services.task_service import list_tasks

        result = list_tasks(db)

        assert result.total == 1
        assert [item.title for item in result.items] == ["Ligar para lead"]

    def test_hides_legacy_retention_tasks_without_extra_data(self):
        manual_task = _task_ns(id=uuid.uuid4(), title="Confirmar visita guiada", description="Follow-up comercial", extra_data={})
        retention_task = _task_ns(
            id=uuid.uuid4(),
            title="Escalar churn - Ana",
            description="Aluno com 21+ dias sem treino. Acionar gerente responsavel.",
            extra_data={},
        )
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value = mock_scalars
        mock_scalars.all.return_value = [manual_task, retention_task]
        db.scalars.return_value = mock_scalars

        from app.services.task_service import list_tasks

        result = list_tasks(db)

        assert result.total == 1
        assert [item.title for item in result.items] == ["Confirmar visita guiada"]

    def test_can_include_retention_tasks_when_requested(self):
        manual_task = _task_ns(id=uuid.uuid4(), title="Ligar para lead", extra_data={"source": "manual"})
        retention_task = _task_ns(id=uuid.uuid4(), title="Escalar churn - Ana", extra_data={"source": "retention_intelligence"})
        db = MagicMock()
        db.scalar.return_value = 2
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value = mock_scalars
        mock_scalars.all.return_value = [manual_task, retention_task]
        db.scalars.return_value = mock_scalars

        from app.services.task_service import list_tasks

        result = list_tasks(db, include_retention=True)

        assert result.total == 2
        assert [item.title for item in result.items] == ["Ligar para lead", "Escalar churn - Ana"]
