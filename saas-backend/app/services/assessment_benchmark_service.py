from __future__ import annotations

from collections import OrderedDict

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Member
from app.models.assessment import Assessment


def build_benchmark(
    db: Session,
    member: Member,
    latest_assessment: Assessment | None,
    *,
    goal_type: str,
    overall_score: int,
) -> dict:
    latest_by_member: OrderedDict[str, Assessment] = OrderedDict()
    candidate_assessments = list(
        db.scalars(
            select(Assessment)
            .where(Assessment.deleted_at.is_(None))
            .order_by(desc(Assessment.assessment_date))
            .limit(250)
        ).all()
    )

    for assessment in candidate_assessments:
        member_key = str(assessment.member_id)
        if member_key not in latest_by_member:
            latest_by_member[member_key] = assessment

    filtered = [
        item for item in latest_by_member.values() if _extract_goal_type(item) == goal_type
    ]
    if len(filtered) < 8:
        filtered = list(latest_by_member.values())[:50]

    cohort_scores = sorted(_cohort_score(item) for item in filtered)
    percentile = _percentile_rank(overall_score, cohort_scores)

    if percentile < 35:
        status = "below_expected"
        explanation = "A evolucao do aluno esta abaixo da curva esperada para o cohort semelhante."
    elif percentile < 70:
        status = "on_track"
        explanation = "A evolucao do aluno esta dentro da faixa esperada para perfis semelhantes."
    else:
        status = "ahead"
        explanation = "A evolucao do aluno esta acima do esperado para perfis semelhantes."

    cohort_label = (
        f"Cohort {goal_type.replace('_', ' ')}"
        if goal_type != "general"
        else "Cohort geral de avaliacao"
    )

    return {
        "cohort_label": cohort_label,
        "sample_size": len(cohort_scores),
        "percentile": percentile,
        "expected_curve_status": status,
        "explanation": explanation,
        "position_label": _position_label(percentile),
        "peer_average_score": round(sum(cohort_scores) / len(cohort_scores), 1) if cohort_scores else None,
    }


def _cohort_score(assessment: Assessment) -> int:
    extra = assessment.extra_data if isinstance(assessment.extra_data, dict) else {}
    adherence = _to_float(extra.get("adherence_score")) or 55
    perceived = _to_float(extra.get("perceived_progress_score")) or 50
    strength = float(assessment.strength_score or 50)
    cardio = float(assessment.cardio_score or 50)
    return int(round(min(100, max(0, (adherence * 0.35) + (perceived * 0.25) + (strength * 0.2) + (cardio * 0.2)))))


def _percentile_rank(value: int, ordered_scores: list[int]) -> int:
    if not ordered_scores:
        return 50
    below_or_equal = sum(1 for score in ordered_scores if score <= value)
    return int(round((below_or_equal / len(ordered_scores)) * 100))


def _position_label(percentile: int) -> str:
    if percentile < 35:
        return "Abaixo do esperado"
    if percentile < 70:
        return "Dentro da curva"
    return "Acima do esperado"


def _extract_goal_type(assessment: Assessment) -> str:
    extra = assessment.extra_data if isinstance(assessment.extra_data, dict) else {}
    raw = str(extra.get("goal_type") or extra.get("main_goal") or "general").strip().lower()
    if raw in {"emagrecimento", "perda de gordura", "fat_loss", "fat loss"}:
        return "fat_loss"
    if raw in {"hipertrofia", "ganho de massa", "muscle_gain", "muscle gain"}:
        return "muscle_gain"
    if raw in {"performance", "condicionamento", "athletic"}:
        return "performance"
    return "general"


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
