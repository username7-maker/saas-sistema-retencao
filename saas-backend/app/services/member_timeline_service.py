from datetime import datetime
from uuid import UUID

from sqlalchemy import select, union_all
from sqlalchemy.orm import Session

from app.models import AuditLog, Checkin, NPSResponse, RiskAlert, Task


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
        events.append({
            "type": "task",
            "timestamp": task.created_at.isoformat(),
            "title": task.title,
            "detail": f"Status: {status} | Prioridade: {task.priority.value if hasattr(task.priority, 'value') else task.priority}",
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

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events[:limit]
