from __future__ import annotations

import logging

import anthropic

from app.core.circuit_breaker import claude_circuit_breaker
from app.core.config import settings
from app.models import Member
from app.models.assessment import Assessment
from app.utils.claude import _parse_claude_json


logger = logging.getLogger(__name__)


def build_narratives(
    member: Member,
    latest_assessment: Assessment | None,
    *,
    diagnosis: dict,
    forecast: dict,
    benchmark: dict,
) -> dict:
    if not settings.claude_api_key:
        return _fallback_narratives(member, diagnosis=diagnosis, forecast=forecast, benchmark=benchmark)

    if claude_circuit_breaker.is_open():
        logger.info("Circuit breaker aberto para Claude. Usando fallback em build_narratives.")
        return _fallback_narratives(member, diagnosis=diagnosis, forecast=forecast, benchmark=benchmark)

    try:
        prompt = (
            "Voce e um especialista em experiencia do aluno para academias.\n"
            "Retorne JSON com campos coach_summary, member_summary, retention_summary.\n"
            "Cada campo deve ter no maximo 280 caracteres.\n"
            f"Aluno: {member.full_name}\n"
            f"Risco atual: {member.risk_level.value} ({member.risk_score})\n"
            f"Gargalo principal: {diagnosis['primary_bottleneck_label']}\n"
            f"Forecast 60d: {forecast['probability_60d']}%\n"
            f"Forecast corrigido 90d: {forecast['corrected_probability_90d']}%\n"
            f"Benchmark: {benchmark['position_label']} ({benchmark['percentile']} percentil)\n"
            "Responda em portugues do Brasil."
        )
        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=350,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = _parse_claude_json(response.content[0].text.strip())
        claude_circuit_breaker.record_success()
        return {
            "coach_summary": str(parsed.get("coach_summary") or "")[:280],
            "member_summary": str(parsed.get("member_summary") or "")[:280],
            "retention_summary": str(parsed.get("retention_summary") or "")[:280],
        }
    except Exception:
        claude_circuit_breaker.record_failure()
        logger.exception("Falha ao gerar narrativas de avaliacao com Claude. Usando fallback.")
        return _fallback_narratives(member, diagnosis=diagnosis, forecast=forecast, benchmark=benchmark)


def _fallback_narratives(member: Member, *, diagnosis: dict, forecast: dict, benchmark: dict) -> dict:
    coach_summary = (
        f"Priorize {diagnosis['primary_bottleneck_label'].lower()} e alinhe a rotina do aluno. "
        f"A chance atual de meta em 60 dias esta em {forecast['probability_60d']}%."
    )
    member_summary = (
        f"Seu progresso depende principalmente de ajustar {diagnosis['primary_bottleneck_label'].lower()}. "
        f"Hoje sua curva esta {benchmark['position_label'].lower()} para perfis parecidos."
    )
    retention_summary = (
        f"{member.full_name} tem risco de frustracao {diagnosis['frustration_risk']} e previsao de meta em 90 dias de "
        f"{forecast['probability_90d']}%. Necessita comunicacao ativa de valor."
    )
    return {
        "coach_summary": coach_summary[:280],
        "member_summary": member_summary[:280],
        "retention_summary": retention_summary[:280],
    }
