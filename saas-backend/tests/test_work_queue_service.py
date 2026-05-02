import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models import RoleEnum, TaskPriority, TaskStatus
from app.schemas.work_queue import WorkQueueExecuteInput, WorkQueueItemOut, WorkQueueOutcomeInput
from app.services.work_queue_service import _matches_shift, execute_work_queue_item, update_work_queue_outcome


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
TASK_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
RECOMMENDATION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _user(role=RoleEnum.RECEPTIONIST):
    return SimpleNamespace(id=USER_ID, gym_id=GYM_ID, role=role, work_shift="morning")


def _task(**kwargs):
    defaults = dict(
        id=TASK_ID,
        gym_id=GYM_ID,
        member_id=None,
        lead_id=None,
        assigned_to_user_id=None,
        title="Chamar aluno",
        description="Aluno precisa de contato.",
        priority=TaskPriority.HIGH,
        status=TaskStatus.TODO,
        kanban_column=TaskStatus.TODO.value,
        due_date=None,
        completed_at=None,
        suggested_message="Oi, tudo bem?",
        extra_data={},
        deleted_at=None,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
        member=None,
        lead=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_execute_task_moves_todo_to_doing_and_records_operator_note(monkeypatch):
    task = _task()
    db = MagicMock()
    db.scalar.return_value = task
    monkeypatch.setattr("app.services.work_queue_service.log_audit_event", lambda *args, **kwargs: None)

    result = execute_work_queue_item(
        db,
        current_user=_user(),
        source_type="task",
        source_id=TASK_ID,
        payload=WorkQueueExecuteInput(operator_note="Chamar agora"),
    )

    assert task.status == TaskStatus.DOING
    assert task.kanban_column == TaskStatus.DOING.value
    assert task.extra_data["work_queue_operator_note"] == "Chamar agora"
    assert result.item.state == "awaiting_outcome"
    assert result.prepared_message == "Oi, tudo bem?"
    created_events = [call.args[0] for call in db.add.call_args_list if getattr(call.args[0], "event_type", None) == "execution_started"]
    assert created_events
    assert created_events[0].note == "Chamar agora"
    db.flush.assert_called_once()


def test_task_outcome_completed_marks_done(monkeypatch):
    task = _task(status=TaskStatus.DOING, kanban_column=TaskStatus.DOING.value)
    db = MagicMock()
    db.scalar.return_value = task
    monkeypatch.setattr("app.services.work_queue_service.log_audit_event", lambda *args, **kwargs: None)

    result = update_work_queue_outcome(
        db,
        current_user=_user(),
        source_type="task",
        source_id=TASK_ID,
        payload=WorkQueueOutcomeInput(outcome="completed", note="Resolvido"),
    )

    assert task.status == TaskStatus.DONE
    assert task.completed_at is not None
    assert task.extra_data["work_queue_outcome"] == "completed"
    assert result.item.state == "done"


def test_task_outcome_no_response_snoozes_to_tomorrow(monkeypatch):
    task = _task(status=TaskStatus.DOING, kanban_column=TaskStatus.DOING.value)
    db = MagicMock()
    db.scalar.return_value = task
    monkeypatch.setattr("app.services.work_queue_service.log_audit_event", lambda *args, **kwargs: None)

    update_work_queue_outcome(
        db,
        current_user=_user(),
        source_type="task",
        source_id=TASK_ID,
        payload=WorkQueueOutcomeInput(outcome="no_response", note=None, snooze_preset="tomorrow", contact_channel="call"),
    )

    assert task.status == TaskStatus.TODO
    assert task.due_date is not None
    assert task.completed_at is None
    assert task.extra_data["work_queue_contact_channel"] == "call"
    created_events = [call.args[0] for call in db.add.call_args_list if getattr(call.args[0], "event_type", None) == "snoozed"]
    assert created_events
    assert created_events[0].outcome == "no_response"
    assert created_events[0].contact_channel == "call"


def test_finance_task_payment_confirmed_marks_done(monkeypatch):
    task = _task(
        status=TaskStatus.DOING,
        kanban_column=TaskStatus.DOING.value,
        extra_data={"source": "delinquency", "domain": "finance"},
    )
    db = MagicMock()
    db.scalar.return_value = task
    monkeypatch.setattr("app.services.work_queue_service.log_audit_event", lambda *args, **kwargs: None)

    result = update_work_queue_outcome(
        db,
        current_user=_user(),
        source_type="task",
        source_id=TASK_ID,
        payload=WorkQueueOutcomeInput(outcome="payment_confirmed", note="Pago na recepcao"),
    )

    assert task.status == TaskStatus.DONE
    assert task.completed_at is not None
    assert task.extra_data["work_queue_outcome"] == "payment_confirmed"
    assert result.item.domain == "finance"


def test_finance_task_payment_promised_snoozes_and_keeps_open(monkeypatch):
    task = _task(
        status=TaskStatus.DOING,
        kanban_column=TaskStatus.DOING.value,
        extra_data={"source": "delinquency", "domain": "finance"},
    )
    db = MagicMock()
    db.scalar.return_value = task
    monkeypatch.setattr("app.services.work_queue_service.log_audit_event", lambda *args, **kwargs: None)

    update_work_queue_outcome(
        db,
        current_user=_user(),
        source_type="task",
        source_id=TASK_ID,
        payload=WorkQueueOutcomeInput(outcome="payment_promised", snooze_preset="tomorrow", contact_channel="whatsapp"),
    )

    assert task.status == TaskStatus.TODO
    assert task.due_date is not None
    assert task.extra_data["owner_role"] == "reception"
    created_events = [call.args[0] for call in db.add.call_args_list if getattr(call.args[0], "event_type", None) == "snoozed"]
    assert created_events
    assert created_events[0].outcome == "payment_promised"


def test_matches_my_shift_for_overnight_user():
    user = _user()
    user.work_shift = "overnight"
    item = WorkQueueItemOut(
        source_type="task",
        source_id=TASK_ID,
        subject_name="Aluno madrugada",
        domain="retention",
        severity="high",
        preferred_shift="madrugada",
        reason="Padrao de check-in da madrugada",
        primary_action_label="Contato nao invasivo",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )

    assert _matches_shift(item, user, "my_shift") is True


def test_archived_task_cannot_execute(monkeypatch):
    task = _task(extra_data={"operational_archive": {"archived_at": "2026-04-29T00:00:00+00:00"}})
    db = MagicMock()
    db.scalar.return_value = task
    monkeypatch.setattr("app.services.work_queue_service.log_audit_event", lambda *args, **kwargs: None)

    with pytest.raises(HTTPException) as exc_info:
        execute_work_queue_item(
            db,
            current_user=_user(),
            source_type="task",
            source_id=TASK_ID,
            payload=WorkQueueExecuteInput(operator_note="Tentar"),
        )

    assert exc_info.value.status_code == 404


def test_ai_triage_execute_requires_confirmation_for_critical(monkeypatch):
    db = MagicMock()
    recommendation = SimpleNamespace(id=RECOMMENDATION_ID, approval_state="pending", payload_snapshot={}, gym_id=GYM_ID)
    item = WorkQueueItemOut(
        source_type="ai_triage",
        source_id=RECOMMENDATION_ID,
        subject_name="Aluno",
        domain="retention",
        severity="critical",
        reason="Risco alto",
        primary_action_label="Preparar WhatsApp",
        primary_action_type="prepare_outbound_message",
        requires_confirmation=True,
        state="do_now",
        context_path="/ai/triage",
        outcome_state="pending",
    )
    monkeypatch.setattr("app.services.work_queue_service.get_ai_triage_recommendation_or_404", lambda *args, **kwargs: recommendation)
    monkeypatch.setattr("app.services.work_queue_service._ai_to_item", lambda _recommendation: item)

    with pytest.raises(HTTPException) as exc_info:
        execute_work_queue_item(
            db,
            current_user=_user(),
            source_type="ai_triage",
            source_id=RECOMMENDATION_ID,
            payload=WorkQueueExecuteInput(confirm_approval=False),
        )

    assert exc_info.value.status_code == 409


def test_ai_triage_execute_does_not_duplicate_already_prepared(monkeypatch):
    db = MagicMock()
    recommendation = SimpleNamespace(
        id=RECOMMENDATION_ID,
        approval_state="approved",
        payload_snapshot={"metadata": {"prepared_task_id": str(TASK_ID)}},
        gym_id=GYM_ID,
    )
    item = WorkQueueItemOut(
        source_type="ai_triage",
        source_id=RECOMMENDATION_ID,
        subject_name="Aluno",
        domain="retention",
        severity="high",
        reason="Ja preparado",
        primary_action_label="Criar tarefa",
        primary_action_type="create_task",
        requires_confirmation=False,
        state="awaiting_outcome",
        context_path="/ai/triage",
        outcome_state="pending",
    )
    prepare = MagicMock()
    monkeypatch.setattr("app.services.work_queue_service.get_ai_triage_recommendation_or_404", lambda *args, **kwargs: recommendation)
    monkeypatch.setattr("app.services.work_queue_service._ai_to_item", lambda _recommendation: item)
    monkeypatch.setattr("app.services.work_queue_service.prepare_ai_triage_recommendation_action", prepare)

    result = execute_work_queue_item(
        db,
        current_user=_user(),
        source_type="ai_triage",
        source_id=RECOMMENDATION_ID,
        payload=WorkQueueExecuteInput(),
    )

    assert result.task_id == TASK_ID
    prepare.assert_not_called()
