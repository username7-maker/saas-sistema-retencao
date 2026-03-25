from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models import MemberStatus, RiskLevel
from app.services.assessment_action_engine import build_actions, sync_assessment_tasks
from app.services.assessment_diagnosis_service import build_diagnosis
from app.services.assessment_forecast_service import build_forecast


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
ASSESSMENT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _member(**overrides):
    data = {
        "id": MEMBER_ID,
        "gym_id": GYM_ID,
        "full_name": "Aluno Evolucao",
        "status": MemberStatus.ACTIVE,
        "risk_level": RiskLevel.YELLOW,
        "risk_score": 52,
        "last_checkin_at": datetime.now(tz=timezone.utc) - timedelta(days=10),
        "deleted_at": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _assessment(**overrides):
    data = {
        "id": ASSESSMENT_ID,
        "member_id": MEMBER_ID,
        "weight_kg": Decimal("82.0"),
        "body_fat_pct": Decimal("24.0"),
        "lean_mass_kg": Decimal("38.0"),
        "strength_score": 55,
        "cardio_score": 52,
        "resting_hr": 74,
        "extra_data": {
            "goal_type": "fat_loss",
            "goal_target_value": 18,
            "target_frequency_per_week": 4,
            "adherence_score": 48,
            "sleep_quality_score": 42,
            "stress_score": 78,
            "pain_score": 18,
            "perceived_progress_score": 32,
            "exercise_execution_score": 57,
        },
    }
    data.update(overrides)
    return SimpleNamespace(**data)


class TestAssessmentForecast:
    def test_forecast_penalizes_low_consistency(self):
        member = _member()
        latest = _assessment()
        previous = _assessment(
            weight_kg=Decimal("84.0"),
            body_fat_pct=Decimal("26.0"),
            lean_mass_kg=Decimal("37.5"),
            strength_score=51,
            cardio_score=49,
        )

        forecast = build_forecast(
            member,
            latest,
            previous,
            goal_type="fat_loss",
            target_frequency_per_week=4,
            recent_weekly_checkins=1.0,
            days_since_last_checkin=10,
        )

        assert forecast["probability_60d"] < 60
        assert forecast["corrected_probability_90d"] > forecast["probability_90d"]
        assert forecast["consistency_score"] < 50
        assert forecast["likely_days_to_goal"] is not None


class TestAssessmentDiagnosis:
    def test_diagnosis_prioritizes_consistency_when_checkins_are_low(self):
        member = _member(risk_score=68)
        latest = _assessment()
        previous = _assessment(
            weight_kg=Decimal("83.0"),
            body_fat_pct=Decimal("25.0"),
            lean_mass_kg=Decimal("38.1"),
            strength_score=54,
            cardio_score=50,
        )
        forecast = build_forecast(
            member,
            latest,
            previous,
            goal_type="fat_loss",
            target_frequency_per_week=4,
            recent_weekly_checkins=0.5,
            days_since_last_checkin=13,
        )

        diagnosis = build_diagnosis(
            member,
            latest,
            previous,
            constraints=None,
            recent_weekly_checkins=0.5,
            target_frequency_per_week=4,
            days_since_last_checkin=13,
            forecast=forecast,
        )

        assert diagnosis["primary_bottleneck"] == "consistency"
        assert diagnosis["frustration_risk"] >= 60
        assert diagnosis["factors"][0]["key"] == "consistency"


class TestAssessmentActions:
    def test_actions_include_expectation_reset_for_high_frustration(self):
        member = _member()
        latest = _assessment()
        diagnosis = {
            "primary_bottleneck": "consistency",
            "frustration_risk": 79,
        }
        forecast = {
            "probability_60d": 34,
        }

        actions = build_actions(member, latest, diagnosis=diagnosis, forecast=forecast)

        keys = {action["key"] for action in actions}
        assert "consistency_recovery" in keys
        assert "expectation_reset" in keys
        assert "goal_review" in keys


class TestSyncAssessmentTasks:
    @patch("app.services.assessment_action_engine.invalidate_dashboard_cache")
    def test_sync_assessment_tasks_creates_only_missing_tasks(self, mock_cache):
        member = _member()
        latest = _assessment()
        db = MagicMock()
        db.scalar.side_effect = [None, SimpleNamespace(id=uuid.uuid4())]

        sync_assessment_tasks(
            db,
            member,
            latest,
            actions=[
                {
                    "key": "consistency_recovery",
                    "title": "Ativar frequencia de Aluno Evolucao",
                    "owner_role": "reception",
                    "priority": "high",
                    "reason": "Baixa consistencia.",
                    "due_in_days": 1,
                    "suggested_message": "Vamos ajustar sua rotina?",
                },
                {
                    "key": "expectation_reset",
                    "title": "Realinhar expectativa com Aluno Evolucao",
                    "owner_role": "manager",
                    "priority": "urgent",
                    "reason": "Risco alto de frustracao.",
                    "due_in_days": 1,
                    "suggested_message": "Quero te mostrar sua evolucao.",
                },
            ],
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        mock_cache.assert_called_once_with("tasks")
        created_task = db.add.call_args[0][0]
        assert created_task.extra_data["source"] == "assessment_intelligence"
        assert created_task.extra_data["owner_role"] == "reception"
