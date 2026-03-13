"""
Test that onboarding and plan followup tasks are not duplicated.
"""
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.onboarding_service import (
    create_onboarding_tasks_for_member,
    create_plan_followup_tasks_for_member,
)

MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _make_member(plan_name="Plano Mensal"):
    return SimpleNamespace(
        id=MEMBER_ID,
        gym_id=GYM_ID,
        join_date=date.today(),
        plan_name=plan_name,
        assigned_user_id=None,
    )


def _make_db_with_count(count):
    db = MagicMock()
    db.scalar.return_value = count
    return db


def test_onboarding_tasks_not_created_when_already_exist():
    """create_onboarding_tasks_for_member should return early if tasks exist."""
    db = _make_db_with_count(6)  # already 6 onboarding tasks
    member = _make_member()

    create_onboarding_tasks_for_member(db, member)

    db.add_all.assert_not_called()
    db.commit.assert_not_called()


def test_onboarding_tasks_created_when_none_exist():
    """create_onboarding_tasks_for_member should create tasks when none exist."""
    db = _make_db_with_count(0)
    member = _make_member()

    create_onboarding_tasks_for_member(db, member)

    db.add_all.assert_called_once()
    db.commit.assert_called_once()


def test_plan_followup_tasks_not_created_when_already_exist():
    """create_plan_followup_tasks_for_member should return early if tasks exist."""
    db = _make_db_with_count(3)  # already 3 followup tasks
    member = _make_member("Plano Mensal")

    create_plan_followup_tasks_for_member(db, member)

    db.add_all.assert_not_called()


def test_plan_followup_tasks_created_when_none_exist():
    """create_plan_followup_tasks_for_member should create tasks when none exist."""
    db = _make_db_with_count(0)
    member = _make_member("Plano Mensal")

    create_plan_followup_tasks_for_member(db, member)

    db.add_all.assert_called_once()
    db.commit.assert_called_once()
