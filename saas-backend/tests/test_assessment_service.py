import uuid
from datetime import datetime, timedelta, timezone
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
