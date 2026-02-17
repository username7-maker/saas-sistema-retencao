import logging
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache, make_cache_key
from app.core.config import settings

logger = logging.getLogger(__name__)
INSIGHT_CACHE_TTL_SECONDS = 3600


def generate_executive_insight(db: Session, dashboard_data: dict) -> str:
    cache_key = make_cache_key("dashboard_insight_executive")
    cached = dashboard_cache.get(cache_key)
    if isinstance(cached, str):
        return cached

    prompt = _build_executive_prompt(db, dashboard_data)

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


def generate_retention_insight(db: Session, retention_data: dict) -> str:
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
            name = item.get("full_name", item.get("fullName", "?"))
            score = item.get("risk_score", item.get("riskScore", "?"))
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


def _build_executive_prompt(db: Session, data: dict) -> str:
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
