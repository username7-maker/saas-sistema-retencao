import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models import RoleEnum, TaskStatus
from app.schemas import TaskEventCreate
from app.services.task_event_service import create_task_event, record_task_event


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_GYM_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
TASK_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _user(role=RoleEnum.RECEPTIONIST):
    return SimpleNamespace(id=USER_ID, gym_id=GYM_ID, role=role)


def _task(**kwargs):
    defaults = dict(
        id=TASK_ID,
        gym_id=GYM_ID,
        member_id=None,
        lead_id=None,
        status=TaskStatus.TODO,
        kanban_column=TaskStatus.TODO.value,
        due_date=None,
        completed_at=None,
        extra_data={},
        deleted_at=None,
        member=None,
        lead=None,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_record_task_event_updates_operational_summary():
    db = MagicMock()
    task = _task()

    event = record_task_event(
        db,
        task=task,
        current_user=_user(),
        event_type="comment",
        note="Aluno pediu retorno sexta.",
        flush=False,
    )

    assert event.gym_id == GYM_ID
    assert event.task_id == TASK_ID
    assert event.event_type == "comment"
    assert task.extra_data["last_task_event"]["note"] == "Aluno pediu retorno sexta."
    db.add.assert_any_call(event)


def test_create_task_event_blocks_cross_tenant(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr("app.services.task_event_service.get_task_with_relations_or_404", lambda *_args, **_kwargs: _task(gym_id=OTHER_GYM_ID))

    with pytest.raises(HTTPException) as exc_info:
        create_task_event(
            db,
            task_id=TASK_ID,
            payload=TaskEventCreate(event_type="comment", note="Tentativa indevida."),
            current_user=_user(),
            commit=False,
        )

    assert exc_info.value.status_code == 404
