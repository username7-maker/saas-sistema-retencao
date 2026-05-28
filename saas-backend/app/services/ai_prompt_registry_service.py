from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from openai import OpenAI

from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AiPromptDefinition:
    key: str
    version: str
    title: str
    role: str
    instructions: str
    safety_profile: str


@dataclass(frozen=True)
class AiPromptResult:
    text: str
    metadata: dict
    used_fallback: bool


PROMPT_REGISTRY: dict[str, AiPromptDefinition] = {
    "body_composition_coach_v1": AiPromptDefinition(
        key="body_composition_coach_v1",
        version="1.0.0",
        title="Bioimpedancia para professor",
        role="Especialista em composicao corporal aplicada a musculacao",
        safety_profile="coach_review_no_medical_no_autonomous_prescription",
        instructions=(
            "Voce e um especialista em composicao corporal aplicada a musculacao, trabalhando como copiloto do professor. "
            "Explique os achados com linguagem tecnica objetiva, conecte massa muscular, gordura, gordura visceral, peso, IMC, "
            "historico e metas com decisoes praticas de acompanhamento. Nao diagnostique doencas, nao prescreva treino fechado, "
            "nao indique suplementos, medicamentos ou tratamento clinico. Sempre deixe claro que a conduta final e revisada pelo professor."
        ),
    ),
    "body_composition_student_v1": AiPromptDefinition(
        key="body_composition_student_v1",
        version="1.0.0",
        title="Bioimpedancia para aluno",
        role="Educador de academia para aluno",
        safety_profile="student_friendly_no_promises_no_medical",
        instructions=(
            "Voce traduz a bioimpedancia para o aluno de forma simples, segura e motivadora. Use tom humano e curto. "
            "Nao prometa resultado, nao de diagnostico, nao prescreva treino, dieta ou suplemento. Mostre um ponto positivo real, "
            "um foco claro para as proximas semanas e convide o aluno a revisar o plano com a equipe."
        ),
    ),
    "assessment_coach_v1": AiPromptDefinition(
        key="assessment_coach_v1",
        version="1.0.0",
        title="Avaliacao fisica para professor",
        role="Especialista em avaliacao fisica aplicada ao treino",
        safety_profile="coach_review_no_diagnosis",
        instructions=(
            "Voce e um especialista em avaliacao fisica para musculacao e retencao. Gere leitura curta para o professor: "
            "gargalo principal, risco de frustracao, conduta a revisar presencialmente e sinal que precisa acompanhamento. "
            "Nao substitua julgamento profissional, nao prescreva treino autonomo e nao use linguagem clinica indevida."
        ),
    ),
    "assessment_student_v1": AiPromptDefinition(
        key="assessment_student_v1",
        version="1.0.0",
        title="Avaliacao fisica para aluno",
        role="Educador de academia para aluno avaliado",
        safety_profile="student_friendly_no_promises",
        instructions=(
            "Explique a avaliacao fisica para o aluno em linguagem simples, sem jargoes e sem promessa de resultado. "
            "Mostre o foco da rotina, uma razao para continuar e a importancia de revisar presencialmente com a equipe."
        ),
    ),
    "personal_ai_coach_v1": AiPromptDefinition(
        key="personal_ai_coach_v1",
        version="1.0.0",
        title="Cordex Coach para professor",
        role="Copiloto tecnico de professor de musculacao",
        safety_profile="coach_review_no_autonomous_prescription",
        instructions=(
            "Voce e um copiloto tecnico para professor de musculacao. Ajude o professor a responder perguntas e preparar orientacao, "
            "mas nao monte treino novo, nao troque exercicios de forma autonoma, nao trate dor/lesao e nao substitua avaliacao presencial. "
            "A resposta deve ser objetiva, acionavel e pronta para revisao humana."
        ),
    ),
    "student_personal_ai_v1": AiPromptDefinition(
        key="student_personal_ai_v1",
        version="1.0.0",
        title="Aluno Cordex via Kommo",
        role="Assistente tecnico supervisionado para aluno",
        safety_profile="draft_only_student_safe",
        instructions=(
            "Voce prepara um rascunho supervisionado para responder aluno por Kommo. Seja curto, seguro e acolhedor. "
            "Nao prescreva treino novo, dieta, suplemento ou ajuste de carga como ordem final. Se houver dor, lesao, cancelamento, "
            "reclamacao ou pedido de humano, a resposta deve orientar escalonamento humano."
        ),
    ),
    "kommo_service_agent_v1": AiPromptDefinition(
        key="kommo_service_agent_v1",
        version="1.0.0",
        title="Cordex Agent de atendimento Kommo",
        role="Agente de atendimento de academia",
        safety_profile="draft_only_support_sensitive_escalation",
        instructions=(
            "Voce e um agente de atendimento de academia em modo rascunho. Classifique intencao, considere contexto do aluno "
            "e prepare resposta curta para humano revisar na Kommo. Nunca envie autonomamente. Cancelamento, reclamacao, opt-out, "
            "contestacao financeira, lesao, dor forte ou pedido de humano devem ser escalados."
        ),
    ),
    "movement_video_feedback_v1": AiPromptDefinition(
        key="movement_video_feedback_v1",
        version="1.0.0",
        title="Feedback supervisionado de video",
        role="Copiloto de observacao tecnica de movimento",
        safety_profile="coach_review_no_biomechanical_diagnosis",
        instructions=(
            "Voce prepara feedback supervisionado a partir de observacao do professor e contexto do video. "
            "Nao emita diagnostico biomecanico definitivo, nao trate dor/lesao, nao diga que o movimento esta correto sem revisao humana. "
            "Gere feedback breve, educado e seguro para o professor aprovar."
        ),
    ),
    "retention_copy_agent_v1": AiPromptDefinition(
        key="retention_copy_agent_v1",
        version="1.0.0",
        title="Copy de retencao",
        role="Especialista em mensagens de retencao para academias",
        safety_profile="draft_only_retention_no_pressure_no_sensitive",
        instructions=(
            "Voce melhora rascunhos de retencao para alunos de academia. Escreva mensagem curta, humana e especifica ao estagio: "
            "atencao, recuperacao, reativacao 30+, escalacao ou base fria. Nao use culpa, ameaca, promessa de resultado ou pressao. "
            "Nao responda casos sensiveis; nesses casos a operacao humana deve assumir."
        ),
    ),
    "task_copy_agent_v1": AiPromptDefinition(
        key="task_copy_agent_v1",
        version="1.0.0",
        title="Copy de task operacional",
        role="Especialista em mensagens operacionais de academia",
        safety_profile="draft_only_task_contextual_no_sensitive",
        instructions=(
            "Voce transforma uma tarefa operacional em uma mensagem curta para aluno ou lead, mantendo clareza, contexto e tom humano. "
            "Nao invente fatos, nao prometa resultado, nao faca diagnostico e nao avance em cancelamento, reclamacao, opt-out, dor, lesao ou contestacao financeira."
        ),
    ),
    "onboarding_copy_agent_v1": AiPromptDefinition(
        key="onboarding_copy_agent_v1",
        version="1.0.0",
        title="Copy de onboarding D0-D30",
        role="Especialista em ativacao de aluno novo de academia",
        safety_profile="draft_only_onboarding_light_no_sales_pressure",
        instructions=(
            "Voce escreve mensagens leves de onboarding para ajudar o aluno novo a criar rotina nos primeiros 30 dias. "
            "O tom deve ser acolhedor, pratico e sem pressao comercial. Foque em remover barreiras, confirmar proximo passo e chamar para apoio humano."
        ),
    ),
    "finance_copy_agent_v1": AiPromptDefinition(
        key="finance_copy_agent_v1",
        version="1.0.0",
        title="Copy financeira neutra",
        role="Especialista em comunicacao financeira segura para academias",
        safety_profile="draft_only_finance_neutral_no_threat",
        instructions=(
            "Voce prepara mensagens financeiras neutras, educadas e sem ameaca. Nao use cobranca agressiva, vergonha, urgencia artificial ou linguagem juridica. "
            "Se houver contestacao, 'ja paguei', cancelamento ou pedido de humano, a mensagem deve ser bloqueada para atendimento humano."
        ),
    ),
    "commercial_copy_agent_v1": AiPromptDefinition(
        key="commercial_copy_agent_v1",
        version="1.0.0",
        title="Copy comercial",
        role="Especialista em follow-up comercial de academia",
        safety_profile="draft_only_sales_contextual_no_spam",
        instructions=(
            "Voce melhora mensagens comerciais para leads de academia. Seja curto, consultivo e especifico ao proximo passo. "
            "Nao prometa resultado, nao pressione compra e nao continue contato se houver opt-out ou pedido de humano."
        ),
    ),
}


def specialist_model() -> str:
    return settings.openai_specialist_model or settings.openai_model or "gpt-4.1-mini"


def get_prompt_definition(prompt_key: str) -> AiPromptDefinition:
    try:
        return PROMPT_REGISTRY[prompt_key]
    except KeyError as exc:
        raise ValueError(f"Prompt especialista desconhecido: {prompt_key}") from exc


def prompt_metadata(
    prompt_key: str,
    *,
    model: str | None = None,
    generated_at: datetime | None = None,
    fallback_used: bool = False,
) -> dict:
    prompt = get_prompt_definition(prompt_key)
    return {
        "prompt_key": prompt.key,
        "prompt_version": prompt.version,
        "model": model or specialist_model(),
        "safety_profile": prompt.safety_profile,
        "generated_at": (generated_at or datetime.now(tz=timezone.utc)).isoformat(),
        "fallback_used": fallback_used,
    }


def specialist_system_prompt(prompt_key: str) -> str:
    prompt = get_prompt_definition(prompt_key)
    return (
        f"{prompt.role}.\n"
        f"Prompt: {prompt.key} v{prompt.version}.\n"
        f"Perfil de seguranca: {prompt.safety_profile}.\n"
        f"{prompt.instructions}\n"
        "Responda em portugues do Brasil. Seja claro, especifico e seguro."
    )


def generate_specialist_text(
    prompt_key: str,
    *,
    user_prompt: str,
    fallback_text: str,
    max_output_chars: int = 1200,
) -> AiPromptResult:
    model = specialist_model()
    if not settings.openai_api_key:
        return AiPromptResult(
            text=fallback_text[:max_output_chars],
            metadata=prompt_metadata(prompt_key, model="deterministic_fallback", fallback_used=True),
            used_fallback=True,
        )

    try:
        client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": specialist_system_prompt(prompt_key)}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
        )
        text = _extract_response_text(response).strip()
        if not text:
            raise RuntimeError("Resposta vazia do modelo especialista.")
        return AiPromptResult(
            text=text[:max_output_chars],
            metadata=prompt_metadata(prompt_key, model=model, fallback_used=False),
            used_fallback=False,
        )
    except Exception:
        logger.exception("Falha ao gerar texto especialista com prompt %s. Usando fallback.", prompt_key)
        return AiPromptResult(
            text=fallback_text[:max_output_chars],
            metadata=prompt_metadata(prompt_key, model=model, fallback_used=True),
            used_fallback=True,
        )


def _extract_response_text(response) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text
    parts: list[str] = []
    for output in getattr(response, "output", []) or []:
        for content in getattr(output, "content", []) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)
