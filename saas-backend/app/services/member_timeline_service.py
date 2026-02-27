import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Checkin, NPSResponse, RiskAlert, Task
from app.models.body_composition import BodyCompositionEvaluation

logger = logging.getLogger(__name__)


def get_member_timeline(db: Session, member_id: UUID, limit: int = 50) -> list[dict]:
    events: list[dict] = []

    checkins = db.scalars(
        select(Checkin)
        .where(Checkin.member_id == member_id)
        .order_by(Checkin.checkin_at.desc())
        .limit(limit)
    ).all()
    for c in checkins:
        events.append({
            "type": "checkin",
            "timestamp": c.checkin_at.isoformat(),
            "title": "Check-in",
            "detail": f"Fonte: {c.source.value if hasattr(c.source, 'value') else c.source}",
            "icon": "activity",
        })

    risk_alerts = db.scalars(
        select(RiskAlert)
        .where(RiskAlert.member_id == member_id)
        .order_by(RiskAlert.created_at.desc())
        .limit(20)
    ).all()
    for alert in risk_alerts:
        level = alert.level.value if hasattr(alert.level, "value") else alert.level
        events.append({
            "type": "risk_alert",
            "timestamp": alert.created_at.isoformat(),
            "title": f"Alerta de Risco - {level.upper()}",
            "detail": f"Score: {alert.score}. {'Resolvido' if alert.resolved else 'Ativo'}",
            "icon": "alert-triangle",
            "level": level,
        })

    nps_responses = db.scalars(
        select(NPSResponse)
        .where(NPSResponse.member_id == member_id)
        .order_by(NPSResponse.created_at.desc())
        .limit(20)
    ).all()
    for nps in nps_responses:
        sentiment = nps.sentiment.value if hasattr(nps.sentiment, "value") else nps.sentiment
        events.append({
            "type": "nps",
            "timestamp": nps.created_at.isoformat(),
            "title": f"NPS: {nps.score}",
            "detail": f"Sentimento: {sentiment}",
            "icon": "star",
        })

    tasks = db.scalars(
        select(Task)
        .where(Task.member_id == member_id, Task.deleted_at.is_(None))
        .order_by(Task.created_at.desc())
        .limit(20)
    ).all()
    for task in tasks:
        status = task.status.value if hasattr(task.status, "value") else task.status
        priority = task.priority.value if hasattr(task.priority, "value") else task.priority
        source = ""
        plan_type = ""
        if task.extra_data:
            raw_source = task.extra_data.get("source")
            raw_plan_type = task.extra_data.get("plan_type")
            source = str(raw_source).lower() if raw_source else ""
            plan_type = str(raw_plan_type).lower() if raw_plan_type else ""

        label = ""
        if source == "onboarding":
            label = "[Onboarding] "
        elif source == "plan_followup":
            if plan_type:
                label = f"[Plano {plan_type.capitalize()}] "
            else:
                label = "[Plano] "

        details = [
            f"Status: {status}",
            f"Prioridade: {priority}",
        ]
        if task.due_date:
            details.append(f"Vencimento: {task.due_date.strftime('%d/%m/%Y')}")

        events.append({
            "type": "task",
            "timestamp": task.created_at.isoformat(),
            "title": f"{label}{task.title}" if label else task.title,
            "detail": " | ".join(details),
            "icon": "clipboard",
        })

    audit_events = db.scalars(
        select(AuditLog)
        .where(
            AuditLog.member_id == member_id,
            AuditLog.action.in_(["whatsapp_sent_manually", "automation_3d", "automation_7d", "automation_10d", "automation_14d", "automation_21d"]),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(20)
    ).all()
    for event in audit_events:
        events.append({
            "type": "automation",
            "timestamp": event.created_at.isoformat(),
            "title": f"Automacao: {event.action}",
            "detail": str(event.details) if event.details else "",
            "icon": "zap",
        })

    try:
        bce_list = db.scalars(
            select(BodyCompositionEvaluation)
            .where(BodyCompositionEvaluation.member_id == member_id)
            .order_by(BodyCompositionEvaluation.evaluation_date.desc())
            .limit(10)
        ).all()
    except Exception:
        db.rollback()
        logger.warning("Nao foi possivel carregar eventos de bioimpedancia no timeline.")
        bce_list = []
    for bce in bce_list:
        source_label = "Tezewa" if bce.source == "tezewa" else "Manual"
        parts = []
        if bce.weight_kg is not None:
            parts.append(f"Peso: {bce.weight_kg} kg")
        if bce.body_fat_percent is not None:
            parts.append(f"Gordura: {bce.body_fat_percent}%")
        if bce.muscle_mass_kg is not None:
            parts.append(f"Músculo: {bce.muscle_mass_kg} kg")
        events.append({
            "type": "body_composition",
            "timestamp": bce.evaluation_date.isoformat(),
            "title": f"Bioimpedância ({source_label})",
            "detail": " | ".join(parts) if parts else "Avaliação registrada",
            "icon": "activity",
        })

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events[:limit]
