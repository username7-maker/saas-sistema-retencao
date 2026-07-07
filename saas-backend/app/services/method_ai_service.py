import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote


VALID_BRAZILIAN_DDDS = {
    "11", "12", "13", "14", "15", "16", "17", "18", "19",
    "21", "22", "24", "27", "28",
    "31", "32", "33", "34", "35", "37", "38",
    "41", "42", "43", "44", "45", "46", "47", "48", "49",
    "51", "53", "54", "55",
    "61", "62", "63", "64", "65", "66", "67", "68", "69",
    "71", "73", "74", "75", "77", "79",
    "81", "82", "83", "84", "85", "86", "87", "88", "89",
    "91", "92", "93", "94", "95", "96", "97", "98", "99",
}

HIGH_PRIORITY_EVENTS = {
    "payment_overdue",
    "proposal_no_response",
    "simulation_no_response",
    "low_frequency",
    "no_checkin_7_days",
    "no_return_scheduled",
    "package_finished_no_repurchase",
    "contract_expiring",
}
CRITICAL_EVENTS = {"cancel_request", "churn_signal", "inactive_customer", "no_show_repeated"}


def _digits_only(value: str | None) -> str:
    return re.sub(r"\D+", "", value or "")


def normalize_brazilian_whatsapp_phone(phone: str | None) -> str | None:
    """Return a strict wa.me phone in 55DDNNNNNNNN[N] format, or None."""

    digits = _digits_only(phone)
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("55"):
        local = digits[2:]
    elif len(digits) in {10, 11}:
        local = digits
    else:
        return None

    if len(local) not in {10, 11}:
        return None

    ddd = local[:2]
    if ddd not in VALID_BRAZILIAN_DDDS:
        return None

    subscriber = local[2:]
    if len(subscriber) == 9 and not subscriber.startswith("9"):
        return None
    return f"55{local}"


def build_wa_me_link(phone: str | None, message: str | None) -> str | None:
    normalized = normalize_brazilian_whatsapp_phone(phone)
    if not normalized:
        return None
    text = (message or "").strip()
    if not text:
        return f"https://wa.me/{normalized}"
    return f"https://wa.me/{normalized}?text={quote(text)}"


def first_name(name: str | None) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        return "cliente"
    return cleaned.split()[0]


def _human_review_metadata(kind: str, **extra: Any) -> dict[str, Any]:
    return {
        "provider": "deterministic_fallback",
        "model": "template-v1",
        "fallback_used": True,
        "requires_human_approval": True,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "kind": kind,
        **extra,
    }


def classify_intent(text: str | None) -> dict[str, Any]:
    value = (text or "").lower()
    if any(token in value for token in ("preco", "valor", "plano", "orcamento", "proposta")):
        intent = "commercial_interest"
    elif any(token in value for token in ("cancel", "parar", "sair", "desist")):
        intent = "churn_risk"
    elif any(token in value for token in ("retorno", "voltar", "remarcar", "renovar")):
        intent = "post_sale_recovery"
    elif any(token in value for token in ("horario", "agenda", "visita", "reuniao")):
        intent = "scheduling"
    else:
        intent = "needs_human_review"
    return {"intent": intent, "confidence": 0.62, "metadata": _human_review_metadata("intent_classification")}


def suggest_priority(event_type: str | None, pillar: str | None = None, payload: dict[str, Any] | None = None) -> str:
    normalized = (event_type or "").strip().lower()
    if normalized in CRITICAL_EVENTS:
        return "critical"
    if normalized in HIGH_PRIORITY_EVENTS:
        return "high"
    if (pillar or "") == "sales" and normalized in {"followup_due", "new_contact", "proposal_sent"}:
        return "high"
    payload = payload or {}
    if str(payload.get("urgency") or "").lower() in {"alta", "high", "urgent", "critical"}:
        return "high"
    return "medium"


def summarize_history(items: list[dict[str, Any]] | None) -> dict[str, Any]:
    history = items or []
    if not history:
        summary = "Sem historico operacional registrado neste modulo."
    else:
        last = history[-1]
        summary = f"{len(history)} registros no historico; ultimo evento: {last.get('event_type') or last.get('action_type') or 'registro'}."
    return {"summary": summary, "metadata": _human_review_metadata("history_summary")}


def suggest_reply(context: dict[str, Any]) -> dict[str, Any]:
    name = first_name(str(context.get("person_name") or ""))
    pillar = context.get("pillar")
    event_type = str(context.get("event_type") or "")
    if pillar == "sales":
        message = f"Oi {name}, passando para acompanhar sua decisao e tirar qualquer duvida antes do proximo passo."
    elif pillar == "acquisition":
        message = f"Oi {name}, recebi seu contato. Posso te ajudar a entender a melhor opcao para o que voce precisa?"
    elif event_type in {"low_frequency", "inactive_customer", "no_checkin_7_days"}:
        message = f"Oi {name}, notei que sua rotina ficou parada. Quer que eu te ajude a retomar com um proximo passo simples?"
    else:
        message = f"Oi {name}, tudo bem? Estou passando para acompanhar seu atendimento e combinar o proximo passo."
    return {
        "message": message,
        "requires_human_approval": True,
        "metadata": _human_review_metadata("reply_suggestion", pillar=pillar, event_type=event_type),
    }


def generate_follow_up_message(context: dict[str, Any]) -> dict[str, Any]:
    name = first_name(str(context.get("person_name") or ""))
    event_type = str(context.get("event_type") or "")
    if event_type in {"proposal_no_response", "simulation_no_response"}:
        message = f"Oi {name}, passando para acompanhar a proposta e entender se ficou alguma duvida para avancarmos."
    elif event_type == "new_contact":
        message = f"Oi {name}, recebi seu contato. Qual objetivo voce quer resolver primeiro?"
    else:
        message = f"Oi {name}, faz sentido retomarmos essa conversa hoje e definir o proximo passo?"
    return {
        "message": message,
        "requires_human_approval": True,
        "metadata": _human_review_metadata("follow_up_message", event_type=event_type),
    }


def generate_post_sale_message(context: dict[str, Any]) -> dict[str, Any]:
    name = first_name(str(context.get("person_name") or ""))
    event_type = str(context.get("event_type") or "")
    if event_type in {"low_frequency", "no_checkin_7_days", "inactive_customer"}:
        message = f"Oi {name}, senti sua falta. Quer que eu te ajude a encaixar um retorno simples esta semana?"
    elif event_type in {"payment_overdue", "plan_expiring", "contract_expiring"}:
        message = f"Oi {name}, tem uma pendencia que pode interromper sua continuidade. Posso te ajudar a resolver?"
    else:
        message = f"Oi {name}, passando para acompanhar sua experiencia e garantir que o proximo passo esta claro."
    return {
        "message": message,
        "requires_human_approval": True,
        "metadata": _human_review_metadata("post_sale_message", event_type=event_type),
    }


def generate_weekly_report(metrics: dict[str, Any]) -> dict[str, Any]:
    recommendations = list(metrics.get("recommendations") or [])
    if not recommendations:
        recommendations = [
            "Priorizar tarefas vencidas antes de abrir novos ciclos.",
            "Revisar contatos sem resposta e separar casos comerciais de retencao.",
        ]
    bottlenecks = list(metrics.get("bottlenecks") or [])
    if not bottlenecks:
        bottlenecks = ["Nenhum gargalo critico identificado com os dados atuais."]

    summary = (
        f"Semana com {metrics.get('tasks_created', 0)} tarefas criadas, "
        f"{metrics.get('tasks_completed', 0)} concluidas e "
        f"{metrics.get('closed_sales', 0)} fechamentos medidos."
    )
    markdown = "\n".join(
        [
            "# Relatorio semanal Cordex Method OS",
            "",
            f"- Tarefas criadas: {metrics.get('tasks_created', 0)}",
            f"- Tarefas concluidas: {metrics.get('tasks_completed', 0)}",
            f"- Leads/prospects: {metrics.get('leads', 0)}",
            f"- Oportunidades abertas: {metrics.get('opportunities', 0)}",
            f"- Vendas/renovacoes medidas: {metrics.get('closed_sales', 0)}",
            f"- Clientes em risco: {metrics.get('risk_customers', 0)}",
            f"- Clientes recuperados: {metrics.get('recovered_customers', 0)}",
            "",
            "## Gargalos",
            *[f"- {item}" for item in bottlenecks],
            "",
            "## Recomendacoes",
            *[f"- {item}" for item in recommendations],
        ]
    )
    return {
        "summary": summary,
        "markdown": markdown,
        "bottlenecks": bottlenecks,
        "recommendations": recommendations,
        "requires_human_review": True,
        "metadata": _human_review_metadata("weekly_report"),
    }
