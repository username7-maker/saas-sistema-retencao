"""Tests for weekly_briefing_service."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.weekly_briefing_service import (
    _collect_weekly_metrics,
    _delta_pct,
    _generate_briefing_text,
    _generate_rule_based_briefing,
)


class TestDeltaPct:
    def test_positive_change(self):
        assert _delta_pct(100, 120) == 20.0

    def test_negative_change(self):
        assert _delta_pct(100, 80) == -20.0

    def test_zero_previous_with_current(self):
        assert _delta_pct(0, 50) == 100.0

    def test_zero_both(self):
        assert _delta_pct(0, 0) == 0.0


class TestGenerateRuleBasedBriefing:
    def test_basic_briefing(self):
        metrics = {
            "checkins_this_week": 100,
            "checkins_last_week": 90,
            "checkins_delta_pct": 11.1,
            "new_at_risk": 3,
            "mrr_at_risk": 500.0,
            "total_active": 200,
        }
        text = _generate_rule_based_briefing(metrics)
        assert "100" in text
        assert "Briefing Semanal" in text

    def test_decline_warning(self):
        metrics = {
            "checkins_this_week": 50,
            "checkins_last_week": 100,
            "checkins_delta_pct": -50.0,
            "new_at_risk": 10,
            "mrr_at_risk": 2000.0,
            "total_active": 200,
        }
        text = _generate_rule_based_briefing(metrics)
        assert "Queda significativa" in text
        assert "Aumento de alunos" in text


class TestGenerateBriefingText:
    @patch("app.services.weekly_briefing_service.settings")
    def test_no_api_key_uses_rule_based(self, mock_settings):
        mock_settings.claude_api_key = None
        metrics = {
            "checkins_this_week": 50,
            "checkins_delta_pct": 0.0,
            "new_at_risk": 0,
            "mrr_at_risk": 0.0,
            "total_active": 100,
        }
        text = _generate_briefing_text(metrics)
        assert "Briefing Semanal" in text


class TestCollectWeeklyMetrics:
    def test_collects(self):
        import uuid
        from datetime import datetime, timedelta, timezone
        now = datetime.now(tz=timezone.utc)
        db = MagicMock()
        db.scalar.side_effect = [100, 90, 5, Decimal("1500.00"), 200]

        result = _collect_weekly_metrics(
            db,
            uuid.uuid4(),
            now,
            now - timedelta(days=7),
            now - timedelta(days=14),
        )
        assert result["checkins_this_week"] == 100
        assert result["checkins_last_week"] == 90
        assert result["new_at_risk"] == 5
        assert result["total_active"] == 200


class TestGenerateAndSendWeeklyBriefing:
    @patch("app.services.weekly_briefing_service.send_whatsapp_sync")
    @patch("app.services.weekly_briefing_service._generate_briefing_text", return_value="Briefing")
    @patch("app.services.weekly_briefing_service._collect_weekly_metrics", return_value={})
    @patch("app.services.weekly_briefing_service.get_gym_instance", return_value="gym_abc123")
    def test_sends_to_recipients(self, mock_instance, mock_metrics, mock_text, mock_whatsapp):
        from types import SimpleNamespace
        import uuid
        user = SimpleNamespace(id=uuid.uuid4(), phone="11999")
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [user]
        db.scalars.return_value = mock_scalars

        from app.services.weekly_briefing_service import generate_and_send_weekly_briefing
        result = generate_and_send_weekly_briefing(db, gym_id=uuid.uuid4())
        assert result["briefing_sent_to"] == 1
        assert result["total_recipients"] == 1

    @patch("app.services.weekly_briefing_service.send_whatsapp_sync", side_effect=Exception("fail"))
    @patch("app.services.weekly_briefing_service._generate_briefing_text", return_value="Briefing")
    @patch("app.services.weekly_briefing_service._collect_weekly_metrics", return_value={})
    @patch("app.services.weekly_briefing_service.get_gym_instance", return_value=None)
    def test_handles_send_failure(self, mock_instance, mock_metrics, mock_text, mock_whatsapp):
        from types import SimpleNamespace
        import uuid
        user = SimpleNamespace(id=uuid.uuid4(), phone="11999")
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [user]
        db.scalars.return_value = mock_scalars

        from app.services.weekly_briefing_service import generate_and_send_weekly_briefing
        result = generate_and_send_weekly_briefing(db, gym_id=uuid.uuid4())
        assert result["briefing_sent_to"] == 0
