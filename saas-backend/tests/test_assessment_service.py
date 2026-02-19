from datetime import datetime, timezone
from decimal import Decimal

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
