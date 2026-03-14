"""Tests for onboarding_service."""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.onboarding_service import (
    _detect_plan_type,
    create_onboarding_tasks_for_member,
    create_plan_followup_tasks_for_member,
)

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


class TestDetectPlanType:
    def test_anual(self):
        assert _detect_plan_type("Plano Anual") == "anual"

    def test_semestral(self):
        assert _detect_plan_type("Semestral Premium") == "semestral"

    def test_mensal(self):
        assert _detect_plan_type("Plano Base") == "mensal"

    def test_none(self):
        assert _detect_plan_type(None) == "mensal"


class TestCreateOnboardingTasks:
    def test_creates_tasks(self):
        member = SimpleNamespace(
            id=MEMBER_ID, gym_id=GYM_ID,
            join_date=date(2026, 3, 1),
        )
        db = MagicMock()
        db.scalar.return_value = 0
        create_onboarding_tasks_for_member(db, member)
        db.add_all.assert_called_once()
        db.commit.assert_called_once()
        tasks = db.add_all.call_args[0][0]
        assert len(tasks) > 0


class TestCreatePlanFollowupTasks:
    def test_creates_for_mensal(self):
        member = SimpleNamespace(
            id=MEMBER_ID, gym_id=GYM_ID,
            join_date=date(2026, 3, 1),
            plan_name="Plano Mensal",
        )
        db = MagicMock()
        db.scalar.return_value = 0
        create_plan_followup_tasks_for_member(db, member)
        db.add_all.assert_called_once()

    def test_creates_for_anual(self):
        member = SimpleNamespace(
            id=MEMBER_ID, gym_id=GYM_ID,
            join_date=date(2026, 3, 1),
            plan_name="Anual Premium",
        )
        db = MagicMock()
        db.scalar.return_value = 0
        create_plan_followup_tasks_for_member(db, member)
        db.add_all.assert_called_once()
