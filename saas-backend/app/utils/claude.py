import json
import logging
import re

import anthropic

from app.core.config import settings
from app.models.enums import NPSSentiment


logger = logging.getLogger(__name__)


def _fallback_sentiment(score: int, comment: str | None) -> tuple[NPSSentiment, str]:
    if score <= 6:
        return NPSSentiment.NEGATIVE, "Aluno detrator com risco de churn."
    if score <= 8:
        return NPSSentiment.NEUTRAL, "Aluno neutro, oportunidade de melhoria."
    return NPSSentiment.POSITIVE, "Aluno promotor com alto potencial de indicacao."


def analyze_sentiment(score: int, comment: str | None) -> tuple[NPSSentiment, str]:
    if not settings.claude_api_key or not comment:
        return _fallback_sentiment(score, comment)

    client = anthropic.Anthropic(api_key=settings.claude_api_key)
    prompt = (
        "Analise o sentimento de feedback NPS para academia.\n"
        "Retorne JSON com campos: sentiment (positive|neutral|negative), summary.\n"
        f"Score: {score}\n"
        f"Comentario: {comment}\n"
    )
    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        parsed = _parse_claude_json(text)
        sentiment = NPSSentiment(parsed["sentiment"])
        summary = parsed["summary"][:500]
        return sentiment, summary
    except Exception:
        logger.exception("Fallback em analise de sentimento Claude")
        return _fallback_sentiment(score, comment)


def _parse_claude_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        return json.loads(fenced.group(1))

    inline = re.search(r"(\{.*\})", text, flags=re.S)
    if inline:
        return json.loads(inline.group(1))

    raise ValueError("Resposta Claude nao contem JSON valido")
