import inspect
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models import AITriageRecommendation, RoleEnum, TaskPriority, TaskStatus
from app.schemas.work_queue import WorkQueueExecuteInput, WorkQueueItemOut, WorkQueueOutcomeInput
from app.services import work_queue_service
from app.services.work_queue_service import (
    _filter_items,
    _matches_shift,
    _task_to_item,
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
        assigned_user=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _autopilot_action(*, action_type: str, status: str, intent: str, member_id=None, **overrides):
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        gym_id=GYM_ID,
        member_id=member_id,
        lead_id=None,
        domain=intent,
        policy_key="synthetic-policy",
        action_type=action_type,
        status=status,
        message_body="Rascunho sintetico",
        outcome=None,
        metadata_json={
            "intent": intent,
            "sensitivity": "normal",
            "summary": "Resumo sintetico",
        },
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _assessment_row(index: int, *, queue_bucket: str, full_name: str | None = None):
    return SimpleNamespace(
        id=uuid.UUID(int=10_000 + index),
        full_name=full_name or f"Aluno avaliacao {index:03d}",
        preferred_shift="morning",
        risk_score=60,
        next_assessment_due=None,
        queue_bucket=queue_bucket,
        coverage_label="Cobertura sintetica",
        due_label="Pendencia sintetica",
        queue_resolution_status="active",
    )


def _scalars_result(values, *, unique: bool = False):
    result = MagicMock()
    result.all.return_value = list(values)
    if unique:
        result.unique.return_value = result
    return result


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


def test_task_to_item_includes_preferred_shift_diagnostic_when_unassigned():
    member_id = uuid.uuid4()
    member = SimpleNamespace(
        id=member_id,
        full_name="Aluno sem turno",
        phone=None,
        preferred_shift=None,
    )
    task = _task(member_id=member_id, member=member)

    item = _task_to_item(
        task,
        shift_diagnostics={
            member_id: {
                "status": "no_recent_checkins",
                "reason": "Sem check-in recente/importado nos ultimos 30 dias.",
                "counts": {"overnight": 0, "morning": 0, "afternoon": 0, "evening": 0},
                "lookback_days": 30,
            }
        },
    )

    assert item.preferred_shift is None
    assert item.preferred_shift_status == "no_recent_checkins"
    assert item.preferred_shift_reason == "Sem check-in recente/importado nos ultimos 30 dias."
    assert item.preferred_shift_counts["morning"] == 0


@pytest.mark.parametrize(
    ("relation_field", "id_field"),
    [
        ("member", "member_id"),
        ("lead", "lead_id"),
    ],
)
def test_wq_task_to_item_suppresses_unresolved_relationship_foreign_key_and_path(relation_field, id_field):
    unresolved_id = uuid.uuid4()
    task = _task(**{id_field: unresolved_id, relation_field: None})

    item = _task_to_item(task)

    assert item.subject_name == task.title
    assert item.member_id is None
    assert item.lead_id is None
    assert item.subject_phone is None
    assert item.context_path == "/tasks"
    assert str(unresolved_id) not in item.model_dump_json()


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


def test_filter_items_matches_execution_bucket():
    user = _user()
    d1_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno D1",
        domain="onboarding",
        severity="high",
        preferred_shift="morning",
        reason="Onboarding dia 1",
        primary_action_label="Conferir treino",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
        execution_bucket="onboarding_d1",
        execution_bucket_label="Dia 1",
    )
    d7_item = WorkQueueItemOut(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno D7",
        domain="onboarding",
        severity="high",
        preferred_shift="morning",
        reason="Onboarding dia 7",
        primary_action_label="Agendar avaliacao",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
        execution_bucket="onboarding_d7_plus",
        execution_bucket_label="Dia 7+",
    )

    filtered = _filter_items(
        [d1_item, d7_item],
        current_user=user,
        state="do_now",
        shift="my_shift",
        assignee="all",
        domain="onboarding",
        bucket="onboarding_d7_plus",
    )

    assert [item.source_id for item in filtered] == [d7_item.source_id]


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


def test_wq_reuse_ai_triage_execute_awaiting_outcome_validates_prepared_task_before_returning_id(monkeypatch):
    db = MagicMock()
    raw_task_id = uuid.uuid4()
    recommendation = SimpleNamespace(
        id=RECOMMENDATION_ID,
        gym_id=GYM_ID,
        source_domain="onboarding",
        source_entity_kind="member",
        source_entity_id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        lead_id=None,
        approval_state="approved",
        payload_snapshot={"metadata": {"prepared_task_id": str(raw_task_id)}},
    )
    item = WorkQueueItemOut(
        source_type="ai_triage",
        source_id=RECOMMENDATION_ID,
        subject_name="Aluno",
        domain="onboarding",
        severity="medium",
        reason="Ja preparado",
        primary_action_label="Criar tarefa",
        primary_action_type="create_task",
        requires_confirmation=False,
        state="awaiting_outcome",
        context_path="/ai/triage",
        outcome_state="pending",
    )
    resolve = MagicMock(return_value=None)
    prepare = MagicMock()
    monkeypatch.setattr("app.services.work_queue_service.get_ai_triage_recommendation_or_404", lambda *args, **kwargs: recommendation)
    monkeypatch.setattr("app.services.work_queue_service._ai_to_item", lambda _recommendation: item)
    monkeypatch.setattr("app.services.work_queue_service._resolve_work_queue_task_for_recommendation", resolve, raising=False)
    monkeypatch.setattr("app.services.work_queue_service.prepare_ai_triage_recommendation_action", prepare)

    result = execute_work_queue_item(
        db,
        current_user=_user(),
        source_type="ai_triage",
        source_id=RECOMMENDATION_ID,
        payload=WorkQueueExecuteInput(),
    )

    assert result.task_id is None
    assert result.context_path == "/ai/triage"
    assert str(raw_task_id) not in result.model_dump_json()
    resolve.assert_called_once()
    prepare.assert_not_called()


def _ai_recommendation(**overrides):
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    prepared_task_id = overrides.pop("prepared_task_id", None)
    metadata = overrides.pop("metadata", {"onboarding_score": 0, "days_since_join": 7})
    if prepared_task_id is not None:
        metadata = dict(metadata)
        metadata["prepared_task_id"] = str(prepared_task_id)
    defaults = dict(
        id=RECOMMENDATION_ID,
        gym_id=GYM_ID,
        source_domain="onboarding",
        source_entity_kind="member",
        source_entity_id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        lead_id=None,
        priority_score=55,
        is_active=True,
        suggestion_state="reviewed",
        approval_state="approved",
        execution_state="prepared" if prepared_task_id else "pending",
        outcome_state="pending",
        last_refreshed_at=now,
        payload_snapshot={
            "subject_name": "Aluno onboarding",
            "priority_bucket": "medium",
            "why_now_summary": "Onboarding exige acao coordenada.",
            "why_now_details": ["Dia 7 do onboarding."],
            "recommended_action": "Retomar tarefas da jornada inicial",
            "recommended_channel": "task",
            "recommended_owner": {"user_id": USER_ID, "role": "reception", "label": "Recepcao"},
            "suggested_message": "Revisar proximos checkpoints.",
            "expected_impact": "Reduzir dropout.",
            "metadata": metadata,
        },
    )
    defaults.update(overrides)
    return AITriageRecommendation(**defaults)


def test_wq_readiness_ai_triage_exposes_canonical_task_freshness_assignment_and_legacy_zero(monkeypatch):
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    canonical_task_id = uuid.uuid4()
    recommendation = _ai_recommendation(
        prepared_task_id=canonical_task_id,
        last_refreshed_at=now - timedelta(hours=24),
    )
    monkeypatch.setattr(work_queue_service, "_now", lambda: now)

    item = work_queue_service._ai_to_item(recommendation)

    assert item.canonical_task_id == canonical_task_id
    assert item.last_refreshed_at == now - timedelta(hours=24)
    assert item.freshness_state == "fresh"
    assert item.freshness_blocking is False
    assert item.assigned_to_user_id == USER_ID
    assert item.assigned_to_name == "Recepcao"
    assert item.assigned_to_role == "reception"
    assert item.signal_value == 0
    assert item.priority_state == "known"
    assert "signal" not in item.readiness_missing_fields
    assert "due_at" in item.readiness_missing_fields
    assert item.severity != "critical"


def test_wq_readiness_ai_triage_marks_stale_and_missing_signal_without_inventing_criticality(monkeypatch):
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    recommendation = _ai_recommendation(
        metadata={"days_since_join": 9},
        last_refreshed_at=now - timedelta(hours=24, seconds=1),
        payload_snapshot={
            "subject_name": "Aluno sem sinal",
            "priority_bucket": "medium",
            "why_now_summary": "Onboarding exige acao.",
            "why_now_details": [],
            "recommended_action": "Revisar onboarding",
            "recommended_channel": "task",
            "recommended_owner": {"user_id": None, "role": None, "label": None},
            "suggested_message": "Revisar contexto.",
            "expected_impact": "Evitar dropout.",
            "metadata": {"days_since_join": 9},
        },
    )
    monkeypatch.setattr(work_queue_service, "_now", lambda: now)

    item = work_queue_service._ai_to_item(recommendation)

    assert item.freshness_state == "stale"
    assert item.signal_value is None
    assert item.priority_state == "unknown"
    assert "signal" in item.readiness_missing_fields
    assert "assigned_to_name" in item.readiness_missing_fields
    assert "assigned_to_role" in item.readiness_missing_fields
    assert item.severity == "medium"


def test_wq_readiness_task_uses_updated_at_assignment_and_unknown_signal(monkeypatch):
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    assigned_user = SimpleNamespace(id=USER_ID, gym_id=GYM_ID, full_name="Dono Operacional", role=RoleEnum.MANAGER)
    task = _task(
        assigned_to_user_id=USER_ID,
        assigned_user=assigned_user,
        updated_at=now - timedelta(hours=25),
        due_date=None,
    )
    monkeypatch.setattr(work_queue_service, "_now", lambda: now)

    item = _task_to_item(task)

    assert item.canonical_task_id == TASK_ID
    assert item.last_refreshed_at == now - timedelta(hours=25)
    assert item.freshness_state == "stale"
    assert item.assigned_to_name == "Dono Operacional"
    assert item.assigned_to_role == "manager"
    assert item.signal_value is None
    assert item.priority_state == "unknown"
    assert "due_at" in item.readiness_missing_fields
    assert "signal" in item.readiness_missing_fields


def test_wq_readiness_task_loader_scopes_assigned_user_before_serialization(monkeypatch):
    db = MagicMock()
    db.scalars.return_value = _scalars_result([], unique=True)
    monkeypatch.setattr(work_queue_service, "preferred_shift_diagnostics_from_checkins", lambda *_args, **_kwargs: {})

    work_queue_service._list_task_items(db, _user(role=RoleEnum.OWNER))

    statement = db.scalars.call_args.args[0]
    sql = str(statement).casefold()
    params = statement.compile().params
    assert GYM_ID in params.values()
    assert "join users" in sql
    assert "users.gym_id" in sql


def _wq_item(index: int, **overrides) -> WorkQueueItemOut:
    defaults = dict(
        source_type="task",
        source_id=uuid.UUID(int=index + 1),
        subject_name=f"Aluno sintetico {index:03d}",
        domain="onboarding",
        severity="high",
        preferred_shift="morning",
        reason="Acompanhamento sintetico",
        primary_action_label="Abrir contexto",
        primary_action_type="open_context",
        requires_confirmation=False,
        state="do_now",
        context_path="/tasks",
        outcome_state="pending",
    )
    defaults.update(overrides)
    return WorkQueueItemOut(**defaults)


def _patch_wq_loaders_empty(monkeypatch) -> None:
    for loader_name in (
        "_list_task_items",
        "_list_ai_items",
        "_list_assessment_queue_items",
        "_list_ai_service_agent_items",
        "_list_student_personal_ai_items",
    ):
        monkeypatch.setattr(work_queue_service, loader_name, lambda *_args, **_kwargs: [])


def test_wq_dataset_188_reaches_page_two_without_repeating_page_one(monkeypatch):
    items = [_wq_item(index) for index in range(188)]
    monkeypatch.setattr(work_queue_service, "_list_task_items", lambda *_args, **_kwargs: items)

    first_page = list_work_queue_items(
        MagicMock(),
        current_user=_user(role=RoleEnum.OWNER),
        state="all",
        shift="all",
        source="task",
        page=1,
        page_size=25,
    )
    second_page = list_work_queue_items(
        MagicMock(),
        current_user=_user(role=RoleEnum.OWNER),
        state="all",
        shift="all",
        source="task",
        page=2,
        page_size=25,
    )

    assert first_page.total == 188
    assert second_page.total == 188
    assert [item.source_id for item in first_page.items] == [uuid.UUID(int=value) for value in range(1, 26)]
    assert [item.source_id for item in second_page.items] == [uuid.UUID(int=value) for value in range(26, 51)]
    assert not ({item.source_id for item in first_page.items} & {item.source_id for item in second_page.items})
    assert getattr(second_page, "truncated_sources", None) == []


@pytest.mark.parametrize(
    ("field", "query"),
    [
        ("subject_name", "aluna-agulha"),
        ("reason", "motivo-agulha"),
        ("primary_action_label", "acao-agulha"),
    ],
)
def test_wq_search_finds_item_after_first_25_before_pagination(monkeypatch, field, query):
    items = [_wq_item(index) for index in range(188)]
    target = items[150].model_copy(update={field: query})
    items[150] = target
    monkeypatch.setattr(work_queue_service, "_list_task_items", lambda *_args, **_kwargs: items)

    assert "q" in inspect.signature(list_work_queue_items).parameters
    result = list_work_queue_items(
        MagicMock(),
        current_user=_user(role=RoleEnum.OWNER),
        state="all",
        shift="all",
        source="task",
        q=f"  {query.upper()}  ",
        page=1,
        page_size=25,
    )

    assert result.total == 1
    assert [item.source_id for item in result.items] == [target.source_id]


def test_wq_state_counts_ignore_only_state_and_use_effective_eligibility(monkeypatch):
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    mine = USER_ID
    matching = dict(
        domain="retention",
        preferred_shift="morning",
        assigned_to_user_id=mine,
        execution_bucket="retention_attention",
        reason="motivo-agulha",
        retention_stage="attention",
    )
    items = [
        _wq_item(1, **matching),
        _wq_item(2, **{**matching, "visible_from": now + timedelta(minutes=1)}),
        _wq_item(3, **{**matching, "due_at": now - timedelta(days=30)}),
        _wq_item(4, **{**matching, "retention_stage": "cold_base"}),
        _wq_item(5, **{**matching, "state": "awaiting_outcome"}),
        _wq_item(6, **{**matching, "state": "done"}),
        _wq_item(7, **{**matching, "reason": "nao corresponde"}),
        _wq_item(8, **{**matching, "preferred_shift": "evening"}),
        _wq_item(9, **{**matching, "assigned_to_user_id": uuid.uuid4()}),
        _wq_item(10, **{**matching, "domain": "onboarding"}),
        _wq_item(11, **{**matching, "execution_bucket": "retention_reactivation"}),
    ]
    monkeypatch.setattr(work_queue_service, "_now", lambda: now)
    monkeypatch.setattr(work_queue_service, "_list_task_items", lambda *_args, **_kwargs: items)

    assert "q" in inspect.signature(list_work_queue_items).parameters
    result = list_work_queue_items(
        MagicMock(),
        current_user=_user(),
        state="done",
        shift="my_shift",
        assignee="mine",
        domain="retention",
        source="task",
        bucket="retention_attention",
        q="  MOTIVO-AGULHA  ",
    )

    assert result.state_counts == {"do_now": 1, "awaiting_outcome": 1, "done": 1}
    assert result.total == 1
    assert [item.source_id for item in result.items] == [uuid.UUID(int=7)]


@pytest.mark.parametrize(
    ("source", "loader_name", "cap"),
    [
        ("task", "_list_task_items", 300),
        ("ai_triage", "_list_ai_items", 200),
        ("assessment_queue", "_list_assessment_queue_items", 200),
        ("ai_service_agent", "_list_ai_service_agent_items", 100),
        ("student_personal_ai", "_list_student_personal_ai_items", 100),
    ],
)
def test_wq_cap_plus_one_marks_source_and_excludes_sentinel(monkeypatch, source, loader_name, cap):
    _patch_wq_loaders_empty(monkeypatch)
    items = [_wq_item(index, source_type=source) for index in range(cap + 1)]
    monkeypatch.setattr(work_queue_service, loader_name, lambda *_args, **_kwargs: items)

    result = list_work_queue_items(
        MagicMock(),
        current_user=_user(role=RoleEnum.OWNER),
        state="all",
        shift="all",
        source=source,
        page=1,
        page_size=100,
    )

    assert result.total == cap
    assert result.state_counts == {"do_now": cap, "awaiting_outcome": 0, "done": 0}
    assert result.truncated_sources == [source]
    assert uuid.UUID(int=cap + 1) not in {item.source_id for item in result.items}


def test_wq_explicit_assessment_source_runs_dedicated_loader(monkeypatch):
    _patch_wq_loaders_empty(monkeypatch)
    item = _wq_item(0, source_type="assessment_queue", domain="assessment")
    loader = MagicMock(return_value=[item])
    monkeypatch.setattr(work_queue_service, "_list_assessment_queue_items", loader)

    result = list_work_queue_items(
        MagicMock(),
        current_user=_user(role=RoleEnum.OWNER),
        state="all",
        shift="all",
        source="assessment_queue",
    )

    assert loader.call_count == 1
    assert result.total == 1
    assert [entry.source_id for entry in result.items] == [item.source_id]


@pytest.mark.parametrize(
    ("loader_name", "cap"),
    [
        ("_list_task_items", 300),
        ("_list_ai_items", 200),
        ("_list_ai_service_agent_items", 100),
        ("_list_student_personal_ai_items", 100),
    ],
)
def test_wq_persisted_loader_query_is_tenant_scoped_searchable_and_cap_plus_one(
    monkeypatch,
    loader_name,
    cap,
):
    loader = getattr(work_queue_service, loader_name)
    assert "q" in inspect.signature(loader).parameters
    scalar_result = MagicMock()
    scalar_result.unique.return_value = scalar_result
    scalar_result.all.return_value = []
    db = MagicMock()
    db.scalars.return_value = scalar_result
    monkeypatch.setattr(work_queue_service, "preferred_shift_diagnostics_from_checkins", lambda *_args, **_kwargs: {})

    loader(db, _user(role=RoleEnum.OWNER), q="  ALVO-SINTETICO  ")

    statement = db.scalars.call_args.args[0]
    params = statement.compile().params
    assert GYM_ID in params.values()
    assert getattr(statement._limit_clause, "value", None) == cap + 1
    assert any("alvo-sintetico" in str(value).casefold() for value in params.values())


def test_wq_assessment_loader_is_tenant_scoped_cap_plus_one_and_searches_post_cap(monkeypatch):
    loader = work_queue_service._list_assessment_queue_items
    assert "q" in inspect.signature(loader).parameters
    matching_id = uuid.UUID(int=700)
    queue_rows = [
        SimpleNamespace(
            id=matching_id,
            full_name="Aluna alvo sintetico",
            preferred_shift="morning",
            risk_score=50,
            next_assessment_due=None,
            queue_bucket="never",
            coverage_label="Nenhuma avaliacao registrada",
            due_label="Primeira avaliacao pendente",
            queue_resolution_status="active",
        ),
        SimpleNamespace(
            id=uuid.UUID(int=701),
            full_name="Aluno sem correspondencia",
            preferred_shift="morning",
            risk_score=50,
            next_assessment_due=None,
            queue_bucket="never",
            coverage_label="Nenhuma avaliacao registrada",
            due_label="Primeira avaliacao pendente",
            queue_resolution_status="active",
        ),
    ]
    get_queue = MagicMock(return_value=SimpleNamespace(items=queue_rows))
    monkeypatch.setattr(work_queue_service, "get_assessments_queue", get_queue)

    result = loader(MagicMock(), _user(role=RoleEnum.OWNER), q="  ALVO SINTETICO  ")

    assert get_queue.call_args.kwargs["gym_id"] == GYM_ID
    assert get_queue.call_args.kwargs["page_size"] == 201
    assert [item.source_id for item in result] == [matching_id]


def test_wq_legacy_snooze_is_visible_from_fallback_and_canonical_value_wins():
    legacy = datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc)
    canonical = legacy + timedelta(hours=2)

    legacy_item = _task_to_item(_task(extra_data={"work_queue_snoozed_until": legacy.isoformat()}))
    canonical_item = _task_to_item(
        _task(
            extra_data={
                "work_queue_visible_from": canonical.isoformat(),
                "work_queue_snoozed_until": legacy.isoformat(),
            }
        )
    )

    assert legacy_item.visible_from == legacy
    assert canonical_item.visible_from == canonical


def test_wq_visible_from_excludes_before_boundary_and_returns_at_exact_instant(monkeypatch):
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    future = _wq_item(800, visible_from=now + timedelta(microseconds=1))
    exact = _wq_item(801, visible_from=now)
    monkeypatch.setattr(work_queue_service, "_now", lambda: now)

    result = _filter_items(
        [future, exact],
        current_user=_user(role=RoleEnum.OWNER),
        state="do_now",
        shift="all",
        assignee="all",
        domain="all",
    )

    assert [item.source_id for item in result] == [exact.source_id]


def test_wq_equal_scores_sort_due_ascending_null_last_then_stable_source_key(monkeypatch):
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    earlier = now + timedelta(days=8)
    later = now + timedelta(days=9)
    items = [
        _wq_item(900, source_type="task", due_at=None),
        _wq_item(902, source_type="task", due_at=later),
        _wq_item(901, source_type="ai_triage", due_at=later),
        _wq_item(899, source_type="task", due_at=earlier),
    ]
    monkeypatch.setattr(work_queue_service, "_now", lambda: now)
    scores = [work_queue_service._work_item_score(item, now)[0] for item in items]
    assert len(set(scores)) == 1

    result = _filter_items(
        items,
        current_user=_user(role=RoleEnum.OWNER),
        state="all",
        shift="all",
        assignee="all",
        domain="all",
    )

    assert [(item.source_type, item.source_id) for item in result] == [
        ("task", uuid.UUID(int=900)),
        ("ai_triage", uuid.UUID(int=902)),
        ("task", uuid.UUID(int=903)),
        ("task", uuid.UUID(int=901)),
    ]


def test_wq_snooze_outcome_writes_canonical_and_legacy_visibility(monkeypatch):
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    visible_from = now + timedelta(days=1)
    task = _task(status=TaskStatus.DOING, kanban_column=TaskStatus.DOING.value)
    db = MagicMock()
    db.scalar.return_value = task
    monkeypatch.setattr(work_queue_service, "_now", lambda: now)
    monkeypatch.setattr(work_queue_service, "log_audit_event", lambda *args, **kwargs: None)

    result = update_work_queue_outcome(
        db,
        current_user=_user(),
        source_type="task",
        source_id=TASK_ID,
        payload=WorkQueueOutcomeInput(
            outcome="no_response",
            scheduled_for=visible_from,
            snooze_preset="custom",
        ),
    )

    assert task.extra_data.get("work_queue_visible_from") == visible_from.isoformat()
    assert task.extra_data.get("work_queue_snoozed_until") == visible_from.isoformat()
    assert result.item.visible_from == visible_from
    assert task.due_date == visible_from


def test_wq_task_search_statement_contains_every_visible_derived_action_default(monkeypatch):
    db = MagicMock()
    db.scalars.return_value = _scalars_result([], unique=True)
    monkeypatch.setattr(work_queue_service, "preferred_shift_diagnostics_from_checkins", lambda *_args, **_kwargs: {})

    work_queue_service._list_task_items(db, _user(role=RoleEnum.OWNER), q="registrar resultado")

    statement = db.scalars.call_args.args[0]
    compiled = statement.compile()
    bound_values = {str(value) for value in compiled.params.values()}
    expected_visible_defaults = {
        "Verificar treino",
        "Registrar feedback",
        "Agendar reavaliacao",
        "Revisar treino do aluno",
        "Abrir contexto tecnico",
        "Executar etapa da jornada",
        "Cobrar inadimplencia",
        "Usar mensagem pronta",
        "Registrar resultado",
        "Abrir avaliacao",
        "Abrir lead",
        "Iniciar tarefa",
    }

    assert expected_visible_defaults <= bound_values
    assert "CASE" in str(statement).upper()
    sql = str(statement).casefold()
    assert sql.count("join members") == 1
    assert sql.count("join leads") == 1
    assert "members.gym_id" in sql
    assert "members.deleted_at" in sql
    assert "leads.gym_id" in sql
    assert "leads.deleted_at" in sql


def test_wq_individual_task_statement_scopes_task_and_serialized_relationships_to_tenant():
    db = MagicMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        work_queue_service.get_work_queue_item(
            db,
            current_user=_user(role=RoleEnum.OWNER),
            source_type="task",
            source_id=TASK_ID,
        )

    assert exc_info.value.status_code == 404
    statement = db.scalar.call_args.args[0]
    sql = str(statement).casefold()
    params = statement.compile().params
    assert GYM_ID in params.values()
    assert sql.count("join members") == 1
    assert sql.count("join leads") == 1
    assert "members.gym_id" in sql
    assert "members.deleted_at" in sql
    assert "leads.gym_id" in sql
    assert "leads.deleted_at" in sql


@pytest.mark.parametrize(
    ("loader_name", "visible_labels"),
    [
        (
            "_list_ai_service_agent_items",
            {"Preparar na Kommo", "Aguardando Kommo", "Assumir conversa", "Revisar conversa"},
        ),
        (
            "_list_student_personal_ai_items",
            {"Preparar resposta Kommo", "Aguardando Kommo", "Assumir conversa", "Revisar aluno"},
        ),
    ],
)
def test_wq_agent_search_statement_reaches_tenant_member_name_and_derived_status_labels(loader_name, visible_labels):
    db = MagicMock()
    db.scalars.return_value = _scalars_result([])

    getattr(work_queue_service, loader_name)(db, _user(role=RoleEnum.OWNER), q="nome visivel")

    statement = db.scalars.call_args.args[0]
    compiled = statement.compile()
    sql = str(statement).casefold()
    bound_values = {str(value) for value in compiled.params.values()}

    assert "members.full_name" in sql
    assert "members.gym_id" in sql
    assert "members.deleted_at" in sql
    assert visible_labels <= bound_values


@pytest.mark.parametrize(
    ("loader_name", "action_type", "draft_status", "intent"),
    [
        (
            "_list_ai_service_agent_items",
            work_queue_service.AI_SERVICE_AGENT_ACTION_TYPE,
            work_queue_service.AI_SERVICE_AGENT_DRAFT_READY,
            "sales",
        ),
        (
            "_list_student_personal_ai_items",
            work_queue_service.STUDENT_PERSONAL_AI_ACTION_TYPE,
            work_queue_service.STUDENT_PERSONAL_AI_DRAFT_READY,
            "routine_support",
        ),
    ],
)
def test_wq_agent_list_resolves_members_in_one_tenant_scoped_batch_without_db_get(
    loader_name,
    action_type,
    draft_status,
    intent,
):
    member_id = uuid.uuid4()
    action = _autopilot_action(
        action_type=action_type,
        status=draft_status,
        intent=intent,
        member_id=member_id,
    )
    member = SimpleNamespace(
        id=member_id,
        gym_id=GYM_ID,
        full_name="Nome resolvido no tenant",
        phone="5511999999999",
        preferred_shift="morning",
        deleted_at=None,
    )
    db = MagicMock()
    db.scalars.side_effect = [_scalars_result([action]), _scalars_result([member])]
    db.get.return_value = member

    result = getattr(work_queue_service, loader_name)(db, _user(role=RoleEnum.OWNER))

    assert [item.subject_name for item in result] == ["Nome resolvido no tenant"]
    assert [item.member_id for item in result] == [member_id]
    assert db.scalars.call_count == 2
    db.get.assert_not_called()
    member_statement = db.scalars.call_args_list[1].args[0]
    member_sql = str(member_statement).casefold()
    member_params = member_statement.compile().params
    assert GYM_ID in member_params.values()
    assert "members.deleted_at" in member_sql


@pytest.mark.parametrize(
    ("mapper_name", "action_type", "draft_status", "intent", "fallback_name"),
    [
        (
            "_ai_service_agent_to_item",
            work_queue_service.AI_SERVICE_AGENT_ACTION_TYPE,
            work_queue_service.AI_SERVICE_AGENT_DRAFT_READY,
            "sales",
            "Conversa Kommo",
        ),
        (
            "_student_personal_ai_to_item",
            work_queue_service.STUDENT_PERSONAL_AI_ACTION_TYPE,
            work_queue_service.STUDENT_PERSONAL_AI_DRAFT_READY,
            "routine_support",
            "Aluno Kommo",
        ),
    ],
)
def test_wq_agent_individual_member_lookup_is_id_gym_deleted_scoped_and_never_leaks_cross_tenant_pii(
    mapper_name,
    action_type,
    draft_status,
    intent,
    fallback_name,
):
    member_id = uuid.uuid4()
    action = _autopilot_action(
        action_type=action_type,
        status=draft_status,
        intent=intent,
        member_id=member_id,
    )
    foreign_member = SimpleNamespace(
        id=member_id,
        gym_id=uuid.uuid4(),
        full_name="PII DE OUTRO TENANT",
        phone="5511888888888",
        preferred_shift="evening",
        deleted_at=None,
    )
    db = MagicMock()
    db.scalar.return_value = None
    db.get.return_value = foreign_member

    item = getattr(work_queue_service, mapper_name)(db, action)

    assert item.subject_name == fallback_name
    assert item.subject_phone is None
    assert item.member_id is None
    assert item.lead_id is None
    assert str(member_id) not in item.context_path
    db.get.assert_not_called()
    statement = db.scalar.call_args.args[0]
    sql = str(statement).casefold()
    params = statement.compile().params
    assert member_id in params.values()
    assert GYM_ID in params.values()
    assert "members.deleted_at" in sql


@pytest.mark.parametrize(
    ("role", "allowed_intents"),
    [
        (RoleEnum.TRAINER, {"assessment", "injury"}),
        (RoleEnum.SALESPERSON, {"sales"}),
    ],
)
def test_wq_ai_service_agent_rbac_intent_predicate_is_in_sql_before_source_cap(role, allowed_intents):
    db = MagicMock()
    db.scalars.return_value = _scalars_result([])

    work_queue_service._list_ai_service_agent_items(db, _user(role=role))

    statement = db.scalars.call_args.args[0]
    sql = str(statement)
    values = {str(value) for value in statement.compile().params.values()}
    assert allowed_intents <= values
    assert "metadata_json" in sql
    assert sql.upper().index("WHERE") < sql.upper().index("LIMIT")
    assert getattr(statement._limit_clause, "value", None) == (
        work_queue_service.WORK_QUEUE_SOURCE_CAPS["ai_service_agent"] + 1
    )


def test_wq_assessment_trainer_buckets_prevent_unauthorized_first_assessments_from_starving_week_work(monkeypatch):
    never_rows = [_assessment_row(index, queue_bucket="never") for index in range(201)]
    week_target = _assessment_row(999, queue_bucket="week", full_name="Aluna autorizada apos distribuicao adversarial")
    requested_buckets: list[str] = []

    def fake_queue(_db, *, page, page_size, bucket, gym_id, **_kwargs):
        assert gym_id == GYM_ID
        assert page_size == 201
        requested_buckets.append(bucket)
        if bucket == "all":
            return SimpleNamespace(items=never_rows, total=len(never_rows), page=page, page_size=page_size)
        if bucket == "week":
            return SimpleNamespace(items=[week_target], total=1, page=page, page_size=page_size)
        return SimpleNamespace(items=[], total=0, page=page, page_size=page_size)

    monkeypatch.setattr(work_queue_service, "get_assessments_queue", fake_queue)

    result = work_queue_service._list_assessment_queue_items(
        MagicMock(),
        _user(role=RoleEnum.TRAINER),
    )

    assert requested_buckets == ["overdue", "week", "upcoming", "covered"]
    assert [item.source_id for item in result] == [week_target.id]


def test_wq_assessment_trainer_bucket_plan_keeps_covered_operational_followups(monkeypatch):
    covered_target = _assessment_row(
        888,
        queue_bucket="covered",
        full_name="Aluna coberta aguardando acompanhamento tecnico",
    )
    requested_buckets: list[str] = []

    def fake_queue(_db, *, page, page_size, bucket, gym_id, **_kwargs):
        assert gym_id == GYM_ID
        assert page == 1
        assert page_size == 201
        requested_buckets.append(bucket)
        if bucket == "covered":
            return SimpleNamespace(items=[covered_target], total=1, page=page, page_size=page_size)
        return SimpleNamespace(items=[], total=0, page=page, page_size=page_size)

    monkeypatch.setattr(work_queue_service, "get_assessments_queue", fake_queue)

    result = work_queue_service._list_assessment_queue_items(
        MagicMock(),
        _user(role=RoleEnum.TRAINER),
    )

    assert requested_buckets == ["overdue", "week", "upcoming", "covered"]
    assert [item.source_id for item in result] == [covered_target.id]
    assert result[0].domain == "trainer"


def test_wq_assessment_receptionist_queries_only_never_bucket_before_cap(monkeypatch):
    requested_buckets: list[str] = []

    def fake_queue(_db, *, page, page_size, bucket, gym_id, **_kwargs):
        requested_buckets.append(bucket)
        row = _assessment_row(1, queue_bucket="never")
        return SimpleNamespace(items=[row], total=1, page=page, page_size=page_size)

    monkeypatch.setattr(work_queue_service, "get_assessments_queue", fake_queue)

    result = work_queue_service._list_assessment_queue_items(
        MagicMock(),
        _user(role=RoleEnum.RECEPTIONIST),
    )

    assert requested_buckets == ["never"]
    assert len(result) == 1
    assert result[0].domain == "assessment"


def test_wq_assessment_owner_trainer_domain_is_bucketed_before_cap(monkeypatch):
    never_rows = [_assessment_row(index, queue_bucket="never") for index in range(201)]
    trainer_target = _assessment_row(
        777,
        queue_bucket="week",
        full_name="Aluna trainer depois do cap adversarial",
    )
    requested_buckets: list[str] = []

    def fake_queue(_db, *, page, page_size, bucket, gym_id, **_kwargs):
        requested_buckets.append(bucket)
        if bucket == "all":
            return SimpleNamespace(
                items=never_rows,
                total=len(never_rows),
                page=page,
                page_size=page_size,
            )
        if bucket == "week":
            return SimpleNamespace(
                items=[trainer_target],
                total=1,
                page=page,
                page_size=page_size,
            )
        return SimpleNamespace(items=[], total=0, page=page, page_size=page_size)

    monkeypatch.setattr(work_queue_service, "get_assessments_queue", fake_queue)

    result = list_work_queue_items(
        MagicMock(),
        current_user=_user(role=RoleEnum.OWNER),
        state="all",
        shift="all",
        domain="trainer",
        source="assessment_queue",
    )

    assert requested_buckets == ["overdue", "week", "upcoming", "covered"]
    assert [item.source_id for item in result.items] == [trainer_target.id]


def test_wq_assessment_exclusions_apply_before_global_cap_and_do_not_create_false_truncation(monkeypatch):
    monkeypatch.setitem(work_queue_service.WORK_QUEUE_SOURCE_CAPS, "assessment_queue", 2)
    excluded = _assessment_row(1, queue_bucket="never")
    first = _assessment_row(2, queue_bucket="overdue")
    second = _assessment_row(3, queue_bucket="week")

    def fake_queue(_db, *, page, page_size, bucket, gym_id, **_kwargs):
        assert bucket == "all"
        assert page == 1
        assert page_size == 3
        return SimpleNamespace(items=[excluded, first, second], total=3, page=page, page_size=page_size)

    monkeypatch.setattr(work_queue_service, "get_assessments_queue", fake_queue)

    result = work_queue_service._list_assessment_queue_items(
        MagicMock(),
        _user(role=RoleEnum.OWNER),
        exclude_member_ids={excluded.id},
    )

    assert [item.source_id for item in result] == [first.id, second.id]
    assert result.truncated is False


def test_wq_sql_search_escapes_percent_and_underscore_as_literal_characters(monkeypatch):
    db = MagicMock()
    db.scalars.return_value = _scalars_result([], unique=True)
    monkeypatch.setattr(work_queue_service, "preferred_shift_diagnostics_from_checkins", lambda *_args, **_kwargs: {})

    work_queue_service._list_task_items(db, _user(role=RoleEnum.OWNER), q="100%_fit")

    statement = db.scalars.call_args.args[0]
    compiled = statement.compile()
    values = {str(value) for value in compiled.params.values()}
    assert "100/%/_fit" in values
    assert "ESCAPE" in str(statement).upper()
