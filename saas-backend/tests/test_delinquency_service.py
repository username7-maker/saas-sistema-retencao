import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models import MemberStatus, TaskPriority, TaskStatus
from app.services.delinquency_service import materialize_delinquency_tasks_for_gym


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
ENTRY_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
TASK_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _member():
    return SimpleNamespace(
        id=MEMBER_ID,
        gym_id=GYM_ID,
        full_name="Aluno Inadimplente",
        phone="11999999999",
        email="aluno@teste.com",
        plan_name="Livre Mensal",
        preferred_shift="morning",
        status=MemberStatus.ACTIVE,
        deleted_at=None,
    )


def _entry(days_overdue=8, amount=Decimal("149.90")):
    member = _member()
    return SimpleNamespace(
        id=ENTRY_ID,
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        member=member,
        due_date=date.today() - timedelta(days=days_overdue),
        amount=amount,
        status="overdue",
    )


def _open_task():
    return SimpleNamespace(
        id=TASK_ID,
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        lead_id=None,
        title="Inadimplencia D+3 - Aluno Inadimplente",
        description=None,
        priority=TaskPriority.HIGH,
        status=TaskStatus.TODO,
        kanban_column=TaskStatus.TODO.value,
        due_date=None,
        completed_at=None,
        suggested_message=None,
        extra_data={"source": "delinquency", "domain": "finance", "delinquency_stage": "d3", "overdue_amount": 99.9},
    )


def test_materialize_delinquency_creates_one_task(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.delinquency_service._active_overdue_entries",
        lambda *_args, **_kwargs: ([_entry()], 0),
    )
    monkeypatch.setattr("app.services.delinquency_service._open_delinquency_task", lambda *_args, **_kwargs: None)

    result = materialize_delinquency_tasks_for_gym(db, gym_id=GYM_ID, commit=False)

    assert result.created_count == 1
    assert result.updated_count == 0
    created_tasks = [call.args[0] for call in db.add.call_args_list if getattr(call.args[0], "member_id", None) == MEMBER_ID]
    assert created_tasks
    task = created_tasks[0]
    assert task.extra_data["source"] == "delinquency"
    assert task.extra_data["domain"] == "finance"
    assert task.extra_data["delinquency_stage"] == "d7"
    assert task.priority == TaskPriority.HIGH


def test_materialize_delinquency_updates_open_task_without_duplicate(monkeypatch):
    db = MagicMock()
    existing = _open_task()
    monkeypatch.setattr(
        "app.services.delinquency_service._active_overdue_entries",
        lambda *_args, **_kwargs: ([_entry(days_overdue=18, amount=Decimal("199.90"))], 0),
    )
    monkeypatch.setattr("app.services.delinquency_service._open_delinquency_task", lambda *_args, **_kwargs: existing)

    result = materialize_delinquency_tasks_for_gym(db, gym_id=GYM_ID, commit=False)

    assert result.created_count == 0
    assert result.updated_count == 1
    assert existing.extra_data["delinquency_stage"] == "d15"
    assert existing.extra_data["overdue_amount"] == 199.9
    assert existing.priority == TaskPriority.URGENT
    stage_events = [call.args[0] for call in db.add.call_args_list if getattr(call.args[0], "event_type", None) == "delinquency_stage_updated"]
    assert stage_events
