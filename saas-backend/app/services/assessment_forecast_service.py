from __future__ import annotations

from decimal import Decimal

from app.models import Member
from app.models.assessment import Assessment


def build_forecast(
    member: Member,
    latest_assessment: Assessment | None,
    previous_assessment: Assessment | None,
    *,
    goal_type: str,
    target_frequency_per_week: int,
    recent_weekly_checkins: float,
    days_since_last_checkin: int | None,
) -> dict:
    consistency_score = _consistency_score(target_frequency_per_week, recent_weekly_checkins, days_since_last_checkin)
    progress_score = _progress_alignment_score(goal_type, latest_assessment, previous_assessment)
    adherence_score = _adherence_score(latest_assessment)
    recovery_score = _recovery_score(latest_assessment)

    weighted_score = (
        (consistency_score * 0.35)
        + (progress_score * 0.30)
        + (adherence_score * 0.20)
        + (recovery_score * 0.15)
    )
    current_probability = int(round(_clamp(weighted_score, 5, 95)))
    corrected_probability = int(round(_clamp(current_probability + 22, 10, 98)))

    probability_30 = int(round(_clamp(current_probability - 8, 5, 95)))
    probability_60 = current_probability
    probability_90 = int(round(_clamp(current_probability + 10, 5, 98)))

    likely_days_to_goal = _estimate_days_to_goal(goal_type, latest_assessment, previous_assessment, probability_90)

    blockers = []
    if consistency_score < 50:
        blockers.append("consistencia de frequencia")
    if adherence_score < 50:
        blockers.append("aderencia percebida")
    if recovery_score < 50:
        blockers.append("recuperacao")
    if progress_score < 50:
        blockers.append("sinais de evolucao abaixo do esperado")

    current_summary = (
        "Cenario atual: "
        f"{probability_60}% de chance de atingir a meta mantendo o comportamento atual."
    )
    corrected_summary = (
        "Cenario corrigido: "
        f"{corrected_probability}% de chance se a academia corrigir {', '.join(blockers[:2]) or 'a aderencia operacional'}."
    )

    return {
        "goal_type": goal_type,
        "probability_30d": probability_30,
        "probability_60d": probability_60,
        "probability_90d": probability_90,
        "corrected_probability_90d": corrected_probability,
        "likely_days_to_goal": likely_days_to_goal,
        "current_summary": current_summary,
        "corrected_summary": corrected_summary,
        "consistency_score": int(round(consistency_score)),
        "progress_score": int(round(progress_score)),
        "adherence_score": int(round(adherence_score)),
        "recovery_score": int(round(recovery_score)),
        "overall_score": current_probability,
        "blocked": current_probability < 45,
        "confidence": "high" if latest_assessment and previous_assessment else "medium",
    }


def _consistency_score(target_frequency_per_week: int, recent_weekly_checkins: float, days_since_last_checkin: int | None) -> float:
    if target_frequency_per_week <= 0:
        target_frequency_per_week = 3
    ratio = recent_weekly_checkins / float(target_frequency_per_week)
    score = _clamp(ratio * 100, 0, 100)
    if days_since_last_checkin is not None:
        if days_since_last_checkin >= 14:
            score -= 30
        elif days_since_last_checkin >= 7:
            score -= 15
    return _clamp(score, 0, 100)


def _progress_alignment_score(goal_type: str, latest_assessment: Assessment | None, previous_assessment: Assessment | None) -> float:
    if not latest_assessment:
        return 45
    if not previous_assessment:
        return 55

    body_fat_delta = _delta(previous_assessment.body_fat_pct, latest_assessment.body_fat_pct)
    weight_delta = _delta(previous_assessment.weight_kg, latest_assessment.weight_kg)
    lean_mass_delta = _delta(previous_assessment.lean_mass_kg, latest_assessment.lean_mass_kg)
    strength_delta = _delta(previous_assessment.strength_score, latest_assessment.strength_score)
    cardio_delta = _delta(previous_assessment.cardio_score, latest_assessment.cardio_score)

    score = 50.0
    if goal_type == "fat_loss":
        if body_fat_delta is not None:
            score += 18 if body_fat_delta < 0 else -18
        elif weight_delta is not None:
            score += 12 if weight_delta < 0 else -12
        if lean_mass_delta is not None and lean_mass_delta < 0:
            score -= 8
    elif goal_type == "muscle_gain":
        if lean_mass_delta is not None:
            score += 18 if lean_mass_delta > 0 else -18
        if strength_delta is not None:
            score += 12 if strength_delta > 0 else -12
    elif goal_type == "performance":
        if strength_delta is not None:
            score += 14 if strength_delta > 0 else -14
        if cardio_delta is not None:
            score += 14 if cardio_delta > 0 else -14
    else:
        positives = [delta for delta in (strength_delta, cardio_delta, lean_mass_delta) if delta is not None and delta > 0]
        negatives = [delta for delta in (body_fat_delta, weight_delta) if delta is not None and delta > 0]
        score += min(len(positives) * 8, 20)
        score -= min(len(negatives) * 6, 18)

    return _clamp(score, 0, 100)


def _adherence_score(latest_assessment: Assessment | None) -> float:
    if not latest_assessment:
        return 50
    extra = latest_assessment.extra_data if isinstance(latest_assessment.extra_data, dict) else {}
    candidates = [
        _to_float(extra.get("adherence_score")),
        _to_float(extra.get("self_reported_adherence_score")),
        _to_float(extra.get("nutrition_adherence_score")),
    ]
    valid = [value for value in candidates if value is not None]
    if valid:
        return _clamp(sum(valid) / len(valid), 0, 100)
    return 55


def _recovery_score(latest_assessment: Assessment | None) -> float:
    if not latest_assessment:
        return 50
    extra = latest_assessment.extra_data if isinstance(latest_assessment.extra_data, dict) else {}

    sleep_quality = _to_float(extra.get("sleep_quality_score")) or 60
    stress_score = _to_float(extra.get("stress_score"))
    pain_score = _to_float(extra.get("pain_score"))

    score = sleep_quality
    if stress_score is not None:
        score -= max(stress_score - 50, 0) * 0.45
    if pain_score is not None:
        score -= pain_score * 0.35
    if latest_assessment.resting_hr and latest_assessment.resting_hr >= 90:
        score -= 10
    return _clamp(score, 0, 100)


def _estimate_days_to_goal(
    goal_type: str,
    latest_assessment: Assessment | None,
    previous_assessment: Assessment | None,
    probability_90: int,
) -> int | None:
    if not latest_assessment:
        return None
    extra = latest_assessment.extra_data if isinstance(latest_assessment.extra_data, dict) else {}
    target_value = _to_float(extra.get("goal_target_value"))
    if target_value is None or previous_assessment is None:
        return 90 if probability_90 >= 70 else 150

    if goal_type == "fat_loss":
        current_value = _to_float(latest_assessment.body_fat_pct) or _to_float(latest_assessment.weight_kg)
        previous_value = _to_float(previous_assessment.body_fat_pct) or _to_float(previous_assessment.weight_kg)
    elif goal_type == "muscle_gain":
        current_value = _to_float(latest_assessment.lean_mass_kg) or _to_float(latest_assessment.weight_kg)
        previous_value = _to_float(previous_assessment.lean_mass_kg) or _to_float(previous_assessment.weight_kg)
    else:
        current_value = _to_float(latest_assessment.strength_score) or _to_float(latest_assessment.cardio_score)
        previous_value = _to_float(previous_assessment.strength_score) or _to_float(previous_assessment.cardio_score)

    if current_value is None or previous_value is None:
        return 90 if probability_90 >= 70 else 150

    velocity = abs(current_value - previous_value)
    if velocity <= 0.01:
        return 180 if probability_90 < 70 else 120

    distance = abs(target_value - current_value)
    estimated_cycles = distance / velocity
    return int(_clamp(round(estimated_cycles * 30), 30, 365))


def _delta(before: Decimal | int | None, after: Decimal | int | None) -> float | None:
    if before is None or after is None:
        return None
    return float(after) - float(before)


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
