"""Tests for booking_service."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models import LeadStage
from app.schemas.sales import PublicBookingConfirmRequest

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


class TestConfirmPublicBooking:
    def test_creates_public_lead_without_premature_commit(self, monkeypatch):
        lead = SimpleNamespace(
            id=LEAD_ID,
            gym_id=GYM_ID,
            stage=LeadStage.NEW,
            last_contact_at=None,
            notes=[],
            phone="11999998888",
            email="lead@test.com",
            deleted_at=None,
        )
        booking = SimpleNamespace(
            id=uuid.uuid4(),
            provider_name="cal",
            scheduled_for=datetime.now(tz=timezone.utc) + timedelta(days=1),
            prospect_whatsapp="11999998888",
            status="confirmed",
        )
        db = MagicMock()
        db.get.return_value = None
        db.scalar.return_value = None

        def _create_lead(*args, **kwargs):
            assert kwargs["commit"] is False
            db.commit.assert_not_called()
            return lead

        monkeypatch.setattr("app.services.booking_service._resolve_public_gym_id", lambda: GYM_ID)
        monkeypatch.setattr("app.services.booking_service.create_public_booking_lead", _create_lead)
        monkeypatch.setattr("app.services.booking_service.pause_sequences_for_lead", lambda *_args, **_kwargs: None)
        monkeypatch.setattr("app.services.booking_service._send_booking_confirmation_whatsapp", lambda *_args, **_kwargs: None)
        monkeypatch.setattr("app.services.booking_service._upsert_booking", lambda *_args, **_kwargs: booking)

        from app.services.booking_service import confirm_public_booking

        saved_lead, saved_booking = confirm_public_booking(
            db,
            PublicBookingConfirmRequest(
                prospect_name="Lead Booking",
                email="lead@test.com",
                whatsapp="11999998888",
                scheduled_for=booking.scheduled_for,
                provider_name="cal",
                provider_booking_id="booking-1",
            ),
        )

        assert saved_lead.id == lead.id
        assert saved_booking.id == booking.id
        assert db.commit.call_count == 2

    def test_does_not_commit_when_core_flow_fails_before_main_commit(self, monkeypatch):
        lead = SimpleNamespace(
            id=LEAD_ID,
            gym_id=GYM_ID,
            stage=LeadStage.NEW,
            last_contact_at=None,
            notes=[],
            phone="11999998888",
            email="lead@test.com",
            deleted_at=None,
        )
        db = MagicMock()

        monkeypatch.setattr("app.services.booking_service._resolve_public_gym_id", lambda: GYM_ID)
        monkeypatch.setattr("app.services.booking_service._resolve_or_create_public_lead", lambda *_args, **_kwargs: lead)
        monkeypatch.setattr(
            "app.services.booking_service._upsert_booking",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        from app.services.booking_service import confirm_public_booking

        with pytest.raises(RuntimeError):
            confirm_public_booking(
                db,
                PublicBookingConfirmRequest(
                    prospect_name="Lead Booking",
                    email="lead@test.com",
                    whatsapp="11999998888",
                    scheduled_for=datetime.now(tz=timezone.utc) + timedelta(days=1),
                    provider_name="cal",
                ),
            )

        db.commit.assert_not_called()

    def test_logs_and_keeps_booking_when_confirmation_whatsapp_fails(self, monkeypatch):
        lead = SimpleNamespace(
            id=LEAD_ID,
            gym_id=GYM_ID,
            stage=LeadStage.NEW,
            last_contact_at=None,
            notes=[],
            phone="11999998888",
            email="lead@test.com",
            deleted_at=None,
        )
        booking = SimpleNamespace(
            id=uuid.uuid4(),
            provider_name="cal",
            scheduled_for=datetime.now(tz=timezone.utc) + timedelta(days=1),
            prospect_whatsapp="11999998888",
            status="confirmed",
        )
        db = MagicMock()

        monkeypatch.setattr("app.services.booking_service._resolve_public_gym_id", lambda: GYM_ID)
        monkeypatch.setattr("app.services.booking_service._resolve_or_create_public_lead", lambda *_args, **_kwargs: lead)
        monkeypatch.setattr("app.services.booking_service._upsert_booking", lambda *_args, **_kwargs: booking)
        monkeypatch.setattr("app.services.booking_service.pause_sequences_for_lead", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(
            "app.services.booking_service._send_booking_confirmation_whatsapp",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("whatsapp down")),
        )

        from app.services.booking_service import confirm_public_booking

        saved_lead, saved_booking = confirm_public_booking(
            db,
            PublicBookingConfirmRequest(
                prospect_name="Lead Booking",
                email="lead@test.com",
                whatsapp="11999998888",
                scheduled_for=booking.scheduled_for,
                provider_name="cal",
            ),
        )

        assert saved_lead.id == lead.id
        assert saved_booking.id == booking.id
        db.commit.assert_called_once()
        db.rollback.assert_called_once()

    def test_can_skip_commit_and_external_side_effect_for_router_owned_flow(self, monkeypatch):
        lead = SimpleNamespace(
            id=LEAD_ID,
            gym_id=GYM_ID,
            stage=LeadStage.NEW,
            last_contact_at=None,
            notes=[],
            phone="11999998888",
            email="lead@test.com",
            deleted_at=None,
        )
        booking = SimpleNamespace(
            id=uuid.uuid4(),
            provider_name="cal",
            scheduled_for=datetime.now(tz=timezone.utc) + timedelta(days=1),
            prospect_whatsapp="11999998888",
            status="confirmed",
        )
        db = MagicMock()
        db.get.return_value = None
        db.scalar.return_value = None

        monkeypatch.setattr("app.services.booking_service._resolve_public_gym_id", lambda: GYM_ID)
        monkeypatch.setattr("app.services.booking_service._resolve_or_create_public_lead", lambda *_args, **_kwargs: lead)
        monkeypatch.setattr("app.services.booking_service.pause_sequences_for_lead", lambda *_args, **_kwargs: None)
        monkeypatch.setattr("app.services.booking_service._upsert_booking", lambda *_args, **_kwargs: booking)
        monkeypatch.setattr("app.services.booking_service._send_booking_confirmation_whatsapp", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("nao deveria enviar")))

        from app.services.booking_service import confirm_public_booking

        saved_lead, saved_booking = confirm_public_booking(
            db,
            PublicBookingConfirmRequest(
                prospect_name="Lead Booking",
                email="lead@test.com",
                whatsapp="11999998888",
                scheduled_for=booking.scheduled_for,
                provider_name="cal",
                provider_booking_id="booking-1",
            ),
            commit=False,
            dispatch_confirmation_whatsapp=False,
        )

        assert saved_lead.id == lead.id
        assert saved_booking.id == booking.id
        db.commit.assert_not_called()
        db.flush.assert_called()

    def test_rejects_whatsapp_dispatch_before_commit(self, monkeypatch):
        monkeypatch.setattr("app.services.booking_service._resolve_public_gym_id", lambda: GYM_ID)

        from app.services.booking_service import confirm_public_booking

        with pytest.raises(ValueError, match="dispatch_confirmation_whatsapp requer commit=True"):
            confirm_public_booking(
                MagicMock(),
                PublicBookingConfirmRequest(
                    prospect_name="Lead Booking",
                    email="lead@test.com",
                    whatsapp="11999998888",
                    scheduled_for=datetime.now(tz=timezone.utc) + timedelta(days=1),
                    provider_name="cal",
                ),
                commit=False,
                dispatch_confirmation_whatsapp=True,
            )
