from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import anthropic
from openai import OpenAI
from pydantic import BaseModel, Field
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
_PRIMARY_GOAL_ALLOWED = {
    "reducao_de_gordura",
    "ganho_de_massa",
    "melhora_metabolica",
    "acompanhamento_geral",
}
_SECONDARY_GOAL_ALLOWED = {
    "preservacao_de_massa_magra",
    "controle_de_gordura",
    "melhora_metabolica",
    "acompanhamento_geral",
}
_COACH_SUMMARY_MAX_LENGTH = 1200
_MEMBER_SUMMARY_MAX_LENGTH = 900
_TECHNICAL_MEMBER_TERMS = (
    "gordura visceral",
    "relacao cintura-quadril",
    "indice de massa corporal",
    "massa muscular esqueletica",
    "percentual de gordura",
    "imc",
)


class _OpenAITrainingFocus(BaseModel):
    primary_goal: str = "acompanhamento_geral"
    secondary_goal: str = "preservacao_de_massa_magra"
    suggested_focuses: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)


class _OpenAIBodyCompositionNarrative(BaseModel):
    coach_summary: str = ""
    member_friendly_summary: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    training_focus: _OpenAITrainingFocus = Field(default_factory=_OpenAITrainingFocus)


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

    provider = _resolve_body_composition_ai_provider()

    provider_available = bool(provider and (provider != "claude" or not claude_circuit_breaker.is_open()))

    if provider_available:
        try:
            if provider == "openai":
                result = _generate_with_openai(
                    member=member,
                    evaluation=evaluation,
                    previous_evaluation=previous_evaluation,
                    constraints=constraints,
                    goals=goals,
                )
            else:
                result = _generate_with_claude(
                    member=member,
                    evaluation=evaluation,
                    previous_evaluation=previous_evaluation,
                    constraints=constraints,
                    goals=goals,
                )
            if provider == "claude":
                claude_circuit_breaker.record_success()
            return result
        except Exception:
            if provider == "claude":
                claude_circuit_breaker.record_failure()
            logger.exception(
                "Falha ao gerar interpretacao de bioimpedancia com provedor %s. Usando fallback.",
                provider,
            )

    return _generate_deterministic_fallback(
        member=member,
        evaluation=evaluation,
        previous_evaluation=previous_evaluation,
        constraints=constraints,
        goals=goals,
    )


def _resolve_body_composition_ai_provider() -> str | None:
    if settings.openai_api_key:
        return "openai"
    if settings.claude_api_key:
        return "claude"
    return None


def _create_openai_client() -> OpenAI:
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )


def _generate_with_openai(
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
    classification_summary = _summarize_classifications(evaluation)
    prompt = (
        "Voce e um assistente de apoio operacional para professores de academia.\n"
        "Analise uma bioimpedancia e retorne campos estruturados com resumo para coach e resumo amigavel para o aluno.\n"
        "Regras obrigatorias:\n"
        "- nao diagnosticar doenca\n"
        "- nao sugerir condicao medica\n"
        "- nao sugerir medicamento, suplemento clinico ou tratamento\n"
        "- nao prescrever treino fechado\n"
        "- nao sugerir exercicios especificos como prescricao pronta\n"
        "- nao substituir avaliacao profissional presencial\n"
        "- produzir apenas interpretacao corporal resumida, alertas objetivos, foco inicial sugerido e direcao geral de acompanhamento\n"
        "- se uma medida estiver acima ou abaixo da faixa impressa, isso deve aparecer fielmente no resumo; nunca diga que esta dentro da faixa quando nao estiver\n"
        "- o campo member_friendly_summary deve soar como uma conversa do professor com o aluno depois do exame\n"
        "- use linguagem acolhedora, simples, humana e motivadora\n"
        "- evite jargao tecnico; se precisar citar um conceito tecnico, explique em palavras simples\n"
        "- comece destacando um bom ponto de partida real antes de falar do foco de melhora\n"
        "- termine convidando para acompanhamento continuo nas proximas semanas\n"
        "- no maximo 4 frases curtas, sem lista\n"
        "- training_focus.primary_goal deve ser um de: reducao_de_gordura, ganho_de_massa, melhora_metabolica, acompanhamento_geral\n"
        "- training_focus.secondary_goal deve ser um de: preservacao_de_massa_magra, controle_de_gordura, melhora_metabolica, acompanhamento_geral\n"
        "- responder em portugues do Brasil\n"
        f"Aluno: {member.full_name}\n"
        f"Plano: {member.plan_name}\n"
        f"Metas: {goals_summary}\n"
        f"Restricoes: {constraints_summary}\n"
        f"Contexto previo: {previous_summary}\n"
        f"Valores atuais: {_serialize_measurements(evaluation)}\n"
        f"Faixas: {range_summary}\n"
        f"Classificacao objetiva: {classification_summary}\n"
    )
    client = _create_openai_client()
    response = client.responses.parse(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Gere uma leitura segura e operacional de bioimpedancia para academias. "
                            "Seja conservador, claro e sem linguagem clinica indevida."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        ],
        text_format=_OpenAIBodyCompositionNarrative,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("OpenAI nao retornou payload estruturado para a leitura de bioimpedancia.")
    return _normalize_ai_payload(parsed.model_dump())


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
    classification_summary = _summarize_classifications(evaluation)
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
        "- se uma medida estiver acima ou abaixo da faixa impressa, isso deve aparecer fielmente no resumo; nunca diga que esta dentro da faixa quando nao estiver\n"
        "- member_friendly_summary deve soar como uma conversa do professor com o aluno depois do exame\n"
        "- use linguagem acolhedora, simples, humana e motivadora\n"
        "- evite jargao tecnico; se precisar citar um conceito tecnico, explique em palavras simples\n"
        "- comece destacando um bom ponto de partida real antes de falar do foco de melhora\n"
        "- termine convidando para acompanhamento continuo nas proximas semanas\n"
        "- no maximo 4 frases curtas, sem lista\n"
        "- training_focus.primary_goal deve ser um de: reducao_de_gordura, ganho_de_massa, melhora_metabolica, acompanhamento_geral\n"
        "- training_focus.secondary_goal deve ser um de: preservacao_de_massa_magra, controle_de_gordura, melhora_metabolica, acompanhamento_geral\n"
        f"Aluno: {member.full_name}\n"
        f"Plano: {member.plan_name}\n"
        f"Metas: {goals_summary}\n"
        f"Restricoes: {constraints_summary}\n"
        f"Contexto previo: {previous_summary}\n"
        f"Valores atuais: {_serialize_measurements(evaluation)}\n"
        f"Faixas: {range_summary}\n"
        f"Classificacao objetiva: {classification_summary}\n"
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
    coach_summary = _trim_summary_text(" ".join(part for part in coach_parts if part).strip(), max_length=_COACH_SUMMARY_MAX_LENGTH)

    member_summary = _build_member_summary_from_signals(
        primary_goal=primary_goal,
        risk_flags=risk_flags,
        member_first_name=(member.full_name or "").split(" ")[0],
        max_length=_MEMBER_SUMMARY_MAX_LENGTH,
    )

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
    primary_goal = _normalize_goal_slug(
        normalized_focus.get("primary_goal"),
        allowed=_PRIMARY_GOAL_ALLOWED,
        fallback="acompanhamento_geral",
    )
    secondary_goal = _normalize_goal_slug(
        normalized_focus.get("secondary_goal"),
        allowed=_SECONDARY_GOAL_ALLOWED,
        fallback="preservacao_de_massa_magra",
    )
    return {
        "coach_summary": _trim_summary_text(payload.get("coach_summary"), max_length=_COACH_SUMMARY_MAX_LENGTH),
        "member_friendly_summary": _normalize_member_summary_text(
            payload.get("member_friendly_summary"),
            primary_goal=primary_goal,
            risk_flags=payload.get("risk_flags") or [],
            max_length=_MEMBER_SUMMARY_MAX_LENGTH,
        ),
        "risk_flags": [str(item) for item in payload.get("risk_flags") or []][:5],
        "training_focus": {
            "primary_goal": primary_goal,
            "secondary_goal": secondary_goal,
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


def _summarize_classifications(evaluation: BodyCompositionEvaluation) -> str:
    classifications = _classify_fields(evaluation)
    if not classifications:
        return "Sem classificacao automatica por faixa impressa"

    parts = [f"{label}: {status}" for label, status in classifications[:8]]
    return "; ".join(parts)


def _normalize_goal_slug(value: object, *, allowed: set[str], fallback: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return fallback

    candidate = raw.replace("-", "_").replace(" ", "_")
    if candidate in allowed:
        return candidate

    if "geral" in raw and "acompanhamento_geral" in allowed:
        return "acompanhamento_geral"
    if "gordura" in raw:
        if "controle" in raw and "controle_de_gordura" in allowed:
            return "controle_de_gordura"
        if "reducao_de_gordura" in allowed:
            return "reducao_de_gordura"
    if "massa" in raw and "ganho" in raw and "ganho_de_massa" in allowed:
        return "ganho_de_massa"
    if ("metabol" in raw or "visceral" in raw or "imc" in raw) and "melhora_metabolica" in allowed:
        return "melhora_metabolica"
    if "massa_magra" in raw or ("massa" in raw and "preserva" in raw):
        if "preservacao_de_massa_magra" in allowed:
            return "preservacao_de_massa_magra"

    return fallback


def build_body_composition_member_summary(
    evaluation: BodyCompositionEvaluation,
    *,
    member_first_name: str | None = None,
) -> str:
    stored = _normalize_member_summary_text(
        evaluation.ai_member_friendly_summary,
        primary_goal=_normalize_goal_slug(
            (evaluation.ai_training_focus_json or {}).get("primary_goal"),
            allowed=_PRIMARY_GOAL_ALLOWED,
            fallback="acompanhamento_geral",
        ),
        risk_flags=evaluation.ai_risk_flags_json or [],
        max_length=_MEMBER_SUMMARY_MAX_LENGTH,
    )
    if stored:
        return stored

    return _build_member_summary_from_signals(
        primary_goal=_normalize_goal_slug(
            (evaluation.ai_training_focus_json or {}).get("primary_goal"),
            allowed=_PRIMARY_GOAL_ALLOWED,
            fallback="acompanhamento_geral",
        ),
        risk_flags=evaluation.ai_risk_flags_json or [],
        member_first_name=member_first_name,
        max_length=_MEMBER_SUMMARY_MAX_LENGTH,
    )


def _normalize_member_summary_text(
    value: object,
    *,
    primary_goal: str,
    risk_flags: list[object],
    max_length: int,
) -> str:
    text = _trim_summary_text(value, max_length=max_length)
    if text and not _looks_too_technical_for_member(text):
        return text
    return _build_member_summary_from_signals(
        primary_goal=primary_goal,
        risk_flags=[str(item) for item in risk_flags][:3],
        max_length=max_length,
    )


def _looks_too_technical_for_member(text: str) -> bool:
    lowered = text.lower()
    jargon_hits = sum(1 for term in _TECHNICAL_MEMBER_TERMS if term in lowered)
    has_dense_numbers = len(re.findall(r"\d+[,.]?\d*", lowered)) >= 4
    has_parenthetical_numbers = bool(re.search(r"\([^)]*\d", text))
    return jargon_hits >= 2 or (jargon_hits >= 1 and (has_dense_numbers or has_parenthetical_numbers))


def _build_member_summary_from_signals(
    *,
    primary_goal: str,
    risk_flags: list[str],
    member_first_name: str | None = None,
    max_length: int,
) -> str:
    intro = (
        f"{member_first_name}, seu exame mostra um bom ponto de partida para organizar os proximos passos. "
        if member_first_name
        else "Seu exame mostra um bom ponto de partida para organizar os proximos passos. "
    )
    main_goal = _goal_for_member(primary_goal)
    flags_text = _humanize_risk_flags_for_member(risk_flags)
    message = (
        f"{intro}Agora vamos concentrar o acompanhamento em {main_goal}. "
        f"{flags_text} "
        "Com constancia nas proximas semanas, fica mais facil ajustar o plano e acompanhar sua evolucao de forma segura."
    )
    return _trim_summary_text(message, max_length=max_length)


def _goal_for_member(primary_goal: str) -> str:
    if primary_goal == "reducao_de_gordura":
        return "reduzir gordura sem perder o que voce ja tem de massa muscular"
    if primary_goal == "ganho_de_massa":
        return "ganhar massa com mais consistencia e acompanhar a resposta do corpo"
    if primary_goal == "melhora_metabolica":
        return "melhorar marcadores corporais e retomar ritmo com mais equilibrio"
    return "acompanhar sua evolucao corporal com mais clareza"


def _humanize_risk_flags_for_member(risk_flags: list[str]) -> str:
    if not risk_flags:
        return "Nao apareceu nenhum alerta forte fora do esperado neste momento."

    normalized = [_humanize_single_risk_flag(flag) for flag in risk_flags[:2] if str(flag).strip()]
    if not normalized:
        return "Nao apareceu nenhum alerta forte fora do esperado neste momento."
    if len(normalized) == 1:
        return f"O principal ponto de atencao agora e {normalized[0]}."
    return f"Os principais pontos de atencao agora sao {normalized[0]} e {normalized[1]}."


def _humanize_single_risk_flag(flag: str) -> str:
    lowered = flag.strip().lower()
    replacements = {
        "peso acima da faixa recomendada": "o peso estar acima da faixa recomendada",
        "gordura visceral elevada": "a gordura na regiao abdominal estar acima do desejado",
        "percentual de gordura acima da faixa": "o percentual de gordura estar acima do desejado",
        "imc acima da faixa": "o indice corporal estar acima do desejado",
        "massa muscular abaixo da faixa": "a massa muscular estar abaixo do ideal",
        "musculo esqueletico abaixo da faixa": "a musculatura de sustentacao estar abaixo do ideal",
    }
    return replacements.get(lowered, lowered)


def _trim_summary_text(value: object, *, max_length: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= max_length:
        return text

    sentence_cutoff = max(
        text.rfind(". ", 0, max_length),
        text.rfind("! ", 0, max_length),
        text.rfind("? ", 0, max_length),
    )
    if sentence_cutoff >= int(max_length * 0.6):
        return text[: sentence_cutoff + 1].strip()

    word_cutoff = text.rfind(" ", 0, max_length)
    if word_cutoff >= int(max_length * 0.6):
        return text[:word_cutoff].rstrip(" ,;:-") + "..."

    return text[:max_length].rstrip(" ,;:-") + "..."


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
