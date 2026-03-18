from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import anthropic
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.circuit_breaker import claude_circuit_breaker
from app.core.config import settings
from app.models import Member
from app.models.assessment import MemberConstraints, MemberGoal
from app.models.body_composition import BodyCompositionEvaluation
from app.utils.claude import _parse_claude_json


logger = logging.getLogger(__name__)

_FIELD_LABELS = {
    "weight_kg": "peso",
    "body_fat_kg": "gordura corporal em kg",
    "body_fat_percent": "percentual de gordura",
    "waist_hip_ratio": "relacao cintura-quadril",
    "fat_free_mass_kg": "massa livre de gordura",
    "muscle_mass_kg": "massa muscular",
    "skeletal_muscle_kg": "musculo esqueletico",
    "visceral_fat_level": "gordura visceral",
    "bmi": "IMC",
    "health_score": "health score",
}


def generate_body_composition_ai(
    db: Session,
    *,
    member: Member,
    evaluation: BodyCompositionEvaluation,
) -> dict[str, Any]:
    previous_evaluation = db.scalar(
        select(BodyCompositionEvaluation)
        .where(
            BodyCompositionEvaluation.member_id == member.id,
            BodyCompositionEvaluation.id != evaluation.id,
        )
        .order_by(desc(BodyCompositionEvaluation.evaluation_date), desc(BodyCompositionEvaluation.created_at))
        .limit(1)
    )
    constraints = db.scalar(
        select(MemberConstraints)
        .where(MemberConstraints.member_id == member.id, MemberConstraints.deleted_at.is_(None))
        .order_by(desc(MemberConstraints.created_at))
        .limit(1)
    )
    goals = list(
        db.scalars(
            select(MemberGoal)
            .where(MemberGoal.member_id == member.id, MemberGoal.deleted_at.is_(None))
            .order_by(MemberGoal.achieved.asc(), MemberGoal.target_date.asc().nullslast(), MemberGoal.created_at.desc())
        ).all()
    )

    if settings.claude_api_key and not claude_circuit_breaker.is_open():
        try:
            result = _generate_with_claude(
                member=member,
                evaluation=evaluation,
                previous_evaluation=previous_evaluation,
                constraints=constraints,
                goals=goals,
            )
            claude_circuit_breaker.record_success()
            return result
        except Exception:
            claude_circuit_breaker.record_failure()
            logger.exception("Falha ao gerar interpretacao de bioimpedancia com Claude. Usando fallback.")

    return _generate_deterministic_fallback(
        member=member,
        evaluation=evaluation,
        previous_evaluation=previous_evaluation,
        constraints=constraints,
        goals=goals,
    )


def _generate_with_claude(
    *,
    member: Member,
    evaluation: BodyCompositionEvaluation,
    previous_evaluation: BodyCompositionEvaluation | None,
    constraints: MemberConstraints | None,
    goals: list[MemberGoal],
) -> dict[str, Any]:
    range_summary = _summarize_ranges(evaluation)
    goals_summary = ", ".join(goal.title for goal in goals[:3]) if goals else "Sem metas ativas registradas"
    constraints_summary = _summarize_constraints(constraints)
    previous_summary = _summarize_previous(previous_evaluation)
    prompt = (
        "Voce e um assistente de apoio operacional para professores de academia.\n"
        "Analise uma bioimpedancia e retorne JSON com campos: coach_summary, member_friendly_summary, "
        "risk_flags, training_focus.\n"
        "Regras obrigatorias:\n"
        "- nao diagnosticar doenca\n"
        "- nao sugerir condicao medica\n"
        "- nao sugerir medicamento, suplemento clinico ou tratamento\n"
        "- nao prescrever treino fechado\n"
        "- nao sugerir exercicios especificos como prescricao pronta\n"
        "- nao substituir avaliacao profissional presencial\n"
        "- produzir apenas interpretacao corporal resumida, alertas objetivos, foco inicial sugerido e direcao geral de acompanhamento\n"
        "- responder em portugues do Brasil\n"
        "- training_focus deve ter primary_goal, secondary_goal, suggested_focuses, cautions\n"
        f"Aluno: {member.full_name}\n"
        f"Plano: {member.plan_name}\n"
        f"Metas: {goals_summary}\n"
        f"Restricoes: {constraints_summary}\n"
        f"Contexto previo: {previous_summary}\n"
        f"Valores atuais: {_serialize_measurements(evaluation)}\n"
        f"Faixas: {range_summary}\n"
    )
    client = anthropic.Anthropic(api_key=settings.claude_api_key)
    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=min(max(settings.claude_max_tokens, 600), 700),
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    parsed = _parse_claude_json(response.content[0].text.strip())
    return _normalize_ai_payload(parsed)


def _generate_deterministic_fallback(
    *,
    member: Member,
    evaluation: BodyCompositionEvaluation,
    previous_evaluation: BodyCompositionEvaluation | None,
    constraints: MemberConstraints | None,
    goals: list[MemberGoal],
) -> dict[str, Any]:
    classifications = _classify_fields(evaluation)
    high_flags = [label for label, status in classifications if status == "acima"]
    low_flags = [label for label, status in classifications if status == "abaixo"]

    risk_flags: list[str] = []
    for label in high_flags[:3]:
        risk_flags.append(f"{label} acima da faixa")
    for label in low_flags[:2]:
        risk_flags.append(f"{label} abaixo da faixa")
    if not risk_flags:
        risk_flags.append("medidas principais dentro da faixa impressa")

    primary_goal = _resolve_primary_goal(high_flags, low_flags, evaluation)
    secondary_goal = _resolve_secondary_goal(primary_goal, high_flags, low_flags)
    suggested_focuses = _build_focuses(primary_goal, secondary_goal, previous_evaluation)

    coach_parts = [
        _compose_body_summary(high_flags, low_flags),
        f"Meta principal sugerida: {primary_goal.replace('_', ' ')}.",
    ]
    if previous_evaluation:
        delta_text = _compare_with_previous(evaluation, previous_evaluation)
        if delta_text:
            coach_parts.append(delta_text)
    if constraints:
        coach_parts.append("Validar foco com restricoes e contexto do professor responsavel.")
    elif goals:
        coach_parts.append("Cruzar o foco com as metas registradas antes de ajustar a direcao do acompanhamento.")
    coach_summary = " ".join(part for part in coach_parts if part).strip()[:500]

    member_summary = (
        "O exame ajuda a orientar o acompanhamento corporal inicial, sem substituir avaliacao presencial. "
        f"No momento, a direcao sugerida e {primary_goal.replace('_', ' ')} com monitoramento das medidas-chave."
    )[:500]

    return {
        "coach_summary": coach_summary,
        "member_friendly_summary": member_summary,
        "risk_flags": risk_flags[:4],
        "training_focus": {
            "primary_goal": primary_goal,
            "secondary_goal": secondary_goal,
            "suggested_focuses": suggested_focuses,
            "cautions": [
                "apoio ao professor, nao substituir avaliacao profissional presencial",
                "nao usar como diagnostico clinico ou prescricao automatica fechada",
            ],
        },
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def _normalize_ai_payload(payload: dict[str, Any]) -> dict[str, Any]:
    training_focus = payload.get("training_focus")
    normalized_focus = training_focus if isinstance(training_focus, dict) else {}
    return {
        "coach_summary": str(payload.get("coach_summary") or "")[:500],
        "member_friendly_summary": str(payload.get("member_friendly_summary") or "")[:500],
        "risk_flags": [str(item) for item in payload.get("risk_flags") or []][:5],
        "training_focus": {
            "primary_goal": str(normalized_focus.get("primary_goal") or "acompanhamento_geral"),
            "secondary_goal": str(normalized_focus.get("secondary_goal") or "preservacao_de_massa_magra"),
            "suggested_focuses": [str(item) for item in normalized_focus.get("suggested_focuses") or []][:5],
            "cautions": [str(item) for item in normalized_focus.get("cautions") or []][:4]
            or [
                "apoio ao professor, nao substituir avaliacao profissional presencial",
                "nao usar como diagnostico clinico ou prescricao automatica fechada",
            ],
        },
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def _serialize_measurements(evaluation: BodyCompositionEvaluation) -> dict[str, float | int]:
    payload: dict[str, float | int] = {}
    for field in _FIELD_LABELS:
        value = getattr(evaluation, field, None)
        numeric = _to_float(value)
        if numeric is None:
            continue
        payload[field] = int(numeric) if field in {"physical_age", "health_score"} else round(numeric, 2)
    return payload


def _classify_fields(evaluation: BodyCompositionEvaluation) -> list[tuple[str, str]]:
    measured_ranges = evaluation.measured_ranges_json or {}
    results: list[tuple[str, str]] = []
    for field_name, label in _FIELD_LABELS.items():
        current = _to_float(getattr(evaluation, field_name, None))
        if current is None:
            continue
        range_payload = measured_ranges.get(field_name)
        if not isinstance(range_payload, dict):
            continue
        minimum = _to_float(range_payload.get("min"))
        maximum = _to_float(range_payload.get("max"))
        if minimum is not None and current < minimum:
            results.append((label, "abaixo"))
            continue
        if maximum is not None and current > maximum:
            results.append((label, "acima"))
            continue
        if minimum is not None or maximum is not None:
            results.append((label, "dentro"))
    return results


def _resolve_primary_goal(high_flags: list[str], low_flags: list[str], evaluation: BodyCompositionEvaluation) -> str:
    if any(label in {"gordura corporal em kg", "percentual de gordura", "gordura visceral", "peso", "IMC"} for label in high_flags):
        return "reducao_de_gordura"
    if any(label in {"massa livre de gordura", "massa muscular", "musculo esqueletico"} for label in low_flags):
        return "ganho_de_massa"
    if any(label in {"gordura visceral", "IMC"} for label in high_flags):
        return "melhora_metabolica"
    if _to_float(getattr(evaluation, "health_score", None)) is not None and _to_float(getattr(evaluation, "health_score", None)) < 70:
        return "melhora_metabolica"
    return "acompanhamento_geral"


def _resolve_secondary_goal(primary_goal: str, high_flags: list[str], low_flags: list[str]) -> str:
    if primary_goal == "reducao_de_gordura" and any(label in {"massa livre de gordura", "massa muscular", "musculo esqueletico"} for label in low_flags):
        return "preservacao_de_massa_magra"
    if primary_goal == "ganho_de_massa" and any(label in {"percentual de gordura", "gordura corporal em kg"} for label in high_flags):
        return "controle_de_gordura"
    if primary_goal == "melhora_metabolica":
        return "preservacao_de_massa_magra"
    return "preservacao_de_massa_magra"


def _build_focuses(primary_goal: str, secondary_goal: str, previous_evaluation: BodyCompositionEvaluation | None) -> list[str]:
    focuses = []
    if primary_goal == "reducao_de_gordura":
        focuses.extend([
            "acompanhar composicao corporal com progressao consistente",
            "elevar gasto calorico semanal com supervisao do professor",
        ])
    elif primary_goal == "ganho_de_massa":
        focuses.extend([
            "estimular progressao de carga e consistencia de rotina",
            "monitorar preservacao da composicao corporal ao longo das reavaliacoes",
        ])
    elif primary_goal == "melhora_metabolica":
        focuses.extend([
            "priorizar consistencia de treino e acompanhamento de marcadores corporais",
            "reavaliar composicao e aderencia em janela curta",
        ])
    else:
        focuses.append("manter acompanhamento regular e revisar objetivos com o professor")

    if secondary_goal == "preservacao_de_massa_magra":
        focuses.append("preservar massa magra durante o acompanhamento")
    if previous_evaluation:
        focuses.append("comparar resposta corporal com a avaliacao anterior antes de ajustar a direcao")
    return focuses[:4]


def _compare_with_previous(current: BodyCompositionEvaluation, previous: BodyCompositionEvaluation) -> str:
    current_fat = _to_float(current.body_fat_percent)
    previous_fat = _to_float(previous.body_fat_percent)
    current_weight = _to_float(current.weight_kg)
    previous_weight = _to_float(previous.weight_kg)
    parts: list[str] = []
    if current_fat is not None and previous_fat is not None:
        delta = round(current_fat - previous_fat, 2)
        if delta > 0:
            parts.append(f"Percentual de gordura subiu {delta} ponto(s).")
        elif delta < 0:
            parts.append(f"Percentual de gordura caiu {abs(delta)} ponto(s).")
    if current_weight is not None and previous_weight is not None:
        delta = round(current_weight - previous_weight, 2)
        if delta > 0:
            parts.append(f"Peso total subiu {delta} kg.")
        elif delta < 0:
            parts.append(f"Peso total caiu {abs(delta)} kg.")
    return " ".join(parts[:2])


def _compose_body_summary(high_flags: list[str], low_flags: list[str]) -> str:
    if high_flags:
        return f"Leitura corporal com destaque para {', '.join(high_flags[:2])} acima da faixa."
    if low_flags:
        return f"Leitura corporal com destaque para {', '.join(low_flags[:2])} abaixo da faixa."
    return "Leitura corporal sem desvios impressos relevantes nas principais medidas comparaveis."


def _summarize_ranges(evaluation: BodyCompositionEvaluation) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    measured_ranges = evaluation.measured_ranges_json or {}
    if not isinstance(measured_ranges, dict):
        return result
    for key, value in measured_ranges.items():
        if not isinstance(value, dict):
            continue
        minimum = _to_float(value.get("min"))
        maximum = _to_float(value.get("max"))
        if minimum is None and maximum is None:
            continue
        result[key] = {}
        if minimum is not None:
            result[key]["min"] = minimum
        if maximum is not None:
            result[key]["max"] = maximum
    return result


def _summarize_constraints(constraints: MemberConstraints | None) -> str:
    if not constraints:
        return "Sem restricoes registradas"
    parts = []
    if constraints.medical_conditions:
        parts.append(f"condicoes: {constraints.medical_conditions}")
    if constraints.injuries:
        parts.append(f"lesoes: {constraints.injuries}")
    if constraints.contraindications:
        parts.append(f"contraindicacoes: {constraints.contraindications}")
    return "; ".join(parts) if parts else "Sem restricoes registradas"


def _summarize_previous(previous_evaluation: BodyCompositionEvaluation | None) -> str:
    if not previous_evaluation:
        return "Sem bioimpedancia anterior registrada"
    return (
        f"Ultima bioimpedancia em {previous_evaluation.evaluation_date.isoformat()} com peso "
        f"{_to_float(previous_evaluation.weight_kg) or '-'} kg e gordura "
        f"{_to_float(previous_evaluation.body_fat_percent) or '-'}%."
    )


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
