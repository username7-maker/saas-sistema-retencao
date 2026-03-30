import logging
import re
import unicodedata
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Lead, LeadStage, NurturingSequence, ObjectionResponse
from app.schemas.objection import ObjectionResponseUpdate

logger = logging.getLogger(__name__)


def _normalize_text(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def _extract_context(
    db: Session,
    lead_id: UUID | None,
    context: dict | None,
    *,
    gym_scope: UUID | None = None,
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(context or {})
    if not lead_id:
        return merged

    seq_stmt = (
        select(NurturingSequence)
        .where(NurturingSequence.lead_id == lead_id)
        .order_by(NurturingSequence.created_at.desc())
        .limit(1)
    )
    if gym_scope:
        seq_stmt = seq_stmt.where(NurturingSequence.gym_id == gym_scope)
    seq = db.scalar(seq_stmt)
    if seq and isinstance(seq.diagnosis_data, dict):
        merged.update(seq.diagnosis_data)

    lead = db.get(Lead, lead_id)
    if lead and (gym_scope is None or lead.gym_id == gym_scope):
        merged.setdefault("lead_name", lead.full_name)
        merged.setdefault("lead_stage", lead.stage.value)
    return merged


def _keyword_match(message_text: str, objections: list[ObjectionResponse]) -> ObjectionResponse | None:
    haystack = _normalize_text(message_text)
    best_match: tuple[int, ObjectionResponse] | None = None
    for item in objections:
        keywords = [str(k).strip() for k in (item.trigger_keywords or []) if str(k).strip()]
        for keyword in keywords:
            normalized_keyword = _normalize_text(keyword)
            if not normalized_keyword:
                continue
            if normalized_keyword in haystack:
                score = len(normalized_keyword)
                if not best_match or score > best_match[0]:
                    best_match = (score, item)
    return best_match[1] if best_match else None


def _render_template(template: str, context: dict[str, Any]) -> str:
    safe_context = {k: v for k, v in context.items() if isinstance(k, str)}
    try:
        return template.format_map({**safe_context})
    except Exception:
        return template


def _personalize_with_claude(base_response: str, message_text: str, context: dict[str, Any]) -> str:
    if not settings.claude_api_key:
        return base_response

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        prompt = (
            "Voce e um SDR de SaaS B2B para academias. Personalize a resposta abaixo "
            "de forma curta (max 120 palavras), profissional e objetiva. "
            "Mantenha a proposta central da resposta base.\n"
            f"Mensagem do prospect: {message_text}\n"
            f"Contexto: {context}\n"
            f"Resposta base: {base_response}\n"
        )
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()[:1200] or base_response
    except Exception:
        logger.exception("Falha ao personalizar resposta de objecao com Claude")
        return base_response


def generate_objection_response(
    db: Session,
    *,
    message_text: str,
    lead_id: UUID | None = None,
    context: dict | None = None,
    public_gym_id: UUID | None = None,
) -> dict[str, Any]:
    filters = [ObjectionResponse.is_active.is_(True)]
    if public_gym_id:
        filters.append(or_(ObjectionResponse.gym_id.is_(None), ObjectionResponse.gym_id == public_gym_id))
    else:
        filters.append(ObjectionResponse.gym_id.is_(None))

    objections = list(db.scalars(select(ObjectionResponse).where(*filters)).all())
    merged_context = _extract_context(db, lead_id, context, gym_scope=public_gym_id)

    matched = _keyword_match(message_text, objections)
    if matched:
        base_response = _render_template(matched.response_template, merged_context)
        personalized = _personalize_with_claude(base_response, message_text, merged_context)
        source = "keyword_ai" if settings.claude_api_key else "keyword_rule"
        return {
            "matched": True,
            "objection_id": matched.id,
            "response_text": personalized,
            "source": source,
        }

    generic = (
        "Entendi seu ponto. Posso te mostrar em 15 minutos, com os dados da sua academia, "
        "como reduzir churn e recuperar receita com automacao. Quer que eu te envie um horario?"
    )
    return {
        "matched": False,
        "objection_id": None,
        "response_text": generic,
        "source": "generic",
    }


def list_admin_objections(db: Session, admin_gym_id: UUID) -> list[ObjectionResponse]:
    return list(
        db.scalars(
            select(ObjectionResponse).where(
                or_(ObjectionResponse.gym_id.is_(None), ObjectionResponse.gym_id == admin_gym_id)
            )
        ).all()
    )


def update_admin_objection(
    db: Session,
    *,
    objection_id: UUID,
    admin_gym_id: UUID,
    payload: ObjectionResponseUpdate,
) -> ObjectionResponse:
    item = db.get(ObjectionResponse, objection_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objecao nao encontrada")

    if item.gym_id not in {None, admin_gym_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Objecao fora do escopo administrativo")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(item, key, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def mark_sequence_completed_if_won(db: Session, lead_id: UUID) -> None:
    lead = db.get(Lead, lead_id)
    if not lead or lead.stage != LeadStage.WON:
        return
    sequences = list(
        db.scalars(
            select(NurturingSequence).where(
                NurturingSequence.lead_id == lead_id,
                NurturingSequence.completed.is_(False),
            )
        ).all()
    )
    for seq in sequences:
        seq.completed = True
        details = dict(seq.diagnosis_data or {})
        details["stop_reason"] = "lead_won"
        seq.diagnosis_data = details
        db.add(seq)
    db.commit()
