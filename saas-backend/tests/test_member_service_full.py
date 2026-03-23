"""Tests for member_service covering create, list, update, delete."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models import MemberStatus, RiskLevel
from app.schemas import MemberCreate, MemberUpdate

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _mock_member(**overrides):
    defaults = dict(
        id=MEMBER_ID, gym_id=GYM_ID, full_name="Aluno Teste",
        email="aluno@t.com", phone="11999998888",
        status=MemberStatus.ACTIVE, risk_level=RiskLevel.GREEN,
        risk_score=0, join_date=date.today(), plan_name="Mensal",
        monthly_fee=Decimal("99.90"), deleted_at=None,
        loyalty_months=0, preferred_shift=None, assigned_user_id=None,
        extra_data={}, cpf_encrypted=None, updated_at=datetime.now(tz=timezone.utc),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestCreateMember:
    @patch("app.services.member_service.invalidate_dashboard_cache")
    @patch("app.services.member_service.create_plan_followup_tasks_for_member")
    @patch("app.services.member_service.create_onboarding_tasks_for_member")
    @patch("app.services.member_service.get_current_gym_id", return_value=GYM_ID)
    def test_creates_member(self, mock_gym, mock_onboard, mock_followup, mock_cache):
        db = MagicMock()
        db.scalar.return_value = None  # No duplicate email
        db.refresh = MagicMock()
        payload = MemberCreate(full_name="Novo", email="novo@t.com", plan_name="Mensal", monthly_fee=Decimal("99.90"), join_date=date.today())
        from app.services.member_service import create_member
        create_member(db, payload)
        db.add.assert_called_once()
        db.commit.assert_called_once()
        mock_onboard.assert_called_once()
        mock_onboard.assert_called_once_with(db, mock_onboard.call_args.args[1], commit=True)
        mock_followup.assert_called_once_with(db, mock_followup.call_args.args[1], commit=True)

    @patch("app.services.member_service.get_current_gym_id", return_value=GYM_ID)
    def test_duplicate_email_raises(self, mock_gym):
        db = MagicMock()
        db.scalar.return_value = _mock_member()  # Existing
        payload = MemberCreate(full_name="Dup", email="aluno@t.com", plan_name="Mensal", monthly_fee=Decimal("99.90"), join_date=date.today())
        from app.services.member_service import create_member
        with pytest.raises(HTTPException) as exc_info:
            create_member(db, payload)
        assert exc_info.value.status_code == 400

    def test_no_gym_context_raises(self):
        db = MagicMock()
        payload = MemberCreate(full_name="Novo", plan_name="Mensal", monthly_fee=Decimal("99.90"), join_date=date.today())
        with patch("app.services.member_service.get_current_gym_id", return_value=None):
            from app.services.member_service import create_member
            with pytest.raises(HTTPException) as exc_info:
                create_member(db, payload)
            assert exc_info.value.status_code == 400

    @patch("app.services.member_service.invalidate_dashboard_cache")
    @patch("app.services.member_service.create_plan_followup_tasks_for_member")
    @patch("app.services.member_service.create_onboarding_tasks_for_member")
    @patch("app.services.member_service.encrypt_cpf", return_value="encrypted")
    def test_creates_with_cpf(self, mock_enc, mock_onboard, mock_followup, mock_cache):
        db = MagicMock()
        db.scalar.return_value = None
        db.refresh = MagicMock()
        payload = MemberCreate(
            full_name="CPF", plan_name="Mensal", monthly_fee=Decimal("99.90"),
            join_date=date.today(), cpf="12345678901",
        )
        from app.services.member_service import create_member
        create_member(db, payload, gym_id=GYM_ID)
        mock_enc.assert_called_once_with("12345678901")

    @patch("app.services.member_service.invalidate_dashboard_cache")
    @patch("app.services.member_service.create_plan_followup_tasks_for_member")
    @patch("app.services.member_service.create_onboarding_tasks_for_member")
    def test_commit_false_avoids_premature_commit(self, mock_onboard, mock_followup, mock_cache):
        db = MagicMock()
        db.scalar.return_value = None
        db.refresh = MagicMock()
        payload = MemberCreate(
            full_name="Novo",
            email="novo@t.com",
            plan_name="Mensal",
            monthly_fee=Decimal("99.90"),
            join_date=date.today(),
        )
        from app.services.member_service import create_member
        create_member(db, payload, gym_id=GYM_ID, commit=False)
        db.commit.assert_not_called()
        db.flush.assert_called_once()
        mock_onboard.assert_called_once_with(db, mock_onboard.call_args.args[1], commit=False)
        mock_followup.assert_called_once_with(db, mock_followup.call_args.args[1], commit=False)

    @patch("app.services.member_service.invalidate_dashboard_cache")
    @patch("app.services.member_service.create_plan_followup_tasks_for_member")
    @patch("app.services.member_service.create_onboarding_tasks_for_member", side_effect=RuntimeError("boom"))
    def test_commit_false_keeps_transaction_open_when_task_creation_fails(self, mock_onboard, mock_followup, mock_cache):
        db = MagicMock()
        db.scalar.return_value = None
        db.refresh = MagicMock()
        payload = MemberCreate(
            full_name="Novo",
            email="novo@t.com",
            plan_name="Mensal",
            monthly_fee=Decimal("99.90"),
            join_date=date.today(),
        )
        from app.services.member_service import create_member
        with pytest.raises(RuntimeError):
            create_member(db, payload, gym_id=GYM_ID, commit=False)
        db.commit.assert_not_called()


class TestGetMemberOr404:
    def test_found(self):
        db = MagicMock()
        db.scalar.return_value = _mock_member()
        from app.services.member_service import get_member_or_404
        result = get_member_or_404(db, MEMBER_ID)
        assert result.id == MEMBER_ID

    def test_not_found_raises(self):
        db = MagicMock()
        db.scalar.return_value = None
        from app.services.member_service import get_member_or_404
        with pytest.raises(HTTPException) as exc_info:
            get_member_or_404(db, MEMBER_ID)
        assert exc_info.value.status_code == 404


class TestUpdateMember:
    @patch("app.services.member_service.invalidate_dashboard_cache")
    @patch("app.services.member_service.get_member_or_404")
    def test_updates_fields(self, mock_get, mock_cache):
        member = _mock_member()
        mock_get.return_value = member
        db = MagicMock()
        db.refresh = MagicMock()
        payload = MemberUpdate(full_name="Atualizado")
        from app.services.member_service import update_member
        result = update_member(db, MEMBER_ID, payload)
        assert member.full_name == "Atualizado"
        db.commit.assert_called_once()

    @patch("app.services.member_service.invalidate_dashboard_cache")
    @patch("app.services.member_service.get_member_or_404")
    @patch("app.services.member_service.encrypt_cpf", return_value="new-enc")
    def test_updates_cpf(self, mock_enc, mock_get, mock_cache):
        member = _mock_member()
        mock_get.return_value = member
        db = MagicMock()
        db.refresh = MagicMock()
        payload = MemberUpdate(cpf="12345678901")
        from app.services.member_service import update_member
        update_member(db, MEMBER_ID, payload)
        assert member.cpf_encrypted == "new-enc"


class TestSoftDeleteMember:
    @patch("app.services.member_service.invalidate_dashboard_cache")
    @patch("app.services.member_service.get_member_or_404")
    def test_soft_deletes(self, mock_get, mock_cache):
        member = _mock_member()
        mock_get.return_value = member
        db = MagicMock()
        from app.services.member_service import soft_delete_member
        soft_delete_member(db, MEMBER_ID)
        assert member.deleted_at is not None
        assert member.status == MemberStatus.CANCELLED
        db.commit.assert_called_once()
