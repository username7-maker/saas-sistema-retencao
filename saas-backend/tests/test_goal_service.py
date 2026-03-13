"""Tests for goal_service."""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.goal_service import (
    _progress_pct,
    _status,
    create_goal,
    delete_goal,
    get_goal_or_404,
    list_goals,
    update_goal,
)


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _goal_create(**overrides):
    from app.schemas.goal import GoalCreate
    defaults = dict(
        name="Meta MRR",
        metric_type="mrr",
        target_value=10000.0,
        comparator="gte",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        alert_threshold_pct=50,
    )
    defaults.update(overrides)
    return GoalCreate(**defaults)


class TestCreateGoal:
    def test_creates(self):
        db = MagicMock()
        db.refresh = MagicMock()
        result = create_goal(db, _goal_create())
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_invalid_period_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            create_goal(MagicMock(), _goal_create(
                period_start=date(2026, 12, 1),
                period_end=date(2026, 1, 1),
            ))
        assert exc_info.value.status_code == 400


class TestGetGoalOr404:
    def test_found(self):
        goal = SimpleNamespace(id=uuid.uuid4())
        db = MagicMock()
        db.get.return_value = goal
        assert get_goal_or_404(db, goal.id) == goal

    def test_not_found(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(HTTPException):
            get_goal_or_404(db, uuid.uuid4())


class TestListGoals:
    def test_lists_all(self):
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars
        result = list_goals(db)
        assert result == []

    def test_active_only(self):
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars
        result = list_goals(db, active_only=True)
        assert result == []


class TestUpdateGoal:
    def test_updates(self):
        goal = SimpleNamespace(
            id=uuid.uuid4(), metric_type="mrr", target_value=10000,
            period_start=date(2026, 1, 1), period_end=date(2026, 12, 31),
        )
        db = MagicMock()
        db.get.return_value = goal
        db.refresh = MagicMock()
        from app.schemas.goal import GoalUpdate
        result = update_goal(db, goal.id, GoalUpdate(target_value=20000))
        db.commit.assert_called_once()

    def test_invalid_period_raises(self):
        goal = SimpleNamespace(
            id=uuid.uuid4(), metric_type="mrr", target_value=10000,
            period_start=date(2026, 1, 1), period_end=date(2026, 12, 31),
        )
        db = MagicMock()
        db.get.return_value = goal
        from app.schemas.goal import GoalUpdate
        with pytest.raises(HTTPException):
            update_goal(db, goal.id, GoalUpdate(period_end=date(2025, 1, 1)))


class TestDeleteGoal:
    def test_deletes(self):
        goal = SimpleNamespace(id=uuid.uuid4())
        db = MagicMock()
        db.get.return_value = goal
        delete_goal(db, goal.id)
        db.delete.assert_called_once()
        db.commit.assert_called_once()


class TestProgressPct:
    def test_gte_comparator(self):
        assert _progress_pct("gte", 100, 75) == 75.0

    def test_lte_comparator(self):
        assert _progress_pct("lte", 5, 10) == 50.0

    def test_zero_target(self):
        assert _progress_pct("gte", 0, 100) == 0.0

    def test_lte_zero_current(self):
        assert _progress_pct("lte", 5, 0) == 100.0


class TestStatusFn:
    def test_achieved_gte(self):
        s, msg = _status("gte", 100, 150, 50, 150.0)
        assert s == "achieved"

    def test_at_risk(self):
        s, msg = _status("gte", 100, 20, 50, 20.0)
        assert s == "at_risk"

    def test_on_track(self):
        s, msg = _status("gte", 100, 70, 50, 70.0)
        assert s == "on_track"

    def test_achieved_lte(self):
        s, msg = _status("lte", 5, 3, 50, 100.0)
        assert s == "achieved"
