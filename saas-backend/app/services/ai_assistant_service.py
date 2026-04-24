from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import Member, RiskLevel, Task
from app.models.body_composition import BodyCompositionEvaluation
from app.schemas.assistant import AIAssistantPayload


_ONBOARDING_FACTOR_LABELS = {
    "checkin_frequency": "Check-ins iniciais",
    "first_assessment": "Primeira avaliacao",
    "task_completion": "Execucao das tarefas",
    "consistency": "Consistencia da rotina",
    "member_response": "Resposta do aluno",
}

_CHURN_LABELS = {
    "early_dropout": "onboarding fragil",
    "voluntary_dissatisfaction": "insatisfacao percebida",
    "voluntary_financial": "barreira financeira",
    "voluntary_relocation": "mudanca de rotina",
    "involuntary_inactivity": "inatividade",
    "involuntary_seasonal": "padrao sazonal",
    "unknown": "causa ainda difusa",
}


def _assistant_contract(
    *,
    provider: str = "system",
    mode: str = "rule_based",
    fallback_used: bool = False,
    manual_required: bool = True,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "mode": mode,
        "fallback_used": fallback_used,
        "manual_required": manual_required,
    }


def build_onboarding_assistant(member: Member, onboarding_result: dict[str, Any]) -> AIAssistantPayload:
    factors = onboarding_result.get("factors") or {}
    weakest_key = min(factors, key=factors.get) if factors else "checkin_frequency"
    weakest_value = int(factors.get(weakest_key, 0))
    weakest_label = _ONBOARDING_FACTOR_LABELS.get(weakest_key, weakest_key.replace("_", " "))
    days_since_join = int(onboarding_result.get("days_since_join") or 0)
    score = int(onboarding_result.get("score") or 0)
    status = str(onboarding_result.get("status") or "active")
    total_tasks = int(onboarding_result.get("total_tasks") or 0)
    completed_tasks = int(onboarding_result.get("completed_tasks") or 0)
    checkin_count = int(onboarding_result.get("checkin_count") or 0)

    cta_target = f"/assessments/members/{member.id}?tab=overview"
    cta_label = "Abrir perfil 360"
    recommended_channel = "WhatsApp"
    next_best_action = "Reforcar a rotina do aluno nas proximas 24 horas."
    suggested_message = (
        f"Oi {first_name(member.full_name)}, vi que seu comeco ainda esta instavel. "
        "Quero te ajudar a encaixar a rotina desta semana e remover qualquer barreira."
    )

    if weakest_key == "first_assessment":
        cta_target = f"/assessments/members/{member.id}?tab=registro"
        cta_label = "Abrir avaliacao"
        recommended_channel = "Avaliacao"
        next_best_action = "Agendar a primeira avaliacao e transformar a entrada em um plano claro."
        suggested_message = (
            f"Oi {first_name(member.full_name)}, vamos marcar sua primeira avaliacao para ajustar meta, frequencia e plano de treino?"
        )
    elif weakest_key in {"task_completion", "consistency"}:
        cta_target = f"/assessments/members/{member.id}?tab=acoes"
        cta_label = "Abrir acoes"
        recommended_channel = "Follow-up humano"
        next_best_action = "Executar o proximo follow-up do onboarding e confirmar a proxima ida do aluno."
    elif weakest_key == "member_response":
        cta_target = f"/assessments/members/{member.id}?tab=contexto"
        cta_label = "Abrir contexto"
        recommended_channel = "WhatsApp"
        next_best_action = "Fazer contato curto e entender o que esta travando a resposta do aluno."

    confidence_label = "Alta" if score >= 70 else "Moderada" if score >= 40 else "Prioridade imediata"
    summary = (
        f"{member.full_name} esta {days_since_join} dias dentro do onboarding com score {score}. "
        f"O maior gargalo hoje e {weakest_label.lower()}."
    )
    why_it_matters = (
        f"Quando {weakest_label.lower()} fica em {weakest_value}%, o risco de o aluno esfriar antes do D30 aumenta. "
        "A melhor janela de recuperacao ainda e nas proximas 24 horas."
    )
    evidence = [
        f"{checkin_count} check-in(s) nos primeiros {days_since_join} dias",
        f"{completed_tasks}/{total_tasks} tarefa(s) concluidas no onboarding",
        f"{weakest_label}: {weakest_value}%",
    ]
    if status == "at_risk":
        evidence.append("Status atual do onboarding: em risco")

    return AIAssistantPayload(
        summary=summary,
        why_it_matters=why_it_matters,
        next_best_action=next_best_action,
        suggested_message=suggested_message,
        evidence=evidence,
        **_assistant_contract(),
        confidence_label=confidence_label,
        recommended_channel=recommended_channel,
        cta_target=cta_target,
        cta_label=cta_label,
    )


def build_task_assistant(db: Session, task: Task) -> AIAssistantPayload:
    source = str((task.extra_data or {}).get("source") or "manual").strip().lower()

    if task.member is not None and source in {"onboarding", "onboarding_handoff", "plan_followup"}:
        from app.services.onboarding_score_service import calculate_onboarding_score

        assistant = build_onboarding_assistant(task.member, calculate_onboarding_score(db, task.member))
        return assistant.model_copy(
            update={
                "summary": f"Tarefa orientada pelo onboarding: {task.title}. {assistant.summary}",
                "cta_label": "Executar no perfil",
            }
        )

    if task.member is not None and source == "assessment_intelligence":
        from app.services.assessment_intelligence_service import get_assessment_summary_360

        summary = get_assessment_summary_360(db, task.member.id)
        assistant = build_assessment_assistant(summary)
        return assistant.model_copy(update={"summary": f"Tarefa originada da leitura de avaliacao. {assistant.summary}"})

    if task.member is not None and source == "retention_intelligence":
        member = task.member
        days_without_checkin = days_since(member.last_checkin_at)
        risk_score = int(getattr(member, "risk_score", 0) or 0)
        risk_level = getattr(member, "risk_level", RiskLevel.YELLOW)
        churn_label = _CHURN_LABELS.get(getattr(member, "churn_type", None), "sinal de evasao ativo")
        recommended_channel = "Ligacao" if risk_level == RiskLevel.RED else "WhatsApp"
        return AIAssistantPayload(
            summary=(
                f"{member.full_name} entrou nesta task porque tem risco {risk_level.value} e sinais de {churn_label}."
            ),
            why_it_matters=(
                f"O aluno esta ha {days_without_checkin or 0} dia(s) sem check-in e com score {risk_score}. "
                "Uma abordagem humana contextual tende a recuperar melhor do que um contato generico."
            ),
            next_best_action="Abrir o contexto do aluno, revisar sinais e iniciar uma abordagem curta e humana.",
            suggested_message=(
                f"Oi {first_name(member.full_name)}, percebi que sua rotina saiu um pouco do eixo. "
                "Quero te ajudar a voltar sem pressao e encontrar o melhor ajuste desta semana."
            ),
            evidence=[
                f"Risk score: {risk_score}",
                f"Dias sem check-in: {days_without_checkin or 0}",
                f"Churn type: {churn_label}",
            ],
            **_assistant_contract(),
            confidence_label="Alta" if risk_level == RiskLevel.RED else "Moderada",
            recommended_channel=recommended_channel,
            cta_target=f"/assessments/members/{member.id}?tab=contexto",
            cta_label="Abrir contexto",
        )

    if task.member is not None:
        member = task.member
        return AIAssistantPayload(
            summary=f"Tarefa manual ligada a {member.full_name}.",
            why_it_matters="Mesmo tarefas manuais ganham mais contexto quando executadas a partir do perfil do aluno.",
            next_best_action="Abrir o perfil 360, revisar o historico recente e executar a tarefa no contexto certo.",
            suggested_message=task.suggested_message,
            evidence=[
                f"Prioridade: {task.priority.value}",
                f"Status atual: {task.status.value}",
                f"Origem: {source}",
            ],
            **_assistant_contract(),
            confidence_label="Inicial",
            recommended_channel="Contexto do aluno",
            cta_target=f"/assessments/members/{member.id}?tab=acoes",
            cta_label="Abrir perfil",
        )

    if task.lead is not None:
        return AIAssistantPayload(
            summary=f"Tarefa comercial ligada ao lead {task.lead.full_name}.",
            why_it_matters="Para leads, a melhor execucao costuma acontecer no CRM, onde estao historico e proximo estagio.",
            next_best_action="Abrir o lead no CRM e fazer a proxima acao comercial com contexto.",
            suggested_message=task.suggested_message or f"Oi {first_name(task.lead.full_name)}, posso te ajudar a seguir para o proximo passo?",
            evidence=[
                f"Origem: {source}",
                f"Prioridade: {task.priority.value}",
                f"Prazo: {task.due_date.isoformat() if task.due_date else 'sem prazo'}",
            ],
            **_assistant_contract(),
            confidence_label="Inicial",
            recommended_channel="CRM",
            cta_target=f"/crm?leadId={task.lead_id}",
            cta_label="Abrir lead",
        )

    return AIAssistantPayload(
        summary=f"Tarefa operacional: {task.title}.",
        why_it_matters="Sem um destino vinculado, a tarefa depende de contexto humano para ser executada com qualidade.",
        next_best_action="Revisar a descricao, confirmar o objetivo e seguir pelo fluxo operacional correspondente.",
        suggested_message=task.suggested_message,
        evidence=[
            f"Origem: {source}",
            f"Prioridade: {task.priority.value}",
            f"Status atual: {task.status.value}",
        ],
        **_assistant_contract(),
        confidence_label="Inicial",
        recommended_channel="Operacao",
        cta_target="/tasks",
        cta_label="Voltar para tarefas",
    )


def build_retention_assistant(item: Any) -> AIAssistantPayload:
    churn_label = _CHURN_LABELS.get(getattr(item, "churn_type", None), "risco composto")
    risk_level = getattr(item, "risk_level", RiskLevel.YELLOW)
    days_without_checkin = getattr(item, "days_without_checkin", None)
    forecast_60d = getattr(item, "forecast_60d", None)
    recommended_channel = "Ligacao" if risk_level == RiskLevel.RED else "WhatsApp"

    evidence = [
        f"Risk score: {getattr(item, 'risk_score', 0)}",
        f"Dias sem check-in: {days_without_checkin if days_without_checkin is not None else 'sem dado'}",
        f"Forecast 60d: {forecast_60d if forecast_60d is not None else 'sem forecast'}",
    ]
    if getattr(item, "signals_summary", None):
        evidence.append(str(item.signals_summary))

    return AIAssistantPayload(
        summary=(
            f"{getattr(item, 'full_name', 'Aluno')} entrou na fila por sinais de {churn_label} "
            f"com severidade {risk_level.value}."
        ),
        why_it_matters=(
            f"Com {days_without_checkin if days_without_checkin is not None else 0} dia(s) sem check-in "
            f"e forecast de {forecast_60d if forecast_60d is not None else '--'}%, a janela de recuperacao pede acao contextual."
        ),
        next_best_action=getattr(item, "next_action", None) or "Abrir o playbook e executar a primeira abordagem sugerida.",
        suggested_message=(
            f"Oi {first_name(getattr(item, 'full_name', ''))}, senti sua ausencia nos ultimos dias. "
            "Quero entender o que atrapalhou sua rotina e te ajudar a voltar com um plano simples."
        ),
        evidence=evidence,
        **_assistant_contract(),
        confidence_label="Alta" if risk_level == RiskLevel.RED else "Moderada",
        recommended_channel=recommended_channel,
        cta_target=f"/assessments/members/{getattr(item, 'member_id', '')}?tab=contexto",
        cta_label="Abrir perfil 360",
    )


def build_assessment_assistant(summary: dict[str, Any]) -> AIAssistantPayload:
    member = summary["member"]
    diagnosis = summary["diagnosis"]
    forecast = summary["forecast"]
    next_action = summary["next_best_action"]
    narratives = summary["narratives"]
    probability_60d = int(forecast.get("probability_60d") or 0)
    frustration_risk = int(diagnosis.get("frustration_risk") or 0)

    return AIAssistantPayload(
        summary=(
            f"{member.full_name} mostra como principal gargalo {diagnosis['primary_bottleneck_label'].lower()} "
            f"e chance de {probability_60d}% de atingir a meta em 60 dias."
        ),
        why_it_matters=(
            f"O risco de frustracao esta em {frustration_risk}%. "
            "Sem ajuste rapido, o aluno pode perder percepcao de progresso e engajamento."
        ),
        next_best_action=next_action["title"],
        suggested_message=next_action.get("suggested_message"),
        evidence=[
            f"Resumo coach: {narratives['coach_summary']}",
            f"Resumo aluno: {narratives['member_summary']}",
            f"Benchmark: {summary['benchmark']['position_label']}",
        ],
        **_assistant_contract(),
        confidence_label=str(forecast.get("confidence") or "Moderada").capitalize(),
        recommended_channel="Avaliacao",
        cta_target=f"/assessments/members/{member.id}?tab=registro",
        cta_label="Registrar avaliacao",
    )


def build_body_composition_assistant(
    member: Member,
    evaluation: BodyCompositionEvaluation,
    previous_evaluation: BodyCompositionEvaluation | None = None,
) -> AIAssistantPayload:
    risk_flags = list(evaluation.ai_risk_flags_json or [])
    focus = evaluation.ai_training_focus_json or {}
    primary_goal_slug = str(focus.get("primary_goal") or "acompanhamento_geral")
    primary_goal = _format_body_goal(primary_goal_slug)
    suggested_focuses = [str(item) for item in focus.get("suggested_focuses") or []]
    change_summary = _body_change_summary(evaluation, previous_evaluation)

    evidence = risk_flags[:3]
    if change_summary:
        evidence.append(change_summary)
    if suggested_focuses:
        evidence.extend(suggested_focuses[:2])

    summary = _build_body_assistant_summary(primary_goal, risk_flags)
    why_it_matters = _build_body_assistant_why(evaluation=evaluation, primary_goal=primary_goal)

    return AIAssistantPayload(
        summary=summary,
        why_it_matters=why_it_matters,
        next_best_action=(
            f"Usar o exame para alinhar o foco inicial em {primary_goal} e ajustar o acompanhamento desta semana."
        ),
        suggested_message=(
            f"Seu exame mostra um bom ponto de partida. Agora vamos focar em {primary_goal} e acompanhar as proximas semanas com metas simples."
        ),
        evidence=evidence[:5],
        **_assistant_contract(
            mode="assisted_summary",
            manual_required=bool(evaluation.needs_review),
        ),
        confidence_label=_body_confidence_label(evaluation),
        recommended_channel="Explicacao guiada",
        cta_target=f"/assessments/members/{member.id}?tab=plano",
        cta_label="Ajustar plano",
    )


def first_name(full_name: str) -> str:
    return (full_name or "Aluno").strip().split(" ")[0] or "Aluno"


def days_since(value: datetime | None) -> int | None:
    if value is None:
        return None
    now = datetime.now(tz=timezone.utc)
    reference = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return max(0, (now - reference).days)


def _body_change_summary(
    evaluation: BodyCompositionEvaluation,
    previous_evaluation: BodyCompositionEvaluation | None,
) -> str | None:
    if previous_evaluation is None:
        return None

    deltas: list[str] = []
    weight_delta = _delta_text(evaluation.weight_kg, previous_evaluation.weight_kg, "peso", "kg")
    fat_delta = _delta_text(evaluation.body_fat_percent, previous_evaluation.body_fat_percent, "gordura", "pp")
    muscle_delta = _delta_text(
        evaluation.skeletal_muscle_kg or evaluation.muscle_mass_kg,
        previous_evaluation.skeletal_muscle_kg or previous_evaluation.muscle_mass_kg,
        "massa muscular",
        "kg",
    )
    for delta in (weight_delta, fat_delta, muscle_delta):
        if delta:
            deltas.append(delta)
    return "Comparacao com o exame anterior: " + " | ".join(deltas) if deltas else None


def _delta_text(current: float | None, previous: float | None, label: str, unit: str) -> str | None:
    if current is None or previous is None:
        return None
    delta = round(current - previous, 2)
    if delta == 0:
        return f"{label} estavel"
    direction = "subiu" if delta > 0 else "caiu"
    return f"{label} {direction} {abs(delta)} {unit}"


def _format_body_goal(value: str) -> str:
    mapping = {
        "reducao_de_gordura": "reducao de gordura",
        "ganho_de_massa": "ganho de massa",
        "melhora_metabolica": "melhora metabolica",
        "acompanhamento_geral": "acompanhamento geral",
        "preservacao_de_massa_magra": "preservacao de massa magra",
        "controle_de_gordura": "controle de gordura",
    }
    return mapping.get(value, value.replace("_", " "))


def _build_body_assistant_summary(primary_goal: str, risk_flags: list[str]) -> str:
    if risk_flags:
        flags_text = ", ".join(flag.lower() for flag in risk_flags[:2])
        return f"Bioimpedancia com foco inicial em {primary_goal}, com atencao principal para {flags_text}."
    return f"Bioimpedancia sem alertas prioritarios fora da faixa, com foco inicial em {primary_goal}."


def _build_body_assistant_why(*, evaluation: BodyCompositionEvaluation, primary_goal: str) -> str:
    if evaluation.needs_review:
        return (
            f"A leitura ja ajuda a conduzir a conversa inicial e alinhar {primary_goal}, "
            "mas ainda pede revisao manual antes de fechar o plano."
        )
    return (
        f"A leitura ja ajuda o professor a explicar o exame com clareza, alinhar {primary_goal} "
        "e transformar o resultado em acompanhamento pratico."
    )


def _body_confidence_label(evaluation: BodyCompositionEvaluation) -> str:
    if evaluation.reviewed_manually:
        return "Revisado manualmente"
    if evaluation.needs_review:
        return "Revisao recomendada"
    if evaluation.ocr_confidence is not None and evaluation.ocr_confidence >= 0.85:
        return "Leitura confiavel"
    if evaluation.ocr_confidence is not None:
        return "Leitura assistida"
    return "Moderada"
