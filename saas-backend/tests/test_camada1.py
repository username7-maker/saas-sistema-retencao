"""Tests for CAMADA 1 — AI-First Intelligence features."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models.enums import RiskLevel
from app.services import risk as risk_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class DummyDB:
    """Minimal DB mock that pops scalar values from a list."""

    def __init__(self, values=None):
        self.values = list(values or [])
        self.added = []

    def scalar(self, _query):
        if not self.values:
            return 0
        return self.values.pop(0)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        pass

    def commit(self):
        pass

    def scalars(self, _query):
        return self

    def all(self):
        return []

    def execute(self, _query):
        return self


# ===========================================================================
# 1.1 — Risk Score com Baseline Individual
# ===========================================================================


class TestFrequencyDropBaseline:
    """Tests for _frequency_drop_points with individual baseline logic."""

    def test_member_training_5x_drops_to_1x_gets_high_score(self):
        # baseline_total = 45 (9 weeks * 5 check-ins/week), current = 1
        # baseline_avg = 45/9 = 5.0
        # drop_pct = (5 - 1) / 5 * 100 = 80% → 20 pts
        db = DummyDB(values=[1, 45])
        now = datetime.now(tz=timezone.utc)

        points, drop_pct, baseline_avg = risk_service._frequency_drop_points(db, "member-1", now)

        assert points == 20
        assert drop_pct >= 80.0
        assert baseline_avg == 5.0

    def test_member_training_1x_stays_1x_gets_low_score(self):
        # baseline_total = 9 (9 weeks * 1 check-in/week), current = 1
        # baseline_avg = 9/9 = 1.0
        # drop_pct = (1 - 1) / 1 * 100 = 0% → 0 pts
        db = DummyDB(values=[1, 9])
        now = datetime.now(tz=timezone.utc)

        points, drop_pct, baseline_avg = risk_service._frequency_drop_points(db, "member-1", now)

        assert points == 0
        assert drop_pct == 0.0
        assert baseline_avg == 1.0

    def test_member_training_1x_drops_to_0x_gets_high_score(self):
        # baseline_total = 9, current = 0
        # drop_pct = (1 - 0) / 1 * 100 = 100% → 20 pts
        db = DummyDB(values=[0, 9])
        now = datetime.now(tz=timezone.utc)

        points, drop_pct, baseline_avg = risk_service._frequency_drop_points(db, "member-1", now)

        assert points == 20
        assert drop_pct == 100.0

    def test_new_member_no_history_no_current(self):
        # Both queries return 0
        db = DummyDB(values=[0, 0])
        now = datetime.now(tz=timezone.utc)

        points, drop_pct, baseline_avg = risk_service._frequency_drop_points(db, "member-1", now)

        assert points == 12
        assert drop_pct == 100.0
        assert baseline_avg == 0.0

    def test_new_member_no_history_with_current(self):
        # baseline = 0, current = 3
        db = DummyDB(values=[3, 0])
        now = datetime.now(tz=timezone.utc)

        points, drop_pct, baseline_avg = risk_service._frequency_drop_points(db, "member-1", now)

        assert points == 0
        assert drop_pct == 0.0

    def test_moderate_drop_50pct(self):
        # baseline_total = 36 (avg 4/week), current = 2 → drop 50% → 12 pts
        db = DummyDB(values=[2, 36])
        now = datetime.now(tz=timezone.utc)

        points, drop_pct, baseline_avg = risk_service._frequency_drop_points(db, "member-1", now)

        assert points == 12
        assert 49.0 <= drop_pct <= 51.0

    def test_small_drop_25pct(self):
        # baseline_total = 36 (avg 4/week), current = 3 → drop 25% → 6 pts
        db = DummyDB(values=[3, 36])
        now = datetime.now(tz=timezone.utc)

        points, drop_pct, baseline_avg = risk_service._frequency_drop_points(db, "member-1", now)

        assert points == 6
        assert 24.0 <= drop_pct <= 26.0


# ===========================================================================
# 1.2 — Risk History
# ===========================================================================


class TestRiskHistory:
    """Tests for risk history recording in run_daily_risk_processing."""

    def test_history_saved_when_score_changes(self, monkeypatch):
        member = SimpleNamespace(
            id="m1",
            gym_id="g1",
            risk_score=30,
            risk_level="green",
            deleted_at=None,
            status="active",
        )
        new_result = risk_service.RiskResult(score=65, level=RiskLevel.YELLOW, reasons={"test": True}, days_without_checkin=10)

        monkeypatch.setattr(risk_service, "calculate_risk_score", lambda *_: new_result)
        monkeypatch.setattr(risk_service, "_run_inactivity_automations", lambda *_a, **_kw: [])
        monkeypatch.setattr(risk_service, "_create_or_update_alert", lambda *_a, **_kw: None)
        monkeypatch.setattr(risk_service, "invalidate_dashboard_cache", lambda *_: None)
        monkeypatch.setattr(risk_service, "_count_active_members_for_risk_processing", lambda *_: 1)
        monkeypatch.setattr(risk_service, "_iter_active_members_for_risk_processing", lambda *_a, **_kw: [[member]])
        monkeypatch.setattr(risk_service, "_prefetch_open_risk_alerts", lambda *_a, **_kw: {})
        monkeypatch.setattr(risk_service, "_prefetch_open_call_tasks", lambda *_a, **_kw: set())
        monkeypatch.setattr(risk_service, "_find_manager", lambda *_a, **_kw: None)

        db = MagicMock()
        db.execute.return_value.all.return_value = []

        risk_service.run_daily_risk_processing(db)

        added_objects = [call.args[0] for call in db.add.call_args_list]
        from app.models.member_risk_history import MemberRiskHistory
        history_entries = [obj for obj in added_objects if isinstance(obj, MemberRiskHistory)]
        assert len(history_entries) == 1
        assert history_entries[0].score == 65

    def test_history_not_saved_when_score_unchanged(self, monkeypatch):
        member = SimpleNamespace(
            id="m1",
            gym_id="g1",
            risk_score=65,
            risk_level="yellow",
            deleted_at=None,
            status="active",
        )
        new_result = risk_service.RiskResult(score=65, level=RiskLevel.YELLOW, reasons={}, days_without_checkin=10)

        monkeypatch.setattr(risk_service, "calculate_risk_score", lambda *_: new_result)
        monkeypatch.setattr(risk_service, "_run_inactivity_automations", lambda *_a, **_kw: [])
        monkeypatch.setattr(risk_service, "_create_or_update_alert", lambda *_a, **_kw: None)
        monkeypatch.setattr(risk_service, "invalidate_dashboard_cache", lambda *_: None)
        monkeypatch.setattr(risk_service, "_count_active_members_for_risk_processing", lambda *_: 1)
        monkeypatch.setattr(risk_service, "_iter_active_members_for_risk_processing", lambda *_a, **_kw: [[member]])
        monkeypatch.setattr(risk_service, "_prefetch_open_risk_alerts", lambda *_a, **_kw: {})
        monkeypatch.setattr(risk_service, "_prefetch_open_call_tasks", lambda *_a, **_kw: set())
        monkeypatch.setattr(risk_service, "_find_manager", lambda *_a, **_kw: None)

        db = MagicMock()
        db.execute.return_value.all.return_value = []

        risk_service.run_daily_risk_processing(db)

        added_objects = [call.args[0] for call in db.add.call_args_list]
        from app.models.member_risk_history import MemberRiskHistory
        history_entries = [obj for obj in added_objects if isinstance(obj, MemberRiskHistory)]
        assert len(history_entries) == 0

    def test_apply_risk_statement_timeout_uses_configured_limit(self, monkeypatch):
        db = MagicMock()
        monkeypatch.setattr(risk_service.settings, "risk_processing_statement_timeout_ms", 45000)

        risk_service._apply_risk_statement_timeout(db)

        assert db.execute.call_count == 1
        rendered_query = str(db.execute.call_args.args[0])
        assert "SET LOCAL statement_timeout = 45000" in rendered_query

    def test_apply_risk_statement_timeout_can_be_disabled(self, monkeypatch):
        db = MagicMock()
        monkeypatch.setattr(risk_service.settings, "risk_processing_statement_timeout_ms", 0)

        risk_service._apply_risk_statement_timeout(db)

        db.execute.assert_not_called()

    def test_iter_active_members_for_risk_processing_uses_batches(self):
        first_batch = MagicMock()
        first_batch.all.return_value = [SimpleNamespace(id="m1"), SimpleNamespace(id="m2")]
        second_batch = MagicMock()
        second_batch.all.return_value = [SimpleNamespace(id="m3")]
        db = MagicMock()
        db.scalars.side_effect = [first_batch, second_batch]

        batches = list(risk_service._iter_active_members_for_risk_processing(db, batch_size=2))

        assert len(batches) == 2
        assert len(batches[0]) == 2
        assert len(batches[1]) == 1


# ===========================================================================
# 1.3 — AI Assessment Analysis
# ===========================================================================


class TestAssessmentAIInsights:
    """Tests for generate_ai_insights with goals/constraints/fallback."""

    def test_fallback_analysis_high_body_fat(self):
        from app.services.assessment_analytics_service import _apply_fallback_analysis

        assessment = SimpleNamespace(
            body_fat_pct=Decimal("35.0"),
            bmi=Decimal("32.0"),
            resting_hr=95,
            weight_kg=Decimal("100.0"),
            ai_analysis=None,
            ai_recommendations=None,
            ai_risk_flags=None,
        )

        _apply_fallback_analysis(assessment, [])

        assert "gordura elevado" in assessment.ai_analysis
        assert "obesidade" in assessment.ai_analysis
        assert "cardiaca" in assessment.ai_analysis
        assert assessment.ai_recommendations is not None
        assert assessment.ai_risk_flags is not None

    def test_fallback_analysis_normal_values(self):
        from app.services.assessment_analytics_service import _apply_fallback_analysis

        assessment = SimpleNamespace(
            body_fat_pct=Decimal("20.0"),
            bmi=Decimal("23.0"),
            resting_hr=65,
            weight_kg=Decimal("70.0"),
            ai_analysis=None,
            ai_recommendations=None,
            ai_risk_flags=None,
        )

        _apply_fallback_analysis(assessment, [])

        assert "indisponivel" in assessment.ai_analysis
        assert assessment.ai_risk_flags is None

    def test_comprehensive_prompt_includes_goals_and_constraints(self):
        from app.services.assessment_analytics_service import _build_comprehensive_assessment_prompt

        current = SimpleNamespace(
            weight_kg=80, body_fat_pct=25, bmi=27,
            strength_score=60, flexibility_score=50, cardio_score=70,
            assessment_number=3,
        )
        goals = [
            SimpleNamespace(title="Perder peso", target_value=75, unit="kg", progress_pct=30),
        ]
        constraints = SimpleNamespace(
            medical_conditions="Hipertensao",
            injuries=None,
            medications="Losartana",
            contraindications=None,
        )

        prompt = _build_comprehensive_assessment_prompt(current, [], goals, constraints)

        assert "Perder peso" in prompt
        assert "Hipertensao" in prompt
        assert "Losartana" in prompt
        assert "analysis" in prompt
        assert "recommendations" in prompt
        assert "risk_flags" in prompt

    def test_json_parse_valid(self):
        from app.utils.claude import _parse_claude_json

        text = '```json\n{"analysis": "Aluno evoluiu", "recommendations": "Aumentar carga", "risk_flags": ""}\n```'
        result = _parse_claude_json(text)

        assert result["analysis"] == "Aluno evoluiu"
        assert result["recommendations"] == "Aumentar carga"
        assert result["risk_flags"] == ""

    def test_json_parse_invalid_returns_error(self):
        from app.utils.claude import _parse_claude_json

        with pytest.raises(ValueError):
            _parse_claude_json("This is not JSON at all")


# ===========================================================================
# 1.4 — ROI Summary
# ===========================================================================


class TestRoiSummary:
    """Tests for ROI calculation logic."""

    def test_roi_with_reengaged_members(self, monkeypatch):
        from app.services import roi_service
        from app.core import cache as cache_mod

        monkeypatch.setattr(cache_mod, "get_current_gym_id", lambda: None)

        member = SimpleNamespace(id="m1", full_name="Joao", monthly_fee=Decimal("150.00"))

        db = MagicMock()
        # First call: automated_members query
        db.execute.return_value.all.return_value = [
            SimpleNamespace(member_id="m1", first_action=datetime(2026, 2, 20, tzinfo=timezone.utc)),
        ]
        # Subsequent scalars: checkin_after, then member lookup
        db.scalar.side_effect = ["checkin-id", member]

        monkeypatch.setattr(roi_service.dashboard_cache, "get", lambda *_: None)
        monkeypatch.setattr(roi_service.dashboard_cache, "set", lambda *_a, **_kw: None)

        result = roi_service.get_roi_summary(db, period_days=30)

        assert result["total_automated"] == 1
        assert result["reengaged_count"] == 1
        assert result["preserved_revenue"] == 150.0
        assert result["reengagement_rate"] == 100.0

    def test_roi_empty_no_automations(self, monkeypatch):
        from app.services import roi_service
        from app.core import cache as cache_mod

        monkeypatch.setattr(cache_mod, "get_current_gym_id", lambda: None)

        db = MagicMock()
        db.execute.return_value.all.return_value = []

        monkeypatch.setattr(roi_service.dashboard_cache, "get", lambda *_: None)
        monkeypatch.setattr(roi_service.dashboard_cache, "set", lambda *_a, **_kw: None)

        result = roi_service.get_roi_summary(db, period_days=30)

        assert result["total_automated"] == 0
        assert result["reengaged_count"] == 0
        assert result["preserved_revenue"] == 0.0
        assert result["reengagement_rate"] == 0.0


# ===========================================================================
# 1.5 — Weekly Briefing
# ===========================================================================


class TestWeeklyBriefing:
    """Tests for weekly briefing generation."""

    def test_rule_based_briefing_format(self):
        from app.services.weekly_briefing_service import _generate_rule_based_briefing

        metrics = {
            "checkins_this_week": 120,
            "checkins_last_week": 150,
            "checkins_delta_pct": -20.0,
            "new_at_risk": 8,
            "mrr_at_risk": 2500.0,
            "total_active": 200,
        }

        briefing = _generate_rule_based_briefing(metrics)

        assert "120" in briefing
        assert "-20.0%" in briefing
        assert "reengajamento" in briefing
        assert "retencao" in briefing

    def test_rule_based_briefing_positive(self):
        from app.services.weekly_briefing_service import _generate_rule_based_briefing

        metrics = {
            "checkins_this_week": 200,
            "checkins_last_week": 180,
            "checkins_delta_pct": 11.1,
            "new_at_risk": 2,
            "mrr_at_risk": 500.0,
            "total_active": 300,
        }

        briefing = _generate_rule_based_briefing(metrics)

        assert "200" in briefing
        assert "+11.1%" in briefing
        assert "reengajamento" not in briefing

    def test_no_recipients_returns_zero(self, monkeypatch):
        from app.services import weekly_briefing_service

        monkeypatch.setattr(weekly_briefing_service, "_generate_briefing_text", lambda *_: "test briefing")

        db = MagicMock()
        db.scalars.return_value.all.return_value = []

        result = weekly_briefing_service.generate_and_send_weekly_briefing(db, "gym-1")

        assert result["briefing_sent_to"] == 0
        assert result["total_recipients"] == 0

    def test_delta_pct_calculation(self):
        from app.services.weekly_briefing_service import _delta_pct

        assert _delta_pct(100, 80) == -20.0
        assert _delta_pct(100, 120) == 20.0
        assert _delta_pct(0, 0) == 0.0
        assert _delta_pct(0, 50) == 100.0
