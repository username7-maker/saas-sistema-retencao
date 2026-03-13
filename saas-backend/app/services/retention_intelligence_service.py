from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Checkin,
    Member,
    MemberStatus,
    NPSResponse,
    RiskLevel,
    Task,
    TaskPriority,
    TaskStatus,
)
from app.models.enums import ChurnType
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)


def classify_churn_type(db: Session, member: Member) -> str:
    """Classifica o tipo provavel de churn de um membro em risco."""
    now = datetime.now(tz=timezone.utc)
    join_days = (now.date() - member.join_date).days

    # Early dropout: menos de 30 dias
    if join_days <= 30 and member.risk_score >= 40:
        return ChurnType.EARLY_DROPOUT.value

    # NPS baixo = insatisfacao
    if member.nps_last_score <= 5:
        return ChurnType.VOLUNTARY_DISSATISFACTION.value

    # Checar sazonalidade: comparar com o mesmo periodo do ano anterior via check-ins
    seasonal = _detect_seasonal_pattern(db, member.id, now)
    if seasonal:
        return ChurnType.INVOLUNTARY_SEASONAL.value

    # Sem check-in por muitos dias + NPS neutro = inatividade gradual
    if member.risk_score >= 60 and member.nps_last_score >= 6:
        return ChurnType.INVOLUNTARY_INACTIVITY.value

    return ChurnType.UNKNOWN.value


def _detect_seasonal_pattern(db: Session, member_id: UUID, now: datetime) -> bool:
    """Verifica se o membro teve o mesmo padrao de queda no ano anterior."""
    last_year_start = now - timedelta(days=395)
    last_year_end = now - timedelta(days=335)
    last_year_checkins = db.scalar(
        select(func.count(Checkin.id)).where(
            Checkin.member_id == member_id,
            Checkin.checkin_at >= last_year_start,
            Checkin.checkin_at <= last_year_end,
        )
    ) or 0
    return last_year_checkins <= 2


def build_retention_playbook(db: Session, member: Member, churn_type: str) -> list[dict]:
    """Gera playbook de acoes baseado no tipo de churn."""
    playbooks = {
        ChurnType.EARLY_DROPOUT.value: [
            {
                "action": "call",
                "priority": "urgent",
                "title": "Ligacao urgente - aluno novo sumindo",
                "message": "Ola {nome}, notamos que voce ainda esta no inicio da sua jornada. Podemos agendar um horario para ajustar seu treino?",
                "due_days": 0,
                "owner": "reception",
            },
            {
                "action": "task",
                "priority": "high",
                "title": "Revisar experiencia de onboarding",
                "message": "Verificar se o aluno fez avaliacao, recebeu treino e foi acompanhado nos primeiros dias.",
                "due_days": 1,
                "owner": "manager",
            },
        ],
        ChurnType.VOLUNTARY_DISSATISFACTION.value: [
            {
                "action": "call",
                "priority": "urgent",
                "title": "Ligacao de recuperacao - NPS baixo",
                "message": "Ola {nome}, sua opiniao e muito importante. Quero entender o que podemos melhorar na sua experiencia.",
                "due_days": 0,
                "owner": "manager",
            },
            {
                "action": "notify",
                "priority": "high",
                "title": "Aluno insatisfeito em risco",
                "message": "NPS baixo detectado. Priorizar atendimento personalizado.",
                "due_days": 0,
                "owner": "manager",
            },
            {
                "action": "task",
                "priority": "high",
                "title": "Oferecer beneficio de retencao",
                "message": "Avaliar oferta de upgrade, aula experimental ou cortesia para reverter insatisfacao.",
                "due_days": 2,
                "owner": "manager",
            },
        ],
        ChurnType.INVOLUNTARY_INACTIVITY.value: [
            {
                "action": "whatsapp",
                "priority": "high",
                "title": "Mensagem de reengajamento",
                "message": "Ola {nome}, sentimos sua falta! Que tal retomar os treinos esta semana? Estamos aqui para te ajudar.",
                "due_days": 0,
                "owner": "reception",
            },
            {
                "action": "task",
                "priority": "medium",
                "title": "Agendar revisao de treino",
                "message": "Oferecer revisao de treino gratuita como incentivo para retorno.",
                "due_days": 3,
                "owner": "coach",
            },
        ],
        ChurnType.INVOLUNTARY_SEASONAL.value: [
            {
                "action": "whatsapp",
                "priority": "medium",
                "title": "Mensagem sazonal",
                "message": "Ola {nome}, sabemos que esta epoca pode ser corrida. Seu treino te espera quando voce estiver pronto!",
                "due_days": 0,
                "owner": "reception",
            },
            {
                "action": "task",
                "priority": "low",
                "title": "Monitorar retorno sazonal",
                "message": "Aluno com padrao sazonal. Acompanhar se retorna nas proximas 4 semanas.",
                "due_days": 7,
                "owner": "reception",
            },
        ],
    }
    return playbooks.get(churn_type, playbooks[ChurnType.INVOLUNTARY_INACTIVITY.value])


def materialize_playbook(db: Session, member: Member, playbook: list[dict]) -> list[dict]:
    """Transforma playbook em tasks/notificacoes reais no sistema."""
    now = datetime.now(tz=timezone.utc)
    results = []

    priority_map = {
        "urgent": TaskPriority.URGENT,
        "high": TaskPriority.HIGH,
        "medium": TaskPriority.MEDIUM,
        "low": TaskPriority.LOW,
    }

    for step in playbook:
        title = step["title"]
        # Deduplicacao: verificar se task com mesmo titulo ja existe para este membro
        existing = db.scalar(
            select(Task).where(
                Task.member_id == member.id,
                Task.title == title,
                Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
                Task.deleted_at.is_(None),
            )
        )
        if existing:
            results.append({"title": title, "status": "skipped", "reason": "already_exists"})
            continue

        if step["action"] in ("call", "task", "whatsapp"):
            task = Task(
                gym_id=member.gym_id,
                member_id=member.id,
                assigned_to_user_id=member.assigned_user_id,
                title=title,
                description=step["message"].replace("{nome}", member.full_name),
                priority=priority_map.get(step["priority"], TaskPriority.MEDIUM),
                status=TaskStatus.TODO,
                kanban_column="todo",
                due_date=now + timedelta(days=step.get("due_days", 1)),
                suggested_message=step["message"].replace("{nome}", member.full_name),
                extra_data={
                    "source": "retention_intelligence",
                    "churn_type": member.churn_type,
                    "owner_role": step["owner"],
                },
            )
            db.add(task)
            results.append({"title": title, "status": "created", "type": "task"})

        elif step["action"] == "notify":
            create_notification(
                db,
                member_id=member.id,
                user_id=member.assigned_user_id,
                title=title,
                message=step["message"].replace("{nome}", member.full_name),
                category="retention",
            )
            results.append({"title": title, "status": "created", "type": "notification"})

    return results


def run_daily_retention_intelligence(db: Session) -> dict:
    """Job diario que classifica churn e materializa playbooks para membros em risco."""
    members_at_risk = list(db.scalars(
        select(Member).where(
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.risk_level.in_([RiskLevel.YELLOW, RiskLevel.RED]),
            Member.retention_stage.not_in(["intervening", "recovering"]),
        )
    ).all())

    classified = 0
    playbooks_created = 0

    for member in members_at_risk:
        try:
            churn_type = classify_churn_type(db, member)
            member.churn_type = churn_type
            member.retention_stage = "intervening"

            # VIP tem tratamento especial: sempre urgente para manager
            if member.is_vip and member.risk_level == RiskLevel.RED:
                create_notification(
                    db,
                    member_id=member.id,
                    user_id=member.assigned_user_id,
                    title=f"ALERTA VIP: {member.full_name} em risco critico",
                    message=f"Membro VIP com risco {member.risk_score}. Acionar retencao imediata.",
                    category="retention_vip",
                )

            playbook = build_retention_playbook(db, member, churn_type)
            results = materialize_playbook(db, member, playbook)
            db.add(member)
            classified += 1
            playbooks_created += sum(1 for r in results if r["status"] == "created")
        except Exception:
            logger.exception("Falha ao processar retention intelligence para membro %s", member.id)

    db.commit()
    return {"members_classified": classified, "playbooks_materialized": playbooks_created}
