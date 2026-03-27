"""Tests for audit_service, checkin_service, notification_service."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models import RoleEnum

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


# ---------------------------------------------------------------------------
# audit_service
# ---------------------------------------------------------------------------

class TestLogAuditEvent:
    def test_logs_event_with_user(self):
        user = SimpleNamespace(id=USER_ID, gym_id=GYM_ID)
        db = MagicMock()
        from app.services.audit_service import log_audit_event
        result = log_audit_event(db, "LOGIN", "user", user=user)
        db.add.assert_called_once()
        db.flush.assert_called_once()
        assert result is not None

    def test_logs_event_with_gym_id(self):
        db = MagicMock()
        from app.services.audit_service import log_audit_event
        result = log_audit_event(db, "EXPORT", "member", gym_id=GYM_ID, member_id=MEMBER_ID)
        db.add.assert_called_once()
        assert result is not None

    @patch("app.services.audit_service.get_current_gym_id", return_value=None)
    def test_returns_none_without_gym_id(self, mock_gym):
        db = MagicMock()
        from app.services.audit_service import log_audit_event
        result = log_audit_event(db, "TEST", "entity")
        assert result is None
        db.add.assert_not_called()

    def test_no_flush_when_disabled(self):
        user = SimpleNamespace(id=USER_ID, gym_id=GYM_ID)
        db = MagicMock()
        from app.services.audit_service import log_audit_event
        log_audit_event(db, "CREATE", "member", user=user, flush=False)
        db.flush.assert_not_called()

    def test_redacts_sensitive_details(self):
        user = SimpleNamespace(id=USER_ID, gym_id=GYM_ID)
        db = MagicMock()
        from app.services.audit_service import log_audit_event

        result = log_audit_event(
            db,
            "LOGIN_FAILED",
            "user",
            user=user,
            details={
                "email": "owner@gym.test",
                "gym_slug": "academia-centro",
                "recipient": "lead@gym.test",
                "context": {"whatsapp": "5511999999999"},
            },
        )

        assert result is not None
        assert result.details["email"] == "[redacted-email]"
        assert result.details["gym_slug"] == "[redacted-slug]"
        assert result.details["recipient"] == "[redacted-recipient]"
        assert result.details["context"]["whatsapp"] == "[redacted-phone]"


# ---------------------------------------------------------------------------
# checkin_service
# ---------------------------------------------------------------------------

class TestCreateCheckin:
    @patch("app.services.checkin_service.invalidate_dashboard_cache")
    def test_creates_checkin(self, mock_cache):
        member = SimpleNamespace(id=MEMBER_ID, last_checkin_at=None, deleted_at=None)
        db = MagicMock()
        db.scalar.side_effect = [member, None]  # member found, no duplicate
        db.refresh = MagicMock()

        from app.models.enums import CheckinSource
        from app.schemas import CheckinCreate
        payload = CheckinCreate(
            member_id=MEMBER_ID,
            checkin_at=datetime(2026, 3, 10, 18, 30, tzinfo=timezone.utc),
            source=CheckinSource.MANUAL,
        )
        from app.services.checkin_service import create_checkin
        result = create_checkin(db, payload)
        db.commit.assert_called_once()
        assert member.last_checkin_at is not None

    @patch("app.services.checkin_service.invalidate_dashboard_cache")
    def test_creates_checkin_without_committing_when_router_owns_transaction(self, mock_cache):
        member = SimpleNamespace(id=MEMBER_ID, last_checkin_at=None, deleted_at=None)
        db = MagicMock()
        db.scalar.side_effect = [member, None]
        db.refresh = MagicMock()

        from app.models.enums import CheckinSource
        from app.schemas import CheckinCreate

        payload = CheckinCreate(
            member_id=MEMBER_ID,
            checkin_at=datetime(2026, 3, 10, 18, 30, tzinfo=timezone.utc),
            source=CheckinSource.MANUAL,
        )
        from app.services.checkin_service import create_checkin

        result = create_checkin(db, payload, commit=False)

        assert result is not None
        assert member.last_checkin_at is not None
        db.commit.assert_not_called()
        db.flush.assert_called_once()

    def test_member_not_found_raises(self):
        db = MagicMock()
        db.scalar.return_value = None

        from app.models.enums import CheckinSource
        from app.schemas import CheckinCreate
        payload = CheckinCreate(
            member_id=MEMBER_ID,
            checkin_at=datetime(2026, 3, 10, 18, 30, tzinfo=timezone.utc),
            source=CheckinSource.MANUAL,
        )
        from app.services.checkin_service import create_checkin
        with pytest.raises(ValueError, match="nao encontrado"):
            create_checkin(db, payload)

    def test_duplicate_raises(self):
        member = SimpleNamespace(id=MEMBER_ID, last_checkin_at=None, deleted_at=None)
        existing_checkin = SimpleNamespace(id=uuid.uuid4())
        db = MagicMock()
        db.scalar.side_effect = [member, existing_checkin]

        from app.models.enums import CheckinSource
        from app.schemas import CheckinCreate
        payload = CheckinCreate(
            member_id=MEMBER_ID,
            checkin_at=datetime(2026, 3, 10, 18, 30, tzinfo=timezone.utc),
            source=CheckinSource.MANUAL,
        )
        from app.services.checkin_service import create_checkin
        with pytest.raises(ValueError, match="duplicado"):
            create_checkin(db, payload)

    @patch("app.services.checkin_service.invalidate_dashboard_cache")
    def test_naive_datetime_gets_utc(self, mock_cache):
        member = SimpleNamespace(id=MEMBER_ID, last_checkin_at=None, deleted_at=None)
        db = MagicMock()
        db.scalar.side_effect = [member, None]
        db.refresh = MagicMock()

        from app.models.enums import CheckinSource
        from app.schemas import CheckinCreate
        payload = CheckinCreate(
            member_id=MEMBER_ID,
            checkin_at=datetime(2026, 3, 10, 18, 30),  # Naive
            source=CheckinSource.MANUAL,
        )
        from app.services.checkin_service import create_checkin
        create_checkin(db, payload)
        assert member.last_checkin_at.tzinfo is not None


# ---------------------------------------------------------------------------
# notification_service
# ---------------------------------------------------------------------------

class TestCreateNotification:
    def test_creates(self):
        db = MagicMock()
        from app.services.notification_service import create_notification
        result = create_notification(db, title="Alerta", message="Risco alto", member_id=MEMBER_ID)
        db.add.assert_called_once()
        db.flush.assert_called_once()
        assert result.title == "Alerta"

    def test_no_flush(self):
        db = MagicMock()
        from app.services.notification_service import create_notification
        create_notification(db, title="T", message="M", flush=False)
        db.flush.assert_not_called()


class TestListNotifications:
    def test_lists_for_user(self):
        user = SimpleNamespace(id=USER_ID, role=RoleEnum.SALESPERSON)
        db = MagicMock()
        db.scalar.return_value = 5
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars

        from app.services.notification_service import list_notifications
        result = list_notifications(db, current_user=user)
        assert result.total == 5

    def test_owner_sees_all(self):
        user = SimpleNamespace(id=USER_ID, role=RoleEnum.OWNER)
        db = MagicMock()
        db.scalar.return_value = 10
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars

        from app.services.notification_service import list_notifications
        result = list_notifications(db, current_user=user, include_all=True)
        assert result.total == 10


class TestMarkNotificationRead:
    def test_marks_read(self):
        notif = SimpleNamespace(id=uuid.uuid4(), user_id=USER_ID, read_at=None)
        user = SimpleNamespace(id=USER_ID, role=RoleEnum.OWNER)
        db = MagicMock()
        db.get.return_value = notif
        db.refresh = MagicMock()

        from app.services.notification_service import mark_notification_read
        result = mark_notification_read(db, notification_id=notif.id, current_user=user)
        assert result.read_at is not None

    def test_marks_read_without_committing_when_router_owns_transaction(self):
        notif = SimpleNamespace(id=uuid.uuid4(), user_id=USER_ID, read_at=None)
        user = SimpleNamespace(id=USER_ID, role=RoleEnum.OWNER)
        db = MagicMock()
        db.get.return_value = notif
        db.refresh = MagicMock()

        from app.services.notification_service import mark_notification_read

        result = mark_notification_read(db, notification_id=notif.id, current_user=user, commit=False)

        assert result.read_at is not None
        db.commit.assert_not_called()
        db.flush.assert_called_once()

    def test_not_found_raises(self):
        user = SimpleNamespace(id=USER_ID, role=RoleEnum.OWNER)
        db = MagicMock()
        db.get.return_value = None

        from app.services.notification_service import mark_notification_read
        with pytest.raises(HTTPException) as exc_info:
            mark_notification_read(db, notification_id=uuid.uuid4(), current_user=user)
        assert exc_info.value.status_code == 404

    def test_forbidden_for_other_user(self):
        other_user_id = uuid.uuid4()
        notif = SimpleNamespace(id=uuid.uuid4(), user_id=other_user_id, read_at=None)
        user = SimpleNamespace(id=USER_ID, role=RoleEnum.SALESPERSON)
        db = MagicMock()
        db.get.return_value = notif

        from app.services.notification_service import mark_notification_read
        with pytest.raises(HTTPException) as exc_info:
            mark_notification_read(db, notification_id=notif.id, current_user=user)
        assert exc_info.value.status_code == 403
