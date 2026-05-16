import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models import RoleEnum, TaskPriority, TaskStatus
from app.schemas.work_queue import WorkQueueExecuteInput, WorkQueueItemOut, WorkQueueOutcomeInput
from app.services.work_queue_service import (
    _filter_items,
    _matches_shift,
    execute_work_queue_item,
    list_work_queue_items,
    update_work_queue_outcome,
)


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
TASK_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
RECOMMENDATION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _user(role=RoleEnum.RECEPTIONIST):
    return SimpleNamespace(id=USER_ID, gym_id=GYM_ID, role=role, work_shift="morning", work_shift_scope=None)


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


def test_trainer_technical_outcome_training_delivered_marks_done(monkeypatch):
    task = _task(
        status=TaskStatus.DOING,
        kanban_column=TaskStatus.DOING.value,
        extra_data={
            "source": "assessment_training_delivery_check_d8",
            "domain": "trainer",
            "owner_role": "coach",
            "technical_ladder_step": "training_delivery_check_d8",
        },
    )
    db = MagicMock()
    db.scalar.return_value = task
    monkeypatch.setattr("app.services.work_queue_service.log_audit_event", lambda *args, **kwargs: None)

    result = update_work_queue_outcome(
        db,
        current_user=_user(role=RoleEnum.TRAINER),
        source_type="task",
        source_id=TASK_ID,
        payload=WorkQueueOutcomeInput(outcome="training_delivered", note="Treino confirmado"),
    )

    assert task.status == TaskStatus.DONE
    assert task.extra_data["work_queue_outcome"] == "training_delivered"
    assert result.item.technical_ladder_step == "training_delivery_check_d8"
    assert result.item.technical_ladder_step_label == "D+8 treino"


def test_trainer_technical_outcome_training_missing_keeps_open_for_tomorrow(monkeypatch):
    task = _task(
        status=TaskStatus.DOING,
        kanban_column=TaskStatus.DOING.value,
        extra_data={"source": "assessment_training_delivery_check_d8", "domain": "trainer", "owner_role": "coach"},
    )
    db = MagicMock()
    db.scalar.return_value = task
    monkeypatch.setattr("app.services.work_queue_service.log_audit_event", lambda *args, **kwargs: None)

    update_work_queue_outcome(
        db,
        current_user=_user(role=RoleEnum.TRAINER),
        source_type="task",
        source_id=TASK_ID,
        payload=WorkQueueOutcomeInput(outcome="training_missing", note="Treino nao entregue"),
    )

    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.HIGH
    assert task.due_date is not None
    assert task.extra_data["technical_followup_required"] is True


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


def test_matches_my_shift_for_user_scope_with_night_and_overnight():
    user = _user()
    user.work_shift = "evening"
    user.work_shift_scope = ["evening", "overnight"]
    overnight_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno madrugada",
        domain="trainer",
        severity="medium",
        preferred_shift="overnight",
        reason="Treina na madrugada",
        primary_action_label="Revisar treino",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )
    afternoon_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno tarde",
        domain="trainer",
        severity="medium",
        preferred_shift="afternoon",
        reason="Treina a tarde",
        primary_action_label="Revisar treino",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )

    assert _matches_shift(overnight_item, user, "my_shift") is True
    assert _matches_shift(afternoon_item, user, "my_shift") is False


def test_my_shift_without_configured_shift_does_not_match_all_turns():
    user = _user()
    user.work_shift = None
    user.work_shift_scope = None
    morning_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno manha",
        domain="trainer",
        severity="medium",
        preferred_shift="morning",
        reason="Treina de manha",
        primary_action_label="Revisar treino",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )
    unassigned_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno sem turno",
        domain="trainer",
        severity="medium",
        preferred_shift=None,
        reason="Sem turno definido",
        primary_action_label="Revisar treino",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )

    assert _matches_shift(morning_item, user, "my_shift") is False
    assert _matches_shift(unassigned_item, user, "my_shift") is True


def test_filter_hides_future_visible_from_in_do_now():
    user = _user()
    future_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno futuro",
        domain="trainer",
        severity="medium",
        preferred_shift="morning",
        reason="Reavaliacao futura",
        primary_action_label="Agendar reavaliacao",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        due_at=datetime.now(tz=timezone.utc) + timedelta(days=90),
        visible_from=datetime.now(tz=timezone.utc) + timedelta(days=83),
        context_path="/tasks",
        outcome_state="pending",
        technical_ladder_step="reassessment_due",
    )
    visible_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno visivel",
        domain="trainer",
        severity="medium",
        preferred_shift="morning",
        reason="Treino D+8",
        primary_action_label="Verificar treino",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        due_at=datetime.now(tz=timezone.utc),
        visible_from=datetime.now(tz=timezone.utc) - timedelta(minutes=1),
        context_path="/tasks",
        outcome_state="pending",
        technical_ladder_step="training_delivery_check_d8",
    )

    result = _filter_items(
        [future_item, visible_item],
        current_user=user,
        state="do_now",
        shift="my_shift",
        assignee="all",
        domain="trainer",
    )

    assert [item.subject_name for item in result] == ["Aluno visivel"]


def test_filter_hides_stale_backlog_from_do_now_but_not_all():
    user = _user()
    stale_retention = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno backlog",
        domain="retention",
        severity="high",
        preferred_shift="morning",
        reason="Retencao antiga sem resultado",
        primary_action_label="Contato ativo",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        due_at=datetime.now(tz=timezone.utc) - timedelta(days=16),
        context_path="/tasks",
        outcome_state="pending",
        retention_stage="reactivation",
        retention_stage_label="Reativacao",
    )
    current_onboarding = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno atual",
        domain="onboarding",
        severity="high",
        preferred_shift="morning",
        reason="Onboarding dentro da janela operacional",
        primary_action_label="Contato D7",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        due_at=datetime.now(tz=timezone.utc) - timedelta(days=2),
        context_path="/tasks",
        outcome_state="pending",
    )

    do_now = _filter_items(
        [stale_retention, current_onboarding],
        current_user=user,
        state="do_now",
        shift="my_shift",
        assignee="all",
        domain="all",
    )
    all_items = _filter_items(
        [stale_retention, current_onboarding],
        current_user=user,
        state="all",
        shift="my_shift",
        assignee="all",
        domain="all",
    )

    assert [item.subject_name for item in do_now] == ["Aluno atual"]
    assert {item.subject_name for item in all_items} == {"Aluno backlog", "Aluno atual"}


def test_filter_keeps_stale_trainer_and_finance_items_in_do_now():
    user = _user()
    old_due = datetime.now(tz=timezone.utc) - timedelta(days=30)
    trainer_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno treino",
        domain="trainer",
        severity="high",
        preferred_shift="morning",
        reason="Feedback tecnico atrasado",
        primary_action_label="Registrar feedback",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        due_at=old_due,
        context_path="/tasks",
        outcome_state="pending",
        technical_ladder_step="training_feedback_d14",
    )
    finance_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno financeiro",
        domain="finance",
        severity="high",
        preferred_shift="morning",
        reason="Pagamento pendente",
        primary_action_label="Regularizar pendencia",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        due_at=old_due,
        context_path="/tasks",
        outcome_state="pending",
    )

    result = _filter_items(
        [trainer_item, finance_item],
        current_user=user,
        state="do_now",
        shift="my_shift",
        assignee="all",
        domain="all",
    )

    assert {item.subject_name for item in result} == {"Aluno treino", "Aluno financeiro"}


def test_operations_domain_excludes_retention_items():
    user = _user()
    retention_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno em reativacao",
        domain="retention",
        severity="high",
        preferred_shift="morning",
        reason="30 dias sem check-in",
        primary_action_label="Agendar retorno guiado",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )
    onboarding_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno onboarding",
        domain="onboarding",
        severity="high",
        preferred_shift="morning",
        reason="Primeira avaliacao pendente",
        primary_action_label="Abrir avaliacao",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )

    result = _filter_items(
        [retention_item, onboarding_item],
        current_user=user,
        state="do_now",
        shift="my_shift",
        assignee="all",
        domain="operations",
    )

    assert [item.domain for item in result] == ["onboarding"]


def test_operations_domain_excludes_trainer_items():
    user = _user()
    trainer_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno com treino para revisar",
        domain="trainer",
        severity="high",
        preferred_shift="morning",
        reason="Feedback tecnico pendente",
        primary_action_label="Registrar feedback do treino",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )
    onboarding_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno onboarding",
        domain="onboarding",
        severity="high",
        preferred_shift="morning",
        reason="Primeira avaliacao pendente",
        primary_action_label="Abrir avaliacao",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )

    result = _filter_items(
        [trainer_item, onboarding_item],
        current_user=user,
        state="do_now",
        shift="my_shift",
        assignee="all",
        domain="operations",
    )

    assert [item.domain for item in result] == ["onboarding"]


def test_trainer_can_execute_feedback_followup_task(monkeypatch):
    task = _task(
        member_id=uuid.uuid4(),
        extra_data={"source": "assessment_feedback_followup", "domain": "trainer", "owner_role": "coach"},
        title="Follow-up D+14 da avaliacao - Ana",
    )
    db = MagicMock()
    db.scalar.return_value = task
    monkeypatch.setattr("app.services.work_queue_service.log_audit_event", lambda *args, **kwargs: None)

    result = execute_work_queue_item(
        db,
        current_user=_user(role=RoleEnum.TRAINER),
        source_type="task",
        source_id=TASK_ID,
        payload=WorkQueueExecuteInput(operator_note="Revisar treino"),
    )

    assert task.status == TaskStatus.DOING
    assert result.item.domain == "trainer"
    assert result.item.primary_action_label == "Registrar feedback"


def test_trainer_work_queue_excludes_first_assessment_queue_items(monkeypatch):
    member_id = uuid.uuid4()
    assessment_item = WorkQueueItemOut(
        source_type="assessment_queue",
        source_id=member_id,
        member_id=member_id,
        subject_name="Aluno sem avaliacao",
        domain="assessment",
        severity="high",
        preferred_shift="morning",
        reason="Primeira avaliacao pendente",
        primary_action_label="Agendar primeira avaliacao",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path=f"/assessments/members/{member_id}?tab=acoes",
        outcome_state="active",
    )
    monkeypatch.setattr("app.services.work_queue_service._list_task_items", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("app.services.work_queue_service._list_ai_items", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        "app.services.work_queue_service._list_assessment_queue_items",
        lambda *_args, **_kwargs: [assessment_item],
    )

    result = list_work_queue_items(
        MagicMock(),
        current_user=_user(role=RoleEnum.TRAINER),
        domain="trainer",
        shift="my_shift",
        state="do_now",
    )

    assert result.total == 0
    assert result.items == []


def test_assessment_queue_outcome_updates_queue_resolution(monkeypatch):
    member_id = uuid.uuid4()
    item = WorkQueueItemOut(
        source_type="assessment_queue",
        source_id=member_id,
        member_id=member_id,
        subject_name="Aluno sem avaliacao",
        domain="assessment",
        severity="high",
        preferred_shift="morning",
        reason="Primeira avaliacao pendente",
        primary_action_label="Agendar primeira avaliacao",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path=f"/assessments/members/{member_id}?tab=acoes",
        outcome_state="active",
    )
    update_resolution = MagicMock()
    monkeypatch.setattr("app.services.work_queue_service._member_assessment_queue_item", lambda *_args, **_kwargs: item)
    monkeypatch.setattr("app.services.work_queue_service.update_assessment_queue_resolution", update_resolution)
    monkeypatch.setattr("app.services.work_queue_service.log_audit_event", lambda *args, **kwargs: None)

    result = update_work_queue_outcome(
        MagicMock(),
        current_user=_user(role=RoleEnum.RECEPTIONIST),
        source_type="assessment_queue",
        source_id=member_id,
        payload=WorkQueueOutcomeInput(outcome="scheduled_assessment", note="Marcada para sexta"),
    )

    update_resolution.assert_called_once()
    assert update_resolution.call_args.kwargs["resolution_status"] == "scheduled"
    assert update_resolution.call_args.kwargs["gym_id"] == GYM_ID
    assert result.item.source_type == "assessment_queue"
    assert "removida da fila operacional" in result.detail


def test_retention_domain_returns_only_retention_items():
    user = _user()
    retention_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno em recuperacao",
        domain="retention",
        severity="high",
        preferred_shift="morning",
        reason="14 dias sem check-in",
        primary_action_label="Contato ativo",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )
    manual_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Task manual",
        domain="manual",
        severity="medium",
        preferred_shift="morning",
        reason="Rotina interna",
        primary_action_label="Iniciar tarefa",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )

    result = _filter_items(
        [retention_item, manual_item],
        current_user=user,
        state="do_now",
        shift="my_shift",
        assignee="all",
        domain="retention",
    )

    assert [item.domain for item in result] == ["retention"]


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
