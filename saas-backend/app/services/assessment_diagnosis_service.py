from __future__ import annotations

from app.models import Member
from app.models.assessment import Assessment, MemberConstraints


def build_diagnosis(
    member: Member,
    latest_assessment: Assessment | None,
    previous_assessment: Assessment | None,
    constraints: MemberConstraints | None,
    *,
    recent_weekly_checkins: float,
    target_frequency_per_week: int,
    days_since_last_checkin: int | None,
    forecast: dict,
) -> dict:
    factors = _score_factors(
        latest_assessment=latest_assessment,
        previous_assessment=previous_assessment,
        constraints=constraints,
        recent_weekly_checkins=recent_weekly_checkins,
        target_frequency_per_week=target_frequency_per_week,
        days_since_last_checkin=days_since_last_checkin,
        forecast=forecast,
    )
    ordered = sorted(factors.items(), key=lambda item: item[1]["score"], reverse=True)
    primary = ordered[0]
    secondary = ordered[1]

    perceived_progress = 50
    if latest_assessment and isinstance(latest_assessment.extra_data, dict):
        perceived_progress = int(_to_float(latest_assessment.extra_data.get("perceived_progress_score")) or 50)

    frustration_risk = int(min(100, max(0, round(
        (100 - forecast["probability_60d"]) * 0.45
        + primary[1]["score"] * 0.35
        + member.risk_score * 0.25
        + max(0, 55 - perceived_progress) * 0.4
    ))))

    evolution_factors = [meta["title"] for _, meta in ordered if meta["score"] <= 35][:3]
    if not evolution_factors:
        evolution_factors = ["base fisica preservada", "aderencia minima sustentada"]

    stagnation_factors = [meta["title"] for _, meta in ordered[:3] if meta["score"] >= 35]

    explanation = (
        f"O principal gargalo hoje e {primary[1]['title'].lower()}, "
        f"porque {primary[1]['reason'].lower()}. "
        f"O fator secundario e {secondary[1]['title'].lower()}, com impacto adicional em previsibilidade de meta."
    )

    return {
        "primary_bottleneck": primary[0],
        "primary_bottleneck_label": primary[1]["title"],
        "secondary_bottleneck": secondary[0],
        "secondary_bottleneck_label": secondary[1]["title"],
        "explanation": explanation,
        "evolution_factors": evolution_factors,
        "stagnation_factors": stagnation_factors,
        "frustration_risk": frustration_risk,
        "confidence": "high" if latest_assessment and previous_assessment else "medium",
        "factors": [
            {
                "key": key,
                "label": meta["title"],
                "score": meta["score"],
                "reason": meta["reason"],
            }
            for key, meta in ordered
        ],
    }


def _score_factors(
    *,
    latest_assessment: Assessment | None,
    previous_assessment: Assessment | None,
    constraints: MemberConstraints | None,
    recent_weekly_checkins: float,
    target_frequency_per_week: int,
    days_since_last_checkin: int | None,
    forecast: dict,
) -> dict[str, dict]:
    extra = latest_assessment.extra_data if latest_assessment and isinstance(latest_assessment.extra_data, dict) else {}
    consistency_gap = max((target_frequency_per_week or 3) - recent_weekly_checkins, 0)
    sleep_quality = _to_float(extra.get("sleep_quality_score")) or 60
    stress_score = _to_float(extra.get("stress_score")) or 50
    pain_score = _to_float(extra.get("pain_score")) or 0
    adherence = _to_float(extra.get("adherence_score")) or _to_float(extra.get("self_reported_adherence_score")) or 55
    perceived_progress = _to_float(extra.get("perceived_progress_score")) or 50
    execution_score = _to_float(extra.get("exercise_execution_score")) or 55

    expectation_gap = 100 - forecast["corrected_probability_90d"] if forecast["corrected_probability_90d"] < 70 else 20
    if perceived_progress <= 35:
        expectation_gap += 15

    return {
        "consistency": {
            "title": "Consistencia",
            "score": min(100, round((consistency_gap * 22) + (days_since_last_checkin or 0) * 1.4)),
            "reason": f"o aluno esta treinando em media {recent_weekly_checkins:.1f}x/semana para uma meta que pede {target_frequency_per_week}x/semana",
        },
        "recovery": {
            "title": "Recuperacao",
            "score": min(100, round(max(0, 70 - sleep_quality) + max(0, stress_score - 55) * 0.7)),
            "reason": "sono e estresse estao reduzindo a capacidade de consolidar adaptacao",
        },
        "adherence": {
            "title": "Aderencia",
            "score": min(100, round(max(0, 70 - adherence) + max(0, 60 - perceived_progress) * 0.5)),
            "reason": "a percepcao do aluno e a aderencia autorreportada estao abaixo do ideal",
        },
        "execution": {
            "title": "Execucao",
            "score": min(100, round(max(0, 68 - execution_score))),
            "reason": "a execucao relatada ainda nao sustenta o ganho esperado com seguranca",
        },
        "restriction": {
            "title": "Restricoes",
            "score": min(100, round(pain_score * 0.9 + (18 if constraints and (constraints.injuries or constraints.contraindications) else 0))),
            "reason": "dor, restricao ou historico clinico estao limitando a progressao",
        },
        "expectation": {
            "title": "Expectativa",
            "score": min(100, round(expectation_gap)),
            "reason": "a expectativa de resultado esta descolada da chance real de entrega no prazo atual",
        },
    }


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
