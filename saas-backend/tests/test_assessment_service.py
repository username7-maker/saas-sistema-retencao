import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services import assessment_service


def test_calculate_bmi_returns_none_when_values_missing():
    assert assessment_service._calculate_bmi(None, Decimal("80")) is None
    assert assessment_service._calculate_bmi(Decimal("170"), None) is None


def test_calculate_bmi_returns_expected_value():
    bmi = assessment_service._calculate_bmi(Decimal("170"), Decimal("80"))
    assert bmi == Decimal("27.68")


def test_calculate_progress_pct_handles_missing_or_invalid_target():
    assert assessment_service._calculate_progress_pct(Decimal("10"), None) == 0
    assert assessment_service._calculate_progress_pct(Decimal("10"), Decimal("0")) == 0


def test_calculate_progress_pct_clamps_values():
    assert assessment_service._calculate_progress_pct(Decimal("150"), Decimal("100")) == 100
    assert assessment_service._calculate_progress_pct(Decimal("25"), Decimal("100")) == 25


def test_calculate_delta_for_numeric_series():
    assert assessment_service._calculate_delta([70.0, 68.5, 67.0]) == -3.0
    assert assessment_service._calculate_delta([60, 64, 70]) == 10


def test_calculate_delta_ignores_none_and_requires_two_values():
    assert assessment_service._calculate_delta([None, 10, None, 15]) == 5
    assert assessment_service._calculate_delta([None, 10, None]) is None


def test_normalize_datetime_with_none_returns_aware_datetime():
    result = assessment_service._normalize_datetime(None)
    assert isinstance(result, datetime)
    assert result.tzinfo is not None


def test_normalize_datetime_with_naive_value_sets_utc():
    naive = datetime(2026, 2, 17, 8, 30, 0)
    result = assessment_service._normalize_datetime(naive)
    assert result.tzinfo == timezone.utc
    assert result.hour == 8


def test_safe_delta_value_formats_sign_and_missing_cases():
    assert assessment_service._safe_delta_value(Decimal("70"), Decimal("68")) == "-2.00"
    assert assessment_service._safe_delta_value(Decimal("68"), Decimal("70")) == "+2.00"
    assert assessment_service._safe_delta_value(None, Decimal("70")) == "n/a"


@patch("app.services.assessment_service.invalidate_dashboard_cache")
def test_ensure_assessment_feedback_followup_task_creates_due_14_days_later(mock_cache):
    db = MagicMock()
    db.scalar.return_value = None
    member = SimpleNamespace(
        id=uuid.uuid4(),
        gym_id=uuid.uuid4(),
        full_name="Paulo Ricardo Doneles",
    )
    assessment = SimpleNamespace(
        id=uuid.uuid4(),
        assessment_number=2,
        assessment_date=datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc),
    )
    evaluator_id = uuid.uuid4()

    task = assessment_service._ensure_assessment_feedback_followup_task(
        db,
        member=member,
        assessment=assessment,
        evaluator_id=evaluator_id,
        commit=False,
    )

    assert task is not None
    assert task.assigned_to_user_id == evaluator_id
    assert task.due_date == assessment.assessment_date + timedelta(days=14)
    assert task.extra_data["source"] == "assessment_feedback_followup"
    assert task.extra_data["domain"] == "trainer"
    assert task.extra_data["assessment_id"] == str(assessment.id)
    assert "14 dias da sua avaliacao" in task.suggested_message
    db.add.assert_called_once_with(task)
    db.flush.assert_called_once()
    mock_cache.assert_called_once_with("tasks")


@patch("app.services.assessment_service.invalidate_dashboard_cache")
def test_ensure_assessment_feedback_followup_task_skips_duplicate(mock_cache):
    existing = SimpleNamespace(id=uuid.uuid4())
    db = MagicMock()
    db.scalar.return_value = existing
    member = SimpleNamespace(id=uuid.uuid4(), gym_id=uuid.uuid4(), full_name="Aluno Teste")
    assessment = SimpleNamespace(
        id=uuid.uuid4(),
        assessment_number=1,
        assessment_date=datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc),
    )

    result = assessment_service._ensure_assessment_feedback_followup_task(
        db,
        member=member,
        assessment=assessment,
        evaluator_id=uuid.uuid4(),
        commit=False,
    )

    assert result is existing
    db.add.assert_not_called()
    db.flush.assert_not_called()
    mock_cache.assert_not_called()


def test_post_assessment_task_specs_create_three_technical_steps():
    member = SimpleNamespace(
        id=uuid.uuid4(),
        gym_id=uuid.uuid4(),
        full_name="Carina Santos",
        preferred_shift="afternoon",
    )
    assessment = SimpleNamespace(
        id=uuid.uuid4(),
        assessment_number=3,
        assessment_date=datetime(2026, 5, 5, 9, 0, tzinfo=timezone.utc),
        next_assessment_due=date(2026, 8, 3),
    )

    specs = assessment_service._post_assessment_task_specs(member, assessment)

    assert [item["source"] for item in specs] == [
        "assessment_training_delivery_check_d8",
        "assessment_feedback_followup",
        "assessment_reassessment_due",
    ]
    assert specs[0]["due_date"] == assessment.assessment_date + timedelta(days=8)
    assert specs[1]["due_date"] == assessment.assessment_date + timedelta(days=14)
    assert specs[2]["due_date"].date() == assessment.next_assessment_due
    assert specs[0]["extra_data"]["work_queue_visible_from"] == specs[0]["due_date"].isoformat()
    assert specs[2]["extra_data"]["technical_ladder_step"] == "reassessment_due"
    assert specs[2]["extra_data"]["preferred_shift"] == "afternoon"


def test_body_composition_task_specs_mark_source_and_default_reassessment_due():
    member = SimpleNamespace(
        id=uuid.uuid4(),
        gym_id=uuid.uuid4(),
        full_name="Marcela Frari",
        preferred_shift="evening",
    )
    body_source = SimpleNamespace(
        id=uuid.uuid4(),
        assessment_number=None,
        assessment_date=datetime(2026, 5, 6, 15, 0, tzinfo=timezone.utc),
        next_assessment_due=date(2026, 8, 4),
    )

    specs = assessment_service._post_assessment_task_specs(
        member,
        body_source,
        assessment_source_type="body_composition",
    )

    assert len(specs) == 3
    assert specs[0]["extra_data"]["assessment_source_type"] == "body_composition"
    assert specs[0]["extra_data"]["body_composition_evaluation_id"] == str(body_source.id)
    assert specs[0]["extra_data"]["assessment_sources"] == [
        {"type": "body_composition", "id": str(body_source.id), "body_composition_evaluation_id": str(body_source.id)}
    ]
    assert specs[2]["due_date"].date() == date(2026, 8, 4)


@patch("app.services.assessment_service.invalidate_dashboard_cache")
def test_ensure_post_assessment_ladder_tasks_creates_three_tasks(mock_cache, monkeypatch):
    db = MagicMock()
    db.scalar.return_value = None
    evaluator_id = uuid.uuid4()
    monkeypatch.setattr("app.services.assessment_service._supersede_open_post_assessment_tasks", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.assessment_service._resolve_post_assessment_owner", lambda *args, **kwargs: evaluator_id)
    member = SimpleNamespace(
        id=uuid.uuid4(),
        gym_id=uuid.uuid4(),
        full_name="Carina Santos",
        preferred_shift="morning",
    )
    assessment = SimpleNamespace(
        id=uuid.uuid4(),
        gym_id=member.gym_id,
        assessment_number=1,
        assessment_date=datetime(2026, 5, 5, 9, 0, tzinfo=timezone.utc),
        next_assessment_due=date(2026, 8, 3),
    )

    tasks = assessment_service._ensure_post_assessment_ladder_tasks(
        db,
        member=member,
        assessment=assessment,
        evaluator_id=evaluator_id,
        commit=False,
    )

    assert len(tasks) == 3
    assert {task.extra_data["source"] for task in tasks} == {
        "assessment_training_delivery_check_d8",
        "assessment_feedback_followup",
        "assessment_reassessment_due",
    }
    assert all(task.assigned_to_user_id == evaluator_id for task in tasks)
    assert all(task.extra_data["domain"] == "trainer" for task in tasks)
    assert all(task.extra_data["owner_role"] == "coach" for task in tasks)
    assert db.add.call_count == 3
    db.flush.assert_called_once()
    mock_cache.assert_called_once_with("tasks")


def test_user_covers_member_shift_uses_scope():
    member = SimpleNamespace(gym_id=uuid.uuid4(), preferred_shift="evening")
    trainer = SimpleNamespace(
        gym_id=member.gym_id,
        role=assessment_service.RoleEnum.TRAINER,
        is_active=True,
        work_shift="morning",
        work_shift_scope=["evening", "overnight"],
    )

    assert assessment_service._user_covers_member_shift(trainer, member) is True
