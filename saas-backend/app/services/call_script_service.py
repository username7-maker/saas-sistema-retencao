import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import dashboard_cache, make_cache_key
from app.core.config import settings
from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import Lead, LeadStage, Task, TaskPriority, TaskStatus
from app.schemas.lead import LeadUpdate
from app.schemas.sales import CallEventCreate
from app.services.audit_service import log_audit_event
from app.services.crm_service import append_lead_note, update_lead
from app.services.proposal_service import generate_and_send_for_lead
from app.services.sales_brief_service import get_sales_brief
from app.services.whatsapp_service import send_whatsapp_sync

logger = logging.getLogger(__name__)
CALL_SCRIPT_CACHE_TTL_SECONDS = 2 * 60 * 60


def get_call_script(db: Session, lead_id: UUID) -> dict[str, Any]:
    lead = db.scalar(select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None)))
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead nao encontrado")

    cache_key = make_cache_key("call_script", lead_id)
    cached = dashboard_cache.get(cache_key)
    if isinstance(cached, dict):
        return cached

    brief = get_sales_brief(db, lead_id)
    objections = _known_objections_from_brief(brief)
    fallback = _fallback_script(lead, brief, objections)

    if not settings.claude_api_key:
        dashboard_cache.set(cache_key, fallback, ttl=CALL_SCRIPT_CACHE_TTL_SECONDS)
        return fallback

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        prompt = (
            "Voce e um closer de SaaS B2B para academias. "
            "Retorne JSON com opening, qualification_questions, presentation_points, objections, closing e quick_responses. "
            "opening e closing devem ser curtos. qualification_questions e presentation_points devem ter 2 ou 3 itens. "
            "quick_responses precisa ter chaves preco, sistema, tempo.\n"
            f"Briefing consolidado: {brief}\n"
        )
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = _parse_ai_json(response.content[0].text.strip())
        result = {
            "lead_id": lead.id,
            "opening": parsed.get("opening") or fallback["opening"],
            "qualification_questions": parsed.get("qualification_questions") or fallback["qualification_questions"],
            "presentation_points": parsed.get("presentation_points") or fallback["presentation_points"],
            "objections": parsed.get("objections") or fallback["objections"],
            "closing": parsed.get("closing") or fallback["closing"],
            "quick_responses": parsed.get("quick_responses") or fallback["quick_responses"],
        }
        dashboard_cache.set(cache_key, result, ttl=CALL_SCRIPT_CACHE_TTL_SECONDS)
        return result
    except Exception:
        logger.exception("Falha ao gerar call script com Claude")
        dashboard_cache.set(cache_key, fallback, ttl=CALL_SCRIPT_CACHE_TTL_SECONDS)
        return fallback


def register_call_event(
    db: Session,
    *,
    lead_id: UUID,
    payload: CallEventCreate,
) -> Lead:
    lead = db.scalar(select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None)))
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead nao encontrado")

    event_type = payload.event_type.strip().lower()
    details = {"event_type": event_type, "label": payload.label, "details": payload.details, "next_step": payload.next_step}
    append_lead_note(
        db,
        lead,
        {
            "type": "call_event",
            "event_type": event_type,
            "label": payload.label,
            "details": payload.details,
            "next_step": payload.next_step,
            "lost_reason": payload.lost_reason,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        },
    )

    if event_type == "lost":
        lead.stage = LeadStage.LOST
        lead.lost_reason = payload.lost_reason or lead.lost_reason
    elif event_type == "proposal_requested":
        lead.stage = LeadStage.PROPOSAL_SENT
        lead.last_contact_at = datetime.now(tz=timezone.utc)
        append_lead_note(
            db,
            lead,
            {
                "type": "proposal_requested",
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
                "source": "call_script",
            },
        )
    elif event_type == "close_now":
        lead = update_lead(db, lead.id, LeadUpdate(stage=LeadStage.WON))
    elif event_type == "interest_confirmed":
        lead.last_contact_at = datetime.now(tz=timezone.utc)

    db.add(lead)
    log_audit_event(
        db,
        action="call_event_logged",
        entity="lead",
        gym_id=lead.gym_id,
        entity_id=lead.id,
        details=details,
    )
    db.commit()
    _invalidate_sales_cache(lead.id)
    return lead


def send_lead_proposal_background(lead_id: UUID) -> None:
    db = SessionLocal()
    try:
        lead = db.get(Lead, lead_id)
        if not lead or lead.deleted_at is not None:
            return
        set_current_gym_id(lead.gym_id)
        result = generate_and_send_for_lead(db, lead_id)
        append_lead_note(
            db,
            lead,
            {
                "type": "proposal_sent_auto",
                "emailed": result["emailed"],
                "filename": result["filename"],
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        log_audit_event(
            db,
            action="proposal_sent_background",
            entity="lead",
            gym_id=lead.gym_id,
            entity_id=lead.id,
            details={"emailed": result["emailed"], "filename": result["filename"]},
        )
        if lead.phone and result["emailed"]:
            send_whatsapp_sync(
                db,
                phone=lead.phone,
                message="Sua proposta foi enviada por email. Se quiser, eu tambem posso te explicar os numeros na call.",
                lead_id=lead.id,
                template_name="custom",
                direction="outbound",
                event_type="proposal_sent_confirmation",
            )
        db.commit()
        _invalidate_sales_cache(lead.id)
    except Exception:
        logger.exception("Falha ao gerar proposta automatica para lead %s", lead_id)
        log_audit_event(
            db,
            action="proposal_sent_background_failed",
            entity="lead",
            entity_id=lead_id,
            details={"lead_id": str(lead_id)},
        )
        db.commit()
    finally:
        clear_current_gym_id()
        db.close()


def process_proposal_followups(db: Session) -> dict[str, int]:
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(hours=settings.proposal_followup_delay_hours)
    leads = list(
        db.scalars(
            select(Lead).where(
                Lead.stage == LeadStage.PROPOSAL_SENT,
                Lead.deleted_at.is_(None),
            )
        ).all()
    )

    created = 0
    for lead in leads:
        proposal_requested_at = _latest_proposal_requested_at(lead)
        if not proposal_requested_at or proposal_requested_at > cutoff:
            continue

        existing_task = db.scalar(
            select(Task).where(
                Task.lead_id == lead.id,
                Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
                Task.deleted_at.is_(None),
                Task.title.ilike("%follow-up proposta%"),
            )
        )
        if existing_task:
            continue

        task = Task(
            lead_id=lead.id,
            assigned_to_user_id=lead.owner_id,
            title=f"Follow-up proposta - {lead.full_name}",
            description="Proposta enviada ha 24h sem conversao para WON ou LOST.",
            priority=TaskPriority.HIGH,
            status=TaskStatus.TODO,
            kanban_column=TaskStatus.TODO.value,
            due_date=now,
        )
        db.add(task)
        created += 1
        log_audit_event(
            db,
            action="proposal_auto_followup_created",
            entity="lead",
            gym_id=lead.gym_id,
            entity_id=lead.id,
            details={"proposal_requested_at": proposal_requested_at.isoformat()},
        )

    db.commit()
    return {"created": created}


def _latest_proposal_requested_at(lead: Lead) -> datetime | None:
    latest = None
    for note in lead.notes or []:
        if not isinstance(note, dict):
            continue
        if note.get("type") not in {"proposal_requested", "proposal_sent_auto"}:
            continue
        raw = note.get("created_at")
        if not raw:
            continue
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if latest is None or parsed > latest:
            latest = parsed
    return latest


def _known_objections_from_brief(brief: dict[str, Any]) -> list[dict[str, str]]:
    objections: list[dict[str, str]] = []
    for item in brief.get("history", []):
        if item.get("kind") != "objection":
            continue
        objections.append(
            {
                "summary": "Objecao detectada",
                "response_text": str(item.get("detail") or ""),
                "source": "history",
            }
        )
    return objections


def _fallback_script(lead: Lead, brief: dict[str, Any], objections: list[dict[str, str]]) -> dict[str, Any]:
    diagnosis = brief["diagnosis"]
    opening = (
        f"Quero usar seus numeros para ir direto ao ponto: hoje ha R$ {diagnosis['mrr_at_risk']:,.2f} em risco."
        if diagnosis["has_diagnosis"]
        else "Quero entender seu churn e a inatividade para te mostrar rapidamente onde a receita esta escapando."
    )
    qualification = [
        "Hoje, como voces acompanham alunos inativos e quem executa esse contato?",
        "Qual meta de crescimento ou retencao voces querem proteger nos proximos 90 dias?",
        "O time comercial ou operacional sente falta de automacao em algum ponto especifico?",
    ]
    presentation = [
        "Mostre primeiro o painel de risco e como o score prioriza alunos que realmente precisam de acao.",
        "Mostre depois as automacoes e tarefas que reduzem trabalho manual da equipe.",
        "Feche com BI financeiro conectando recuperacao de receita ao investimento.",
    ]
    if not objections:
        objections = [
            {
                "summary": "Preco",
                "response_text": f"O ROI precisa ser comparado com os R$ {diagnosis['annual_loss_projection']:,.2f} projetados de perda anual.",
                "source": "fallback",
            }
        ]
    closing = "Se fizer sentido, o proximo passo e sair desta call com proposta enviada e follow-up combinado."
    return {
        "lead_id": lead.id,
        "opening": opening,
        "qualification_questions": qualification,
        "presentation_points": presentation,
        "objections": objections,
        "closing": closing,
        "quick_responses": {
            "preco": f"O custo precisa ser comparado com R$ {diagnosis['annual_loss_projection']:,.2f} de perda anual projetada.",
            "sistema": "Nao substitui seu sistema de gestao; entra como camada de retencao, BI e automacao comercial.",
            "tempo": "A proposta central e reduzir trabalho manual, nao criar mais uma rotina para a equipe.",
        },
    }


def _invalidate_sales_cache(lead_id: UUID) -> None:
    dashboard_cache.delete(make_cache_key("sales_brief", lead_id))
    dashboard_cache.delete(make_cache_key("call_script", lead_id))


def _parse_ai_json(text: str) -> dict[str, Any]:
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

    raise ValueError("Resposta AI invalida para call script")
