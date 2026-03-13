"""Tests for assessment_service and assessment_benchmark_service helpers."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.assessment_service import (
    _calculate_bmi,
    _calculate_delta,
    _calculate_progress_pct,
    _decimal_to_float,
    _extract_main_lift_load,
    _last_month_labels,
    _normalize_datetime,
    _safe_delta_value,
    _subtract_months,
    _to_decimal,
    get_assessment,
    get_member_or_404,
    list_assessments,
)
from app.services.assessment_benchmark_service import (
    _cohort_score,
    _extract_goal_type,
    _percentile_rank,
    _position_label,
    _to_float,
)


# --- assessment_service helpers ---

class TestNormalizeDatetime:
    def test_none_returns_now(self):
        result = _normalize_datetime(None)
        assert result.tzinfo is not None

    def test_string(self):
        result = _normalize_datetime("2026-03-01T10:00:00")
        assert result.year == 2026
        assert result.tzinfo is not None

    def test_naive_datetime(self):
        dt = datetime(2026, 1, 1, 12, 0)
        result = _normalize_datetime(dt)
        assert result.tzinfo == timezone.utc

    def test_aware_datetime(self):
        dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = _normalize_datetime(dt)
        assert result == dt


class TestToDecimal:
    def test_none(self):
        assert _to_decimal(None) is None

    def test_float(self):
        assert _to_decimal(3.14) == Decimal("3.14")

    def test_int(self):
        assert _to_decimal(42) == Decimal("42")


class TestDecimalToFloat:
    def test_none(self):
        assert _decimal_to_float(None) is None

    def test_decimal(self):
        assert _decimal_to_float(Decimal("3.14")) == 3.14


class TestCalculateBmi:
    def test_valid(self):
        bmi = _calculate_bmi(Decimal("175"), Decimal("80"))
        assert bmi is not None
        assert float(bmi) == pytest.approx(26.12, abs=0.1)

    def test_none_height(self):
        assert _calculate_bmi(None, Decimal("80")) is None

    def test_zero_height(self):
        assert _calculate_bmi(Decimal("0"), Decimal("80")) is None


class TestCalculateProgressPct:
    def test_normal(self):
        assert _calculate_progress_pct(Decimal("75"), Decimal("100")) == 75

    def test_zero_target(self):
        assert _calculate_progress_pct(Decimal("50"), Decimal("0")) == 0

    def test_none_current(self):
        assert _calculate_progress_pct(None, Decimal("100")) == 0

    def test_capped_at_100(self):
        assert _calculate_progress_pct(Decimal("200"), Decimal("100")) == 100


class TestCalculateDelta:
    def test_with_values(self):
        assert _calculate_delta([1.0, 2.0, 3.0]) == 2.0

    def test_single_value(self):
        assert _calculate_delta([1.0]) is None

    def test_with_nones(self):
        assert _calculate_delta([None, 1.0, None, 3.0]) == 2.0

    def test_integers(self):
        assert _calculate_delta([10, 20]) == 10


class TestSafeDeltaValue:
    def test_with_values(self):
        assert _safe_delta_value(Decimal("80"), Decimal("85")) == "+5.00"

    def test_none(self):
        assert _safe_delta_value(None, Decimal("85")) == "n/a"


class TestLastMonthLabels:
    def test_generates(self):
        labels = _last_month_labels(3)
        assert len(labels) == 3

    def test_zero(self):
        assert _last_month_labels(0) == []


class TestSubtractMonthsAssessment:
    def test_same_year(self):
        from datetime import date
        assert _subtract_months(date(2026, 6, 1), 3) == date(2026, 3, 1)

    def test_cross_year(self):
        from datetime import date
        assert _subtract_months(date(2026, 2, 1), 3) == date(2025, 11, 1)


class TestExtractMainLiftLoad:
    def test_from_extra_data(self):
        a = SimpleNamespace(extra_data={"main_lift_load": 100}, strength_score=None)
        assert _extract_main_lift_load(a) == 100.0

    def test_from_strength_score(self):
        a = SimpleNamespace(extra_data={}, strength_score=80)
        assert _extract_main_lift_load(a) == 80.0

    def test_none(self):
        a = SimpleNamespace(extra_data={}, strength_score=None)
        assert _extract_main_lift_load(a) is None


class TestGetAssessment:
    def test_found(self):
        db = MagicMock()
        assessment = SimpleNamespace(id=uuid.uuid4())
        db.scalar.return_value = assessment
        result = get_assessment(db, assessment.id)
        assert result == assessment

    def test_not_found(self):
        db = MagicMock()
        db.scalar.return_value = None
        with pytest.raises(HTTPException):
            get_assessment(db, uuid.uuid4())


class TestGetMemberOr404Assessment:
    def test_not_found(self):
        db = MagicMock()
        db.scalar.return_value = None
        with pytest.raises(HTTPException):
            get_member_or_404(db, uuid.uuid4())


class TestListAssessments:
    def test_lists(self):
        member = SimpleNamespace(id=uuid.uuid4())
        db = MagicMock()
        db.scalar.return_value = member
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars
        result = list_assessments(db, member.id)
        assert result == []


# --- assessment_benchmark_service helpers ---

class TestCohortScore:
    def test_basic(self):
        a = SimpleNamespace(extra_data={}, strength_score=50, cardio_score=50)
        score = _cohort_score(a)
        assert 0 <= score <= 100

    def test_with_extra(self):
        a = SimpleNamespace(
            extra_data={"adherence_score": 80, "perceived_progress_score": 70},
            strength_score=60, cardio_score=55,
        )
        score = _cohort_score(a)
        assert score > 50


class TestPercentileRank:
    def test_empty(self):
        assert _percentile_rank(50, []) == 50

    def test_below_all(self):
        assert _percentile_rank(10, [20, 30, 40, 50]) == 0

    def test_above_all(self):
        assert _percentile_rank(100, [20, 30, 40, 50]) == 100


class TestPositionLabel:
    def test_below(self):
        assert "Abaixo" in _position_label(20)

    def test_on_track(self):
        assert "curva" in _position_label(50)

    def test_above(self):
        assert "Acima" in _position_label(80)


class TestExtractGoalType:
    def test_fat_loss(self):
        a = SimpleNamespace(extra_data={"goal_type": "emagrecimento"})
        assert _extract_goal_type(a) == "fat_loss"

    def test_muscle_gain(self):
        a = SimpleNamespace(extra_data={"goal_type": "hipertrofia"})
        assert _extract_goal_type(a) == "muscle_gain"

    def test_general(self):
        a = SimpleNamespace(extra_data={})
        assert _extract_goal_type(a) == "general"

    def test_performance(self):
        a = SimpleNamespace(extra_data={"goal_type": "performance"})
        assert _extract_goal_type(a) == "performance"


class TestToFloatBenchmark:
    def test_none(self):
        assert _to_float(None) is None

    def test_number(self):
        assert _to_float(3.14) == 3.14

    def test_invalid(self):
        assert _to_float("abc") is None
