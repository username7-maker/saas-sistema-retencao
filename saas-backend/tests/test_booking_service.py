"""Tests for booking_service."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
LEAD_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


class TestGetBookingStatus:
    @patch("app.services.booking_service.get_current_gym_id", return_value=GYM_ID)
    def test_no_booking(self, mock_gym):
        db = MagicMock()
        db.scalar.return_value = None
        from app.services.booking_service import get_booking_status
        result = get_booking_status(db, LEAD_ID)
        assert result["has_booking"] is False

    @patch("app.services.booking_service.get_current_gym_id", return_value=GYM_ID)
    def test_has_booking(self, mock_gym):
        booking = SimpleNamespace(
            id=uuid.uuid4(),
            scheduled_for=datetime.now(tz=timezone.utc) + timedelta(days=1),
            status="confirmed",
            provider_name="Cal.com",
        )
        db = MagicMock()
        db.scalar.return_value = booking
        from app.services.booking_service import get_booking_status
        result = get_booking_status(db, LEAD_ID)
        assert result["has_booking"] is True
        assert result["provider_name"] == "Cal.com"


class TestProcessBookingReminders:
    @patch("app.services.booking_service.send_whatsapp_sync")
    @patch("app.services.booking_service.settings")
    def test_sends_reminders(self, mock_settings, mock_whatsapp):
        mock_settings.booking_reminder_minutes_before = 30
        mock_whatsapp.return_value = SimpleNamespace(status="sent")
        lead = SimpleNamespace(phone="11999")
        booking = SimpleNamespace(
            lead_id=LEAD_ID,
            prospect_whatsapp="11999",
            scheduled_for=datetime.now(tz=timezone.utc),
            reminder_sent_at=None,
        )
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [booking]
        db.scalars.return_value = mock_scalars
        db.get.return_value = lead

        from app.services.booking_service import process_booking_reminders
        result = process_booking_reminders(db)
        assert result["processed"] == 1
        assert result["sent"] == 1

    @patch("app.services.booking_service.send_whatsapp_sync")
    @patch("app.services.booking_service.settings")
    def test_skips_no_phone(self, mock_settings, mock_whatsapp):
        mock_settings.booking_reminder_minutes_before = 30
        booking = SimpleNamespace(
            lead_id=None,
            prospect_whatsapp=None,
            scheduled_for=datetime.now(tz=timezone.utc),
            reminder_sent_at=None,
        )
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [booking]
        db.scalars.return_value = mock_scalars

        from app.services.booking_service import process_booking_reminders
        result = process_booking_reminders(db)
        assert result["processed"] == 1
        assert result["sent"] == 0


class TestResolvePublicGymId:
    @patch("app.services.booking_service.settings")
    def test_raises_without_config(self, mock_settings):
        mock_settings.public_diag_gym_id = ""
        from app.services.booking_service import _resolve_public_gym_id
        with pytest.raises(HTTPException) as exc_info:
            _resolve_public_gym_id()
        assert exc_info.value.status_code == 503

    @patch("app.services.booking_service.settings")
    def test_returns_uuid(self, mock_settings):
        mock_settings.public_diag_gym_id = str(GYM_ID)
        from app.services.booking_service import _resolve_public_gym_id
        result = _resolve_public_gym_id()
        assert result == GYM_ID


class TestPhoneFromSequence:
    def test_returns_phone(self):
        seq = SimpleNamespace(prospect_whatsapp="11888")
        db = MagicMock()
        db.scalar.return_value = seq
        from app.services.booking_service import _phone_from_sequence
        assert _phone_from_sequence(db, LEAD_ID) == "11888"

    def test_returns_none(self):
        db = MagicMock()
        db.scalar.return_value = None
        from app.services.booking_service import _phone_from_sequence
        assert _phone_from_sequence(db, LEAD_ID) is None
