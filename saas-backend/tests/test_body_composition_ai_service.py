"""Tests for body composition AI support service."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _evaluation(**overrides):
    payload = {
        "id": "eval-1",
        "evaluation_date": date(2026, 3, 17),
        "weight_kg": 84.5,
        "body_fat_kg": 19.46,
        "body_fat_percent": 23.0,
        "fat_free_mass_kg": 65.0,
        "muscle_mass_kg": 37.2,
        "skeletal_muscle_kg": 35.6,
        "visceral_fat_level": 9.1,
        "bmi": 26.7,
        "health_score": 62,
        "measured_ranges_json": {
            "weight_kg": {"min": 61.7, "max": 75.5},
            "body_fat_kg": {"min": 7.55, "max": 14.41},
            "body_fat_percent": {"min": 11.0, "max": 21.0},
            "visceral_fat_level": {"min": 1.0, "max": 5.0},
            "skeletal_muscle_kg": {"min": 21.3, "max": 35.7},
            "health_score": {"min": 70, "max": 100},
        },
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_generate_body_composition_ai_fallback_is_safe_and_structured():
    db = MagicMock()
    previous = _evaluation(id="eval-0", evaluation_date=date(2026, 2, 17), body_fat_percent=24.0, weight_kg=86.0)
    constraints = SimpleNamespace(medical_conditions=None, injuries=None, contraindications=None)
    goals_result = MagicMock()
    goals_result.all.return_value = [SimpleNamespace(title="Reducao de gordura", achieved=False, target_date=None, created_at=None)]
    db.scalar.side_effect = [previous, constraints]
    db.scalars.return_value = goals_result

    member = SimpleNamespace(id="member-1", full_name="Aluno Teste", plan_name="Plano anual")

    with patch("app.services.body_composition_ai_service.settings.claude_api_key", ""), patch(
        "app.services.body_composition_ai_service.claude_circuit_breaker.is_open",
        return_value=False,
    ):
        from app.services.body_composition_ai_service import generate_body_composition_ai

        result = generate_body_composition_ai(db, member=member, evaluation=_evaluation())

    assert result["training_focus"]["primary_goal"] == "reducao_de_gordura"
    assert "percentual de gordura acima da faixa" in result["risk_flags"]
    assert "gordura corporal em kg acima da faixa" in result["risk_flags"]
    assert "diagnostico" not in result["coach_summary"].lower()
    assert "doenca" not in result["coach_summary"].lower()
    assert "medicamento" not in result["coach_summary"].lower()
    assert "tratamento" not in result["coach_summary"].lower()
    assert "exercicio especifico" not in result["coach_summary"].lower()
    assert "avaliacao presencial" in result["member_friendly_summary"].lower()
    assert result["training_focus"]["cautions"]
