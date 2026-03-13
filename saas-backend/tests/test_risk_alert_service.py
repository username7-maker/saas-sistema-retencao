"""Tests for risk_alert_service."""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models import RiskLevel, RoleEnum


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


class TestListRiskAlerts:
    @patch("app.services.risk_alert_service.get_current_gym_id", return_value=GYM_ID)
    def test_lists(self, mock_gym):
        db = MagicMock()
        db.scalar.return_value = 2
        db.scalars.return_value.all.return_value = []
        from app.services.risk_alert_service import list_risk_alerts
        result = list_risk_alerts(db)
        assert result.total == 2

    @patch("app.services.risk_alert_service.get_current_gym_id", return_value=None)
    def test_lists_without_gym(self, mock_gym):
        db = MagicMock()
        db.scalar.return_value = 0
        db.scalars.return_value.all.return_value = []
        from app.services.risk_alert_service import list_risk_alerts
        result = list_risk_alerts(db)
        assert result.total == 0


class TestResolveRiskAlert:
    @patch("app.services.risk_alert_service.log_audit_event")
    def test_resolves(self, mock_audit):
        alert = SimpleNamespace(
            id=uuid.uuid4(), member_id=MEMBER_ID,
            resolved=False, resolved_at=None, resolved_by_user_id=None,
            action_history=[],
        )
        user = SimpleNamespace(id=USER_ID)
        db = MagicMock()
        db.get.return_value = alert
        db.refresh = MagicMock()
        from app.services.risk_alert_service import resolve_risk_alert
        result = resolve_risk_alert(db, alert_id=alert.id, current_user=user, resolution_note="OK")
        assert result.resolved is True
        db.commit.assert_called_once()

    def test_not_found_raises(self):
        db = MagicMock()
        db.get.return_value = None
        user = SimpleNamespace(id=USER_ID)
        from app.services.risk_alert_service import resolve_risk_alert
        with pytest.raises(HTTPException) as exc_info:
            resolve_risk_alert(db, alert_id=uuid.uuid4(), current_user=user)
        assert exc_info.value.status_code == 404

    @patch("app.services.risk_alert_service.log_audit_event")
    def test_already_resolved_returns(self, mock_audit):
        alert = SimpleNamespace(
            id=uuid.uuid4(), member_id=MEMBER_ID,
            resolved=True, resolved_at="2026-01-01",
        )
        user = SimpleNamespace(id=USER_ID)
        db = MagicMock()
        db.get.return_value = alert
        from app.services.risk_alert_service import resolve_risk_alert
        result = resolve_risk_alert(db, alert_id=alert.id, current_user=user)
        assert result.resolved is True
        db.commit.assert_not_called()
