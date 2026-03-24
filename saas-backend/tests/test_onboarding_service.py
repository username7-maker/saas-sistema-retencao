"""Tests for onboarding_service."""

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.onboarding_service import (
    _detect_plan_type,
    create_import_playbook_tasks_for_member,
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


class TestCreateImportPlaybookTasks:
    def test_creates_only_single_recent_onboarding_task_for_import(self):
        member = SimpleNamespace(
            id=MEMBER_ID,
            gym_id=GYM_ID,
            join_date=date(2026, 3, 4),
            plan_name="Plano Mensal",
        )
        db = MagicMock()
        db.scalar.side_effect = [0, 0]

        created = create_import_playbook_tasks_for_member(
            db,
            member,
            commit=False,
            now=datetime(2026, 3, 24, tzinfo=timezone.utc),
        )

        assert created == {"onboarding": 1, "plan_followup": 0}
        db.add.assert_called_once()
        task = db.add.call_args.args[0]
        assert task.title == "Revisao tecnica de execucao"
        assert task.extra_data["materialization"] == "import_next_action"
        db.flush.assert_called_once()

    def test_skips_import_playbook_when_next_action_is_too_far(self):
        member = SimpleNamespace(
            id=MEMBER_ID,
            gym_id=GYM_ID,
            join_date=date(2026, 3, 24),
            plan_name="Plano Mensal",
        )
        db = MagicMock()
        db.scalar.side_effect = [0, 0]

        created = create_import_playbook_tasks_for_member(
            db,
            member,
            commit=False,
            now=datetime(2026, 3, 24, tzinfo=timezone.utc),
        )

        assert created == {"onboarding": 1, "plan_followup": 0}

    def test_does_not_create_plan_followup_for_recent_import_when_outside_window(self):
        member = SimpleNamespace(
            id=MEMBER_ID,
            gym_id=GYM_ID,
            join_date=date(2026, 3, 20),
            plan_name="Plano Mensal",
        )
        db = MagicMock()
        db.scalar.side_effect = [0, 0]

        created = create_import_playbook_tasks_for_member(
            db,
            member,
            commit=False,
            now=datetime(2026, 3, 24, tzinfo=timezone.utc),
        )

        assert created["plan_followup"] == 0

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
