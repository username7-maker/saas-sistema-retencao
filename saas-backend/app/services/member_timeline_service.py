import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Checkin, NPSResponse, RiskAlert, Task
from app.models.assessment import Assessment, MemberConstraints, MemberGoal, TrainingPlan
from app.models.body_composition import BodyCompositionEvaluation

logger = logging.getLogger(__name__)


def _scalars_all(db: Session, statement) -> list:
    try:
        result = db.scalars(statement)
    except StopIteration:
        return []
    if result is None:
        return []
    try:
        return list(result.all())
    except StopIteration:
        return []


def _scalar_or_none(db: Session, statement):
    try:
        return db.scalar(statement)
    except StopIteration:
        return None


def _body_composition_source_label(source: str | None) -> str:
    if source == "manual":
        return "Manual"
    if source == "ocr_receipt":
        return "OCR da foto"
    if source == "device_import":
        return "Importado"
    if source == "actuar_sync":
        return "Actuar / sincronizado"
    return "Tezewa (legado)"


def _body_composition_sync_label(sync_status: str | None) -> str:
    if sync_status == "synced":
        return "sync OK"
    if sync_status == "exported":
        return "sync exportado"
    if sync_status == "failed":
        return "sync falhou"
    if sync_status == "pending":
        return "sync pendente"
    if sync_status == "skipped":
        return "sync ignorado"
    return "sync desabilitado"


def get_member_timeline(db: Session, member_id: UUID, limit: int = 50) -> list[dict]:
    events: list[dict] = []

    assessments = _scalars_all(
        db,
        select(Assessment)
        .where(Assessment.member_id == member_id, Assessment.deleted_at.is_(None))
        .order_by(Assessment.assessment_date.desc())
        .limit(10)
    )
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

    constraints = _scalar_or_none(
        db,
        select(MemberConstraints)
        .where(MemberConstraints.member_id == member_id, MemberConstraints.deleted_at.is_(None))
        .order_by(MemberConstraints.updated_at.desc())
        .limit(1)
    )
    if constraints:
        parts = []
        medical_conditions = getattr(constraints, "medical_conditions", None)
        injuries = getattr(constraints, "injuries", None)
        contraindications = getattr(constraints, "contraindications", None)
        if medical_conditions:
            parts.append(f"Saude: {medical_conditions}")
        if injuries:
            parts.append(f"Lesoes: {injuries}")
        if contraindications:
            parts.append(f"Contraindicacoes: {contraindications}")
        events.append({
            "type": "constraints",
            "timestamp": constraints.updated_at.isoformat(),
            "title": "Restricoes atualizadas",
            "detail": " | ".join(parts) if parts else "Restricoes registradas",
            "icon": "shield-alert",
        })

    goals = _scalars_all(
        db,
        select(MemberGoal)
        .where(MemberGoal.member_id == member_id, MemberGoal.deleted_at.is_(None))
        .order_by(MemberGoal.updated_at.desc())
        .limit(10)
    )
    for goal in goals:
        events.append({
            "type": "goal",
            "timestamp": goal.updated_at.isoformat(),
            "title": f"Objetivo: {goal.title}",
            "detail": f"Status: {goal.status} | Progresso: {goal.progress_pct}%",
            "icon": "target",
        })

    training_plans = _scalars_all(
        db,
        select(TrainingPlan)
        .where(TrainingPlan.member_id == member_id, TrainingPlan.deleted_at.is_(None))
        .order_by(TrainingPlan.updated_at.desc())
        .limit(10)
    )
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

    checkins = _scalars_all(
        db,
        select(Checkin)
        .where(Checkin.member_id == member_id)
        .order_by(Checkin.checkin_at.desc())
        .limit(limit)
    )
    for checkin in checkins:
        source = getattr(checkin, "source", None)
        events.append({
            "type": "checkin",
            "timestamp": checkin.checkin_at.isoformat(),
            "title": "Check-in",
            "detail": f"Fonte: {source.value if hasattr(source, 'value') else source}",
            "icon": "activity",
        })

    risk_alerts = _scalars_all(
        db,
        select(RiskAlert)
        .where(RiskAlert.member_id == member_id)
        .order_by(RiskAlert.created_at.desc())
        .limit(20)
    )
    for alert in risk_alerts:
        level = getattr(alert, "level", None)
        level = level.value if hasattr(level, "value") else level
        level_label = str(level or "unknown")
        events.append({
            "type": "risk_alert",
            "timestamp": alert.created_at.isoformat(),
            "title": f"Alerta de risco - {level_label.upper()}",
            "detail": f"Score: {alert.score}. {'Resolvido' if alert.resolved else 'Ativo'}",
            "icon": "alert-triangle",
            "level": level,
        })

    nps_responses = _scalars_all(
        db,
        select(NPSResponse)
        .where(NPSResponse.member_id == member_id)
        .order_by(NPSResponse.created_at.desc())
        .limit(20)
    )
    for nps in nps_responses:
        sentiment = getattr(nps, "sentiment", None)
        sentiment = sentiment.value if hasattr(sentiment, "value") else sentiment
        events.append({
            "type": "nps",
            "timestamp": nps.created_at.isoformat(),
            "title": f"NPS: {nps.score}",
            "detail": f"Sentimento: {sentiment}",
            "icon": "star",
        })

    tasks = _scalars_all(
        db,
        select(Task)
        .where(Task.member_id == member_id, Task.deleted_at.is_(None))
        .order_by(Task.created_at.desc())
        .limit(20)
    )
    for task in tasks:
        raw_status = getattr(task, "status", None)
        raw_priority = getattr(task, "priority", None)
        status = raw_status.value if hasattr(raw_status, "value") else raw_status
        priority = raw_priority.value if hasattr(raw_priority, "value") else raw_priority
        source = ""
        plan_type = ""
        extra_data = getattr(task, "extra_data", None)
        if extra_data:
            raw_source = extra_data.get("source")
            raw_plan_type = extra_data.get("plan_type")
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

    audit_events = _scalars_all(
        db,
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
    )
    for event in audit_events:
        events.append({
            "type": "automation",
            "timestamp": event.created_at.isoformat(),
            "title": f"Automacao: {event.action}",
            "detail": str(event.details) if event.details else "",
            "icon": "zap",
        })

    try:
        body_composition_items = _scalars_all(
            db,
            select(BodyCompositionEvaluation)
            .where(BodyCompositionEvaluation.member_id == member_id)
            .order_by(BodyCompositionEvaluation.evaluation_date.desc())
            .limit(10)
        )
    except Exception:
        db.rollback()
        logger.warning("Nao foi possivel carregar eventos de bioimpedancia no timeline.")
        body_composition_items = []
    for body_item in body_composition_items:
        parts = []
        risk_flags = getattr(body_item, "ai_risk_flags_json", None) or []
        if isinstance(risk_flags, list):
            for flag in risk_flags[:2]:
                if flag:
                    parts.append(str(flag))
        health_score = getattr(body_item, "health_score", None)
        if health_score is not None:
            parts.append(f"health score {health_score}")
        parts.append(_body_composition_sync_label(getattr(body_item, "actuar_sync_status", None)))
        events.append({
            "type": "body_composition",
            "timestamp": body_item.evaluation_date.isoformat(),
            "title": "Bioimpedancia registrada",
            "subtitle": _body_composition_source_label(getattr(body_item, "source", None)),
            "detail": " | ".join(parts) if parts else "Avaliacao registrada",
            "icon": "scan-line",
        })

    events.sort(key=lambda event: event["timestamp"], reverse=True)
    return events[:limit]
