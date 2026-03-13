"""
Test that next_assessment_due is calculated dynamically based on plan type.
"""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.assessment_service import _calculate_next_assessment_due

MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _make_db_with_member(plan_name):
    member = SimpleNamespace(id=MEMBER_ID, plan_name=plan_name)
    db = MagicMock()
    db.scalar.return_value = member
    return db


def test_mensal_plan_returns_30_days():
    db = _make_db_with_member("Plano Mensal")
    assessment_date = datetime.now(tz=timezone.utc)

    due = _calculate_next_assessment_due(db, MEMBER_ID, assessment_date)

    delta = (due - assessment_date.date()).days
    assert delta == 30


def test_trimestral_plan_returns_90_days():
    db = _make_db_with_member("Plano Trimestral")
    assessment_date = datetime.now(tz=timezone.utc)

    due = _calculate_next_assessment_due(db, MEMBER_ID, assessment_date)

    delta = (due - assessment_date.date()).days
    assert delta == 90


def test_anual_plan_returns_120_days():
    db = _make_db_with_member("Plano Anual Premium")
    assessment_date = datetime.now(tz=timezone.utc)

    due = _calculate_next_assessment_due(db, MEMBER_ID, assessment_date)

    delta = (due - assessment_date.date()).days
    assert delta == 120


def test_semestral_plan_returns_90_days():
    db = _make_db_with_member("Plano Semestral")
    assessment_date = datetime.now(tz=timezone.utc)

    due = _calculate_next_assessment_due(db, MEMBER_ID, assessment_date)

    delta = (due - assessment_date.date()).days
    assert delta == 90


def test_unknown_plan_defaults_to_90_days():
    db = _make_db_with_member("Plano Especial")
    assessment_date = datetime.now(tz=timezone.utc)

    due = _calculate_next_assessment_due(db, MEMBER_ID, assessment_date)

    delta = (due - assessment_date.date()).days
    assert delta == 90


def test_missing_member_defaults_to_90_days():
    db = MagicMock()
    db.scalar.return_value = None  # member not found
    assessment_date = datetime.now(tz=timezone.utc)

    due = _calculate_next_assessment_due(db, MEMBER_ID, assessment_date)

    delta = (due - assessment_date.date()).days
    assert delta == 90
