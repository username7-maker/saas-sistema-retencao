"""Tests for assessment_goals_service."""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.assessment_goals_service import (
    create_goal,
    create_training_plan,
    list_goals,
    upsert_constraints,
)


MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


class TestUpsertConstraints:
    @patch("app.services.assessment_goals_service.get_member_or_404")
    def test_creates_new(self, mock_get):
        mock_get.return_value = SimpleNamespace(id=MEMBER_ID)
        db = MagicMock()
        db.scalar.return_value = None  # no existing
        db.refresh = MagicMock()
        result = upsert_constraints(db, MEMBER_ID, {"medical_conditions": "nenhuma"})
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @patch("app.services.assessment_goals_service.get_member_or_404")
    def test_updates_existing(self, mock_get):
        mock_get.return_value = SimpleNamespace(id=MEMBER_ID)
        existing = SimpleNamespace(
            member_id=MEMBER_ID, deleted_at=None,
            medical_conditions=None, injuries=None, medications=None,
            contraindications=None, preferred_training_times=None, notes=None,
            restrictions={},
        )
        db = MagicMock()
        db.scalar.return_value = existing
        db.refresh = MagicMock()
        result = upsert_constraints(db, MEMBER_ID, {"injuries": "joelho"})
        assert existing.injuries == "joelho"


class TestCreateGoal:
    @patch("app.services.assessment_goals_service.get_member_or_404")
    def test_creates(self, mock_get):
        mock_get.return_value = SimpleNamespace(id=MEMBER_ID)
        db = MagicMock()
        db.refresh = MagicMock()
        result = create_goal(db, MEMBER_ID, {
            "title": "Perder 5kg",
            "target_value": 75,
            "current_value": 80,
        })
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @patch("app.services.assessment_goals_service.get_member_or_404")
    def test_achieved_sets_100(self, mock_get):
        mock_get.return_value = SimpleNamespace(id=MEMBER_ID)
        db = MagicMock()
        db.refresh = MagicMock()
        result = create_goal(db, MEMBER_ID, {
            "title": "Meta atingida",
            "target_value": 100,
            "current_value": 50,
            "achieved": True,
        })
        goal_arg = db.add.call_args[0][0]
        assert goal_arg.progress_pct == 100


class TestListGoals:
    @patch("app.services.assessment_goals_service.get_member_or_404")
    def test_lists(self, mock_get):
        mock_get.return_value = SimpleNamespace(id=MEMBER_ID)
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars
        result = list_goals(db, MEMBER_ID)
        assert result == []


class TestCreateTrainingPlan:
    @patch("app.services.assessment_goals_service.get_member_or_404")
    def test_creates_and_deactivates_old(self, mock_get):
        mock_get.return_value = SimpleNamespace(id=MEMBER_ID)
        old_plan = SimpleNamespace(is_active=True)
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [old_plan]
        db.scalars.return_value = mock_scalars
        db.refresh = MagicMock()
        result = create_training_plan(db, MEMBER_ID, USER_ID, {
            "name": "Treino A/B/C",
            "sessions_per_week": 4,
        })
        assert old_plan.is_active is False
        db.commit.assert_called_once()
