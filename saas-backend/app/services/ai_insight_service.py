import logging

from app.core.cache import dashboard_cache, make_cache_key
from app.core.config import settings

logger = logging.getLogger(__name__)
INSIGHT_CACHE_TTL_SECONDS = 3600


def generate_executive_insight(dashboard_data: dict) -> str:
    cache_key = make_cache_key("dashboard_insight_executive")
    cached = dashboard_cache.get(cache_key)
    if isinstance(cached, str):
        return cached

    prompt = _build_executive_prompt(dashboard_data)

    if not settings.claude_api_key:
        insight = _fallback_insight(dashboard_data)
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        insight = response.content[0].text
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight
    except Exception:
        logger.exception("Erro ao gerar insight com Claude")
        insight = _fallback_insight(dashboard_data)
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight


def generate_retention_insight(retention_data: dict) -> str:
    cache_key = make_cache_key("dashboard_insight_retention")
    cached = dashboard_cache.get(cache_key)
    if isinstance(cached, str):
        return cached

    red_count = retention_data.get("red", {}).get("total", 0)
    yellow_count = retention_data.get("yellow", {}).get("total", 0)
    red_items = retention_data.get("red", {}).get("items", [])

    prompt = (
        "Voce e um consultor de retencao de academias. Analise os dados abaixo e de 2-3 recomendacoes "
        "praticas e acionaveis em portugues brasileiro. Seja direto e conciso (max 150 palavras).\n\n"
        f"Alunos em risco vermelho: {red_count}\n"
        f"Alunos em risco amarelo: {yellow_count}\n"
    )

    if red_items:
        top_red = red_items[:5]
        prompt += "\nTop alunos vermelhos:\n"
        for item in top_red:
            if isinstance(item, dict):
                name = item.get("full_name") or item.get("fullName") or item.get("name") or "?"
                score = item.get("risk_score") or item.get("riskScore") or item.get("risk") or "?"
            else:
                name = getattr(item, "full_name", None) or getattr(item, "fullName", None) or getattr(item, "name", None) or "?"
                score = getattr(item, "risk_score", None) or getattr(item, "riskScore", None) or getattr(item, "risk", None) or "?"
            prompt += f"- {name} (score: {score})\n"

    if not settings.claude_api_key:
        insight = _fallback_retention_insight(red_count, yellow_count)
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        insight = response.content[0].text
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight
    except Exception:
        logger.exception("Erro ao gerar insight de retencao com Claude")
        insight = _fallback_retention_insight(red_count, yellow_count)
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight


def _build_executive_prompt(data: dict) -> str:
    total = data.get("total_members", 0)
    active = data.get("active_members", 0)
    mrr = data.get("mrr", 0)
    churn = data.get("churn_rate", 0)
    nps = data.get("nps_avg", 0)
    risk = data.get("risk_distribution", {})
    red = risk.get("red", 0)
    yellow = risk.get("yellow", 0)
    green = risk.get("green", 0)

    return (
        "Voce e um consultor de gestao de academias. Analise os KPIs abaixo e de 2-3 insights "
        "praticos e acionaveis em portugues brasileiro. Seja direto e conciso (max 150 palavras). "
        "Foque no que o gestor DEVE FAZER, nao apenas descreva os numeros.\n\n"
        f"Total de alunos: {total}\n"
        f"Alunos ativos: {active}\n"
        f"MRR: R$ {mrr:.2f}\n"
        f"Taxa de churn: {churn:.2f}%\n"
        f"NPS medio: {nps:.2f}\n"
        f"Distribuicao de risco: Verde={green}, Amarelo={yellow}, Vermelho={red}\n"
    )


def _fallback_insight(data: dict) -> str:
    churn = data.get("churn_rate", 0)
    red = data.get("risk_distribution", {}).get("red", 0)
    yellow = data.get("risk_distribution", {}).get("yellow", 0)
    nps = data.get("nps_avg", 0)

    insights = []

    if churn > 5:
        insights.append(
            f"Sua taxa de churn ({churn:.1f}%) esta acima do ideal para academias (3-5%). "
            "Foque em acoes de retencao para os alunos em risco."
        )
    elif churn > 3:
        insights.append(
            f"Sua taxa de churn ({churn:.1f}%) esta dentro da media. "
            "Continue monitorando os alunos amarelos para evitar escalada."
        )

    if red > 0:
        insights.append(
            f"{red} aluno(s) em risco vermelho precisam de contato imediato. "
            "Priorize ligacoes e WhatsApp para estes alunos hoje."
        )

    if nps < 7:
        insights.append(
            f"NPS medio ({nps:.1f}) abaixo do ideal. "
            "Considere pesquisas qualitativas para entender insatisfacao."
        )

    if not insights:
        insights.append("Indicadores saudaveis. Mantenha o foco em engajamento e retencao proativa.")

    return " ".join(insights)


def generate_operational_insight(dashboard_data: dict) -> str:
    cache_key = make_cache_key("dashboard_insight_operational")
    cached = dashboard_cache.get(cache_key)
    if isinstance(cached, str):
        return cached

    checkins_today = dashboard_data.get("realtime_checkins", 0)
    inactive_7d = dashboard_data.get("inactive_7d_total", 0)
    heatmap = dashboard_data.get("heatmap", [])
    peak_hour = _find_peak_hour(heatmap)

    prompt = (
        "Voce e um consultor operacional de academias. Analise os dados abaixo e de 2-3 recomendacoes "
        "praticas e acionaveis em portugues brasileiro. Seja direto e conciso (max 150 palavras).\n\n"
        f"Check-ins hoje: {checkins_today}\n"
        f"Alunos inativos ha 7+ dias: {inactive_7d}\n"
        f"Horario de pico: {peak_hour}\n"
    )

    if not settings.claude_api_key:
        insight = _fallback_operational_insight(checkins_today, inactive_7d, peak_hour)
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        insight = response.content[0].text
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight
    except Exception:
        logger.exception("Erro ao gerar insight operacional com Claude")
        insight = _fallback_operational_insight(checkins_today, inactive_7d, peak_hour)
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight


def generate_commercial_insight(dashboard_data: dict) -> str:
    cache_key = make_cache_key("dashboard_insight_commercial")
    cached = dashboard_cache.get(cache_key)
    if isinstance(cached, str):
        return cached

    pipeline = dashboard_data.get("pipeline_summary", {})
    total_leads = sum(pipeline.values()) if isinstance(pipeline, dict) else 0
    won = pipeline.get("won", 0) if isinstance(pipeline, dict) else 0
    lost = pipeline.get("lost", 0) if isinstance(pipeline, dict) else 0
    stale_leads = dashboard_data.get("stale_leads_count", 0)
    conversion_rate = dashboard_data.get("conversion_rate", 0)

    prompt = (
        "Voce e um consultor comercial de academias. Analise os dados abaixo e de 2-3 recomendacoes "
        "praticas e acionaveis em portugues brasileiro. Seja direto e conciso (max 150 palavras).\n\n"
        f"Total de leads: {total_leads}\n"
        f"Leads ganhos: {won}\n"
        f"Leads perdidos: {lost}\n"
        f"Leads estagnados: {stale_leads}\n"
        f"Taxa de conversao: {conversion_rate:.1f}%\n"
    )

    if not settings.claude_api_key:
        insight = _fallback_commercial_insight(total_leads, won, lost, stale_leads, conversion_rate)
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        insight = response.content[0].text
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight
    except Exception:
        logger.exception("Erro ao gerar insight comercial com Claude")
        insight = _fallback_commercial_insight(total_leads, won, lost, stale_leads, conversion_rate)
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight


def generate_financial_insight(dashboard_data: dict) -> str:
    cache_key = make_cache_key("dashboard_insight_financial")
    cached = dashboard_cache.get(cache_key)
    if isinstance(cached, str):
        return cached

    mrr = dashboard_data.get("mrr", 0)
    delinquency_rate = dashboard_data.get("delinquency_rate", 0)
    ltv = dashboard_data.get("ltv", 0)
    mrr_history = dashboard_data.get("mrr_history", [])
    mrr_trend = ""
    if len(mrr_history) >= 2:
        prev = mrr_history[-2].get("value", 0) if isinstance(mrr_history[-2], dict) else 0
        curr = mrr_history[-1].get("value", 0) if isinstance(mrr_history[-1], dict) else 0
        if prev > 0:
            pct = ((curr - prev) / prev) * 100
            mrr_trend = f"{pct:+.1f}% vs mes anterior"

    prompt = (
        "Voce e um consultor financeiro de academias. Analise os dados abaixo e de 2-3 recomendacoes "
        "praticas e acionaveis em portugues brasileiro. Seja direto e conciso (max 150 palavras).\n\n"
        f"MRR atual: R$ {mrr:.2f}\n"
        f"Taxa de inadimplencia: {delinquency_rate:.1f}%\n"
        f"LTV medio: R$ {ltv:.2f}\n"
        f"Tendencia MRR: {mrr_trend or 'sem historico suficiente'}\n"
    )

    if not settings.claude_api_key:
        insight = _fallback_financial_insight(mrr, delinquency_rate, ltv, mrr_trend)
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        insight = response.content[0].text
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight
    except Exception:
        logger.exception("Erro ao gerar insight financeiro com Claude")
        insight = _fallback_financial_insight(mrr, delinquency_rate, ltv, mrr_trend)
        dashboard_cache.set(cache_key, insight, ttl=INSIGHT_CACHE_TTL_SECONDS)
        return insight


def _find_peak_hour(heatmap: list) -> str:
    if not heatmap:
        return "indisponivel"
    best = max(heatmap, key=lambda p: p.get("count", 0) if isinstance(p, dict) else getattr(p, "count", 0))
    hour = best.get("hour", "?") if isinstance(best, dict) else getattr(best, "hour", "?")
    count = best.get("count", 0) if isinstance(best, dict) else getattr(best, "count", 0)
    return f"{hour}h ({count} check-ins)"


def _fallback_operational_insight(checkins: int, inactive: int, peak: str) -> str:
    parts = []
    if inactive > 10:
        parts.append(
            f"{inactive} alunos inativos ha 7+ dias. Envie mensagens de reengajamento urgentes "
            "para evitar cancelamentos."
        )
    if checkins == 0:
        parts.append("Nenhum check-in registrado hoje. Verifique o sistema de catracas.")
    elif peak != "indisponivel":
        parts.append(f"Pico de movimento as {peak}. Planeje escala de instrutores de acordo.")
    if not parts:
        parts.append("Operacao funcionando normalmente. Monitore inativos para acao preventiva.")
    return " ".join(parts)


def _fallback_commercial_insight(
    total: int, won: int, lost: int, stale: int, conv_rate: float
) -> str:
    parts = []
    if stale > 0:
        parts.append(
            f"{stale} leads estagnados sem contato recente. "
            "Priorize follow-up imediato para nao perder oportunidades."
        )
    if conv_rate < 20:
        parts.append(
            f"Taxa de conversao ({conv_rate:.0f}%) abaixo do ideal. "
            "Revise abordagem comercial e ofertas de trial."
        )
    if lost > won and total > 0:
        parts.append(
            f"Mais leads perdidos ({lost}) que ganhos ({won}). "
            "Analise motivos de perda e ajuste o pitch."
        )
    if not parts:
        parts.append("Pipeline comercial saudavel. Continue acompanhando leads ativos.")
    return " ".join(parts)


def _fallback_financial_insight(mrr: float, delinquency: float, ltv: float, trend: str) -> str:
    parts = []
    if delinquency > 10:
        parts.append(
            f"Inadimplencia alta ({delinquency:.0f}%). "
            "Implemente cobranca automatica e revise politica de pagamento."
        )
    elif delinquency > 5:
        parts.append(
            f"Inadimplencia moderada ({delinquency:.0f}%). "
            "Envie lembretes de pagamento proativos."
        )
    if trend and "-" in trend:
        parts.append(f"MRR em queda ({trend}). Foque em retencao e upsell de planos.")
    if not parts:
        parts.append("Indicadores financeiros estaveis. Monitore inadimplencia e mantenha MRR crescente.")
    return " ".join(parts)


def _fallback_retention_insight(red_count: int, yellow_count: int) -> str:
    if red_count > 0 and yellow_count > 0:
        return (
            f"Atencao: {red_count} aluno(s) em risco critico e {yellow_count} em risco moderado. "
            "Priorize contato telefonico para os vermelhos e WhatsApp para os amarelos. "
            "Alunos com mais de 14 dias inativos tem 70% mais chance de cancelar."
        )
    if red_count > 0:
        return (
            f"{red_count} aluno(s) precisam de acao urgente. "
            "Agende ligacoes hoje e oferea beneficios de reengajamento."
        )
    if yellow_count > 0:
        return (
            f"{yellow_count} aluno(s) em risco moderado. "
            "Envie mensagens de engajamento antes que evoluam para risco critico."
        )
    return "Nenhum aluno em risco no momento. Otimo trabalho de retencao!"
