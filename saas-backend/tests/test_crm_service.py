"""Tests for crm_service covering lead CRUD, follow-up automation, and CAC."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models import LeadStage, TaskStatus

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
LEAD_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _mock_lead(**overrides):
    defaults = dict(
        id=LEAD_ID, gym_id=GYM_ID, full_name="Lead Teste",
        email="lead@t.com", phone="11999998888",
        stage=LeadStage.NEW, source="instagram",
        estimated_value=Decimal("100"), acquisition_cost=Decimal("10"),
        notes=[], owner_id=None, converted_member_id=None,
        deleted_at=None, last_contact_at=None,
        updated_at=datetime.now(tz=timezone.utc),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestDeleteLead:
    @patch("app.services.crm_service.invalidate_dashboard_cache")
    def test_soft_deletes(self, mock_cache):
        lead = _mock_lead()
        db = MagicMock()
        db.get.return_value = lead
        from app.services.crm_service import delete_lead
        delete_lead(db, LEAD_ID)
        assert lead.deleted_at is not None
        db.commit.assert_called_once()

    def test_not_found_raises(self):
        db = MagicMock()
        db.get.return_value = None
        from app.services.crm_service import delete_lead
        with pytest.raises(HTTPException) as exc_info:
            delete_lead(db, LEAD_ID)
        assert exc_info.value.status_code == 404


class TestCreateLead:
    @patch("app.services.crm_service.invalidate_dashboard_cache")
    def test_creates(self, mock_cache):
        db = MagicMock()
        db.refresh = MagicMock()
        from app.schemas import LeadCreate
        payload = LeadCreate(
            full_name="Novo Lead", source="instagram", gym_id=GYM_ID,
            estimated_value=Decimal("100"), acquisition_cost=Decimal("10"),
        )
        from app.services.crm_service import create_lead
        create_lead(db, payload)
        db.add.assert_called_once()
        db.commit.assert_called_once()


class TestListLeads:
    def test_lists_with_filter(self):
        db = MagicMock()
        db.scalar.return_value = 3
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [_mock_lead()]
        db.scalars.return_value = mock_scalars
        from app.services.crm_service import list_leads
        result = list_leads(db, stage=LeadStage.NEW)
        assert result.total == 3


class TestUpdateLead:
    @patch("app.services.crm_service.invalidate_dashboard_cache")
    def test_updates_stage(self, mock_cache):
        lead = _mock_lead()
        db = MagicMock()
        db.get.return_value = lead
        db.refresh = MagicMock()
        from app.schemas import LeadUpdate
        payload = LeadUpdate(stage=LeadStage.CONTACT)
        from app.services.crm_service import update_lead
        update_lead(db, LEAD_ID, payload)
        assert lead.stage == LeadStage.CONTACT
        assert lead.last_contact_at is not None

    @patch("app.services.crm_service.invalidate_dashboard_cache")
    @patch("app.services.crm_service.send_email")
    def test_won_creates_member(self, mock_email, mock_cache):
        lead = _mock_lead(email="lead@t.com")
        db = MagicMock()
        db.get.return_value = lead
        db.refresh = MagicMock()

        # Simulate flush setting member.id (as the DB would)
        def _fake_flush():
            for call in db.add.call_args_list:
                obj = call[0][0]
                if hasattr(obj, "id") and obj.id is None:
                    obj.id = uuid.uuid4()
        db.flush.side_effect = _fake_flush

        from app.schemas import LeadUpdate
        payload = LeadUpdate(stage=LeadStage.WON)
        from app.services.crm_service import update_lead
        update_lead(db, LEAD_ID, payload)
        assert lead.converted_member_id is not None
        mock_email.assert_called_once()

    def test_not_found_raises(self):
        db = MagicMock()
        db.get.return_value = None
        from app.schemas import LeadUpdate
        from app.services.crm_service import update_lead
        with pytest.raises(HTTPException):
            update_lead(db, LEAD_ID, LeadUpdate(stage=LeadStage.CONTACT))


class TestRunFollowupAutomation:
    @patch("app.services.crm_service.invalidate_dashboard_cache")
    def test_creates_tasks(self, mock_cache):
        lead = _mock_lead(last_contact_at=datetime.now(tz=timezone.utc) - timedelta(days=3))
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [lead]
        db.scalars.return_value = mock_scalars
        db.scalar.return_value = None  # No existing task
        from app.services.crm_service import run_followup_automation
        created = run_followup_automation(db)
        assert created == 1
        db.commit.assert_called_once()

    @patch("app.services.crm_service.invalidate_dashboard_cache")
    def test_skips_existing_task(self, mock_cache):
        lead = _mock_lead(last_contact_at=datetime.now(tz=timezone.utc) - timedelta(days=3))
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [lead]
        db.scalars.return_value = mock_scalars
        db.scalar.return_value = SimpleNamespace(id=uuid.uuid4())  # Existing task
        from app.services.crm_service import run_followup_automation
        created = run_followup_automation(db)
        assert created == 0


class TestCalculateCac:
    def test_with_conversions(self):
        db = MagicMock()
        db.scalar.side_effect = [10, Decimal("500")]  # won_count, total_cost
        from app.services.crm_service import calculate_cac
        result = calculate_cac(db)
        assert result == 50.0

    def test_no_conversions(self):
        db = MagicMock()
        db.scalar.side_effect = [0, Decimal("0")]
        from app.services.crm_service import calculate_cac
        assert calculate_cac(db) == 0.0


class TestCreatePublicDiagnosisLead:
    @patch("app.services.crm_service.invalidate_dashboard_cache")
    def test_creates_lead(self, mock_cache):
        db = MagicMock()
        db.refresh = MagicMock()
        from app.services.crm_service import create_public_diagnosis_lead
        result = create_public_diagnosis_lead(
            db, gym_id=GYM_ID, full_name="Test",
            email="t@t.com", phone="11999", gym_name="Gym",
            total_members=100, avg_monthly_fee=Decimal("99"),
            diagnosis_id=uuid.uuid4(),
        )
        db.add.assert_called_once()


class TestCreatePublicBookingLead:
    @patch("app.services.crm_service.invalidate_dashboard_cache")
    def test_creates_lead(self, mock_cache):
        db = MagicMock()
        db.refresh = MagicMock()
        from app.services.crm_service import create_public_booking_lead
        create_public_booking_lead(
            db, gym_id=GYM_ID, full_name="Visitor",
            email=None, phone="11999",
            scheduled_for=datetime.now(tz=timezone.utc),
        )
        db.add.assert_called_once()


class TestAppendLeadNote:
    def test_appends(self):
        lead = _mock_lead(notes=[{"old": True}])
        db = MagicMock()
        from app.services.crm_service import append_lead_note
        result = append_lead_note(db, lead, {"new": True})
        assert len(result.notes) == 2
