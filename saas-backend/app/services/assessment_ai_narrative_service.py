from __future__ import annotations

import logging

import anthropic
from openai import OpenAI
from pydantic import BaseModel

from app.core.circuit_breaker import claude_circuit_breaker
from app.core.config import settings
from app.models import Member
from app.models.assessment import Assessment
from app.services.ai_prompt_registry_service import prompt_metadata, specialist_model, specialist_system_prompt
from app.utils.claude import _parse_claude_json


logger = logging.getLogger(__name__)


class _OpenAIAssessmentNarratives(BaseModel):
    coach_summary: str = ""
    member_summary: str = ""
    retention_summary: str = ""


def build_narratives(
    member: Member,
    latest_assessment: Assessment | None,
    *,
    diagnosis: dict,
    forecast: dict,
    benchmark: dict,
) -> dict:
    if settings.openai_api_key:
        try:
            return _openai_narratives(member, diagnosis=diagnosis, forecast=forecast, benchmark=benchmark)
        except Exception:
            logger.exception("Falha ao gerar narrativas de avaliacao com OpenAI especialista. Tentando fallback.")

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
            "prompt_metadata": prompt_metadata("assessment_coach_v1", model=settings.claude_model),
            "student_prompt_metadata": prompt_metadata("assessment_student_v1", model=settings.claude_model),
        }
    except Exception:
        claude_circuit_breaker.record_failure()
        logger.exception("Falha ao gerar narrativas de avaliacao com Claude. Usando fallback.")
        return _fallback_narratives(member, diagnosis=diagnosis, forecast=forecast, benchmark=benchmark)


def _openai_narratives(member: Member, *, diagnosis: dict, forecast: dict, benchmark: dict) -> dict:
    prompt = (
        "Retorne JSON com campos coach_summary, member_summary e retention_summary.\n"
        "Cada campo deve ter no maximo 280 caracteres.\n"
        f"Aluno: {member.full_name}\n"
        f"Risco atual: {getattr(member.risk_level, 'value', member.risk_level)} ({member.risk_score})\n"
        f"Gargalo principal: {diagnosis['primary_bottleneck_label']}\n"
        f"Forecast 60d: {forecast['probability_60d']}%\n"
        f"Forecast corrigido 90d: {forecast['corrected_probability_90d']}%\n"
        f"Benchmark: {benchmark['position_label']} ({benchmark['percentile']} percentil)\n"
        "coach_summary deve ser tecnico para professor. member_summary deve ser simples para aluno. "
        "retention_summary deve explicar risco operacional sem exagero."
    )
    client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)
    response = client.responses.parse(
        model=specialist_model(),
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": specialist_system_prompt("assessment_coach_v1")
                        + "\nPara member_summary, aplique tambem o prompt assessment_student_v1.",
                    }
                ],
            },
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ],
        text_format=_OpenAIAssessmentNarratives,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise RuntimeError("OpenAI nao retornou narrativas estruturadas para avaliacao.")
    payload = parsed.model_dump()
    return {
        "coach_summary": str(payload.get("coach_summary") or "")[:280],
        "member_summary": str(payload.get("member_summary") or "")[:280],
        "retention_summary": str(payload.get("retention_summary") or "")[:280],
        "prompt_metadata": prompt_metadata("assessment_coach_v1", model=specialist_model()),
        "student_prompt_metadata": prompt_metadata("assessment_student_v1", model=specialist_model()),
    }


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
        "prompt_metadata": prompt_metadata(
            "assessment_coach_v1",
            model="deterministic_fallback",
            fallback_used=True,
        ),
        "student_prompt_metadata": prompt_metadata(
            "assessment_student_v1",
            model="deterministic_fallback",
            fallback_used=True,
        ),
    }
