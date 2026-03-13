"""Tests for task_service covering create, list, update, delete."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models import TaskPriority, TaskStatus
from app.schemas import TaskCreate, TaskUpdate


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TASK_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _mock_task(status=TaskStatus.TODO, **kwargs):
    defaults = dict(
        id=TASK_ID,
        gym_id=GYM_ID,
        title="Test task",
        description="desc",
        status=status,
        kanban_column=status.value,
        priority=TaskPriority.MEDIUM,
        completed_at=None,
        deleted_at=None,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
        due_date=None,
        suggested_message=None,
        extra_data={},
        member=None,
        lead=None,
        member_id=None,
        lead_id=None,
        assigned_to_user_id=None,
        source="MANUAL",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestCreateTask:
    @patch("app.services.task_service.invalidate_dashboard_cache")
    @patch("app.services.task_service._load_with_relations")
    def test_creates_task(self, mock_load, mock_cache):
        task = _mock_task()
        mock_load.return_value = task
        db = MagicMock()
        payload = TaskCreate(title="Test task", gym_id=GYM_ID)
        from app.services.task_service import create_task
        result = create_task(db, payload)
        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert result.title == "Test task"

    @patch("app.services.task_service.invalidate_dashboard_cache")
    @patch("app.services.task_service._load_with_relations")
    def test_done_sets_completed_at(self, mock_load, mock_cache):
        task = _mock_task(status=TaskStatus.DONE, completed_at=datetime.now(tz=timezone.utc))
        mock_load.return_value = task
        db = MagicMock()
        payload = TaskCreate(title="Done task", gym_id=GYM_ID, status=TaskStatus.DONE)
        from app.services.task_service import create_task
        create_task(db, payload)
        added_task = db.add.call_args[0][0]
        assert added_task.completed_at is not None


class TestUpdateTask:
    @patch("app.services.task_service.invalidate_dashboard_cache")
    @patch("app.services.task_service._load_with_relations")
    def test_updates_task(self, mock_load, mock_cache):
        task = _mock_task()
        mock_load.return_value = task
        db = MagicMock()
        db.get.return_value = task
        payload = TaskUpdate(title="Updated")
        from app.services.task_service import update_task
        result = update_task(db, TASK_ID, payload)
        db.commit.assert_called_once()

    def test_not_found_raises(self):
        db = MagicMock()
        db.get.return_value = None
        payload = TaskUpdate(title="Updated")
        from app.services.task_service import update_task
        with pytest.raises(HTTPException) as exc_info:
            update_task(db, TASK_ID, payload)
        assert exc_info.value.status_code == 404

    def test_deleted_task_raises(self):
        task = _mock_task(deleted_at=datetime.now(tz=timezone.utc))
        db = MagicMock()
        db.get.return_value = task
        payload = TaskUpdate(title="Updated")
        from app.services.task_service import update_task
        with pytest.raises(HTTPException):
            update_task(db, TASK_ID, payload)

    @patch("app.services.task_service.invalidate_dashboard_cache")
    @patch("app.services.task_service._load_with_relations")
    def test_marking_done_sets_completed_at(self, mock_load, mock_cache):
        task = _mock_task()
        mock_load.return_value = task
        db = MagicMock()
        db.get.return_value = task
        payload = TaskUpdate(status=TaskStatus.DONE)
        from app.services.task_service import update_task
        update_task(db, TASK_ID, payload)
        assert task.completed_at is not None

    @patch("app.services.task_service.invalidate_dashboard_cache")
    @patch("app.services.task_service._load_with_relations")
    def test_unmarking_done_clears_completed_at(self, mock_load, mock_cache):
        task = _mock_task(status=TaskStatus.DONE, completed_at=datetime.now(tz=timezone.utc))
        mock_load.return_value = task
        db = MagicMock()
        db.get.return_value = task
        payload = TaskUpdate(status=TaskStatus.TODO)
        from app.services.task_service import update_task
        update_task(db, TASK_ID, payload)
        assert task.completed_at is None


class TestDeleteTask:
    @patch("app.services.task_service.invalidate_dashboard_cache")
    def test_soft_deletes(self, mock_cache):
        task = _mock_task()
        db = MagicMock()
        db.get.return_value = task
        from app.services.task_service import delete_task
        delete_task(db, TASK_ID)
        assert task.deleted_at is not None
        db.commit.assert_called_once()

    def test_not_found_raises(self):
        db = MagicMock()
        db.get.return_value = None
        from app.services.task_service import delete_task
        with pytest.raises(HTTPException):
            delete_task(db, TASK_ID)
