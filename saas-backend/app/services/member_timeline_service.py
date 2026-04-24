import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Checkin, NPSResponse, RiskAlert, Task
from app.models.assessment import Assessment, MemberConstraints, MemberGoal, TrainingPlan
from app.models.body_composition import BodyCompositionEvaluation

logger = logging.getLogger(__name__)


def get_member_timeline(db: Session, member_id: UUID, limit: int = 50) -> list[dict]:
    events: list[dict] = []

    assessments = db.scalars(
        select(Assessment)
        .where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
        .order_by(Assessment.assessment_date.desc())
        .limit(10)
    ).all()
    for assessment in assessments:
        parts = []
        weight_kg = getattr(assessment, "weight_kg", None)
        body_fat_pct = getattr(assessment, "body_fat_pct", None)
        strength_score = getattr(assessment, "strength_score", None)
        if weight_kg is not None:
            parts.append(f"Peso: {weight_kg} kg")
        if body_fat_pct is not None:
            parts.append(f"Gordura: {body_fat_pct}%")
        if strength_score is not None:
            parts.append(f"Forca: {strength_score}")
        events.append({
            "type": "assessment",
            "timestamp": assessment.assessment_date.isoformat(),
            "title": f"Avaliacao #{assessment.assessment_number}",
            "detail": " | ".join(parts) if parts else "Avaliacao registrada",
            "icon": "clipboard-list",
        })

    constraints = db.scalar(
        select(MemberConstraints)
        .where(MemberConstraints.member_id == member_id, MemberConstraints.deleted_at.is_(None))
        .order_by(MemberConstraints.updated_at.desc())
        .limit(1)
    )
    if constraints:
        parts = []
        if constraints.medical_conditions:
            parts.append(f"Saude: {constraints.medical_conditions}")
        if constraints.injuries:
            parts.append(f"Lesoes: {constraints.injuries}")
        if constraints.contraindications:
            parts.append(f"Contraindicacoes: {constraints.contraindications}")
        events.append({
            "type": "constraints",
            "timestamp": constraints.updated_at.isoformat(),
            "title": "Restricoes atualizadas",
            "detail": " | ".join(parts) if parts else "Restricoes registradas",
            "icon": "shield-alert",
        })

    goals = db.scalars(
        select(MemberGoal)
        .where(MemberGoal.member_id == member_id, MemberGoal.deleted_at.is_(None))
        .order_by(MemberGoal.updated_at.desc())
        .limit(10)
    ).all()
    for goal in goals:
        events.append({
            "type": "goal",
            "timestamp": goal.updated_at.isoformat(),
            "title": f"Objetivo: {goal.title}",
            "detail": f"Status: {goal.status} | Progresso: {goal.progress_pct}%",
            "icon": "target",
        })

    training_plans = db.scalars(
        select(TrainingPlan)
        .where(TrainingPlan.member_id == member_id, TrainingPlan.deleted_at.is_(None))
        .order_by(TrainingPlan.updated_at.desc())
        .limit(10)
    ).all()
    for plan in training_plans:
        parts = []
        if plan.objective:
            parts.append(f"Objetivo: {plan.objective}")
        parts.append(f"{plan.sessions_per_week}x por semana")
        if plan.split_type:
            parts.append(f"Divisao: {plan.split_type}")
        events.append({
            "type": "training_plan",
            "timestamp": plan.updated_at.isoformat(),
            "title": f"Treino: {plan.name}",
            "detail": " | ".join(parts),
            "icon": "dumbbell",
        })

    checkins = db.scalars(
        select(Checkin)
        .where(Checkin.member_id == member_id)
        .order_by(Checkin.checkin_at.desc())
        .limit(limit)
    ).all()
    for checkin in checkins:
        events.append({
            "type": "checkin",
            "timestamp": checkin.checkin_at.isoformat(),
            "title": "Check-in",
            "detail": f"Fonte: {checkin.source.value if hasattr(checkin.source, 'value') else checkin.source}",
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
            "title": f"Alerta de risco - {level.upper()}",
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
            label = f"[Plano {plan_type.capitalize()}] " if plan_type else "[Plano] "

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
            AuditLog.action.in_([
                "whatsapp_sent_manually",
                "automation_3d",
                "automation_7d",
                "automation_10d",
                "automation_14d",
                "automation_21d",
            ]),
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
        body_composition_items = db.scalars(
            select(BodyCompositionEvaluation)
            .where(BodyCompositionEvaluation.member_id == member_id)
            .order_by(BodyCompositionEvaluation.evaluation_date.desc())
            .limit(10)
        ).all()
    except Exception:
        db.rollback()
        logger.warning("Nao foi possivel carregar eventos de bioimpedancia no timeline.")
        body_composition_items = []
    for body_item in body_composition_items:
        source_label = "Tezewa" if body_item.source == "tezewa" else "Manual"
        parts = []
        if body_item.weight_kg is not None:
            parts.append(f"Peso: {body_item.weight_kg} kg")
        if body_item.body_fat_percent is not None:
            parts.append(f"Gordura: {body_item.body_fat_percent}%")
        if body_item.muscle_mass_kg is not None:
            parts.append(f"Musculo: {body_item.muscle_mass_kg} kg")
        events.append({
            "type": "body_composition",
            "timestamp": body_item.evaluation_date.isoformat(),
            "title": f"Bioimpedancia ({source_label})",
            "detail": " | ".join(parts) if parts else "Avaliacao registrada",
            "icon": "scan-line",
        })

    events.sort(key=lambda event: event["timestamp"], reverse=True)
    return events[:limit]
