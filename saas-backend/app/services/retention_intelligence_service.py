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
from app.services.retention_stage_service import (
    RETENTION_STAGE_ATTENTION,
    RETENTION_STAGE_COLD_BASE,
    RETENTION_STAGE_MANAGER_ESCALATION,
    RETENTION_STAGE_REACTIVATION,
    RETENTION_STAGE_RECOVERY,
    calculate_member_retention_stage,
    retention_stage_meta,
)
from app.services.task_event_service import record_task_event

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


def build_retention_playbook(
    db: Session,
    member: Member,
    churn_type: str,
    *,
    retention_stage: str | None = None,
    days_without_checkin: int | None = None,
) -> list[dict]:
    """Gera playbook de acoes baseado no tipo de churn."""
    stage = retention_stage or getattr(member, "retention_stage", None)
    if stage:
        stage_playbooks = {
            RETENTION_STAGE_ATTENTION: [
                {
                    "action": "whatsapp",
                    "priority": "medium",
                    "title": "Contato leve - aluno ausente 7+ dias",
                    "message": "Ola {nome}, sentimos sua falta no treino. Esta tudo certo para voltar essa semana?",
                    "due_days": 0,
                    "owner": "reception",
                }
            ],
            RETENTION_STAGE_RECOVERY: [
                {
                    "action": "whatsapp",
                    "priority": "high",
                    "title": "Recuperar rotina de treino",
                    "message": "Ola {nome}, ja faz alguns dias que voce nao treina. Quer que a gente ajuste seu horario ou marque uma conversa rapida para retomar?",
                    "due_days": 0,
                    "owner": "reception",
                },
                {
                    "action": "task",
                    "priority": "medium",
                    "title": "Professor revisar barreira de retorno",
                    "message": "Verificar se o aluno precisa de ajuste de treino, horario ou meta para voltar com seguranca.",
                    "due_days": 1,
                    "owner": "coach",
                },
            ],
            RETENTION_STAGE_REACTIVATION: [
                {
                    "action": "whatsapp",
                    "priority": "high",
                    "title": "Agendar retorno guiado com professor",
                    "message": "Ola {nome}, queremos te ajudar a voltar sem recomecar sozinho. Podemos agendar um retorno guiado com professor esta semana?",
                    "due_days": 0,
                    "owner": "coach",
                }
            ],
            RETENTION_STAGE_MANAGER_ESCALATION: [
                {
                    "action": "call",
                    "priority": "urgent",
                    "title": "Escalar reativacao para gerente",
                    "message": "Aluno com inatividade longa. Gerente deve revisar plano, motivo real, inadimplencia, trancamento ou risco de cancelamento.",
                    "due_days": 0,
                    "owner": "manager",
                }
            ],
            RETENTION_STAGE_COLD_BASE: [
                {
                    "action": "campaign",
                    "priority": "low",
                    "title": "Mover para campanha de winback",
                    "message": "Aluno em base fria. Nao acionar na fila diaria; incluir em campanha periodica de reativacao.",
                    "due_days": 30,
                    "owner": "manager",
                }
            ],
        }
        if stage in stage_playbooks:
            return stage_playbooks[stage]

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
    retention_stage = getattr(member, "retention_stage", None)
    stage_meta = retention_stage_meta(retention_stage)

    priority_map = {
        "urgent": TaskPriority.URGENT,
        "high": TaskPriority.HIGH,
        "medium": TaskPriority.MEDIUM,
        "low": TaskPriority.LOW,
    }

    existing_retention_task = db.scalar(
        select(Task)
        .where(
            Task.member_id == member.id,
            Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
            Task.deleted_at.is_(None),
            Task.extra_data["source"].astext == "retention_intelligence",
        )
        .order_by(Task.created_at.desc())
        .limit(1)
    )

    for step in playbook:
        title = step["title"]

        if step["action"] in ("call", "task", "whatsapp"):
            task_payload = {
                "title": title,
                "description": step["message"].replace("{nome}", member.full_name),
                "priority": priority_map.get(step["priority"], TaskPriority.MEDIUM),
                "due_date": now + timedelta(days=step.get("due_days", 1)),
                "suggested_message": step["message"].replace("{nome}", member.full_name),
                "extra_data": {
                    "source": "retention_intelligence",
                    "domain": "retention",
                    "churn_type": member.churn_type,
                    "owner_role": step["owner"],
                    "retention_stage": retention_stage,
                    "retention_stage_label": stage_meta.label,
                    "retention_stage_priority": stage_meta.priority,
                },
            }

            if existing_retention_task:
                extra = dict(existing_retention_task.extra_data or {})
                previous_stage = extra.get("retention_stage")
                cooldown_until = extra.get("retention_cooldown_until")
                if isinstance(cooldown_until, str):
                    try:
                        parsed_cooldown = datetime.fromisoformat(cooldown_until.replace("Z", "+00:00"))
                    except ValueError:
                        parsed_cooldown = None
                    if parsed_cooldown and parsed_cooldown > now and previous_stage == retention_stage:
                        results.append({"title": title, "status": "skipped", "reason": "cooldown_active"})
                        break

                existing_retention_task.title = task_payload["title"]
                existing_retention_task.description = task_payload["description"]
                existing_retention_task.priority = task_payload["priority"]
                existing_retention_task.due_date = task_payload["due_date"]
                existing_retention_task.suggested_message = task_payload["suggested_message"]
                existing_retention_task.extra_data = {**extra, **task_payload["extra_data"]}
                db.add(existing_retention_task)
                if previous_stage != retention_stage:
                    record_task_event(
                        db,
                        task=existing_retention_task,
                        current_user=None,
                        event_type="status_changed",
                        outcome="retention_stage_changed",
                        note=f"Retencao mudou de {previous_stage or 'sem estagio'} para {retention_stage}.",
                        metadata_json={"previous_stage": previous_stage, "retention_stage": retention_stage},
                        flush=False,
                    )
                results.append({"title": title, "status": "updated", "type": "task"})
                break

            task = Task(
                gym_id=member.gym_id,
                member_id=member.id,
                assigned_to_user_id=member.assigned_user_id,
                title=task_payload["title"],
                description=task_payload["description"],
                priority=task_payload["priority"],
                status=TaskStatus.TODO,
                kanban_column="todo",
                due_date=task_payload["due_date"],
                suggested_message=task_payload["suggested_message"],
                extra_data=task_payload["extra_data"],
            )
            db.add(task)
            results.append({"title": title, "status": "created", "type": "task"})
            existing_retention_task = task
            break

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
        elif step["action"] == "campaign":
            results.append({"title": title, "status": "skipped", "reason": "cold_base_campaign"})

    return results


def run_daily_retention_intelligence(db: Session) -> dict:
    """Job diario que classifica churn e materializa playbooks para membros em risco."""
    members_at_risk = list(db.scalars(
        select(Member).where(
            Member.deleted_at.is_(None),
            Member.status == MemberStatus.ACTIVE,
            Member.risk_level.in_([RiskLevel.YELLOW, RiskLevel.RED]),
        )
    ).all())

    classified = 0
    playbooks_created = 0
    stages_updated = 0

    for member in members_at_risk:
        try:
            retention_stage, days_without_checkin = calculate_member_retention_stage(member)
            if member.retention_stage != retention_stage:
                member.retention_stage = retention_stage
                stages_updated += 1

            churn_type = classify_churn_type(db, member)
            member.churn_type = churn_type

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

            playbook = build_retention_playbook(
                db,
                member,
                churn_type,
                retention_stage=retention_stage,
                days_without_checkin=days_without_checkin,
            )
            results = materialize_playbook(db, member, playbook)
            db.add(member)
            classified += 1
            playbooks_created += sum(1 for r in results if r["status"] == "created")
        except Exception:
            logger.exception("Falha ao processar retention intelligence para membro %s", member.id)

    db.commit()
    return {"members_classified": classified, "stages_updated": stages_updated, "playbooks_materialized": playbooks_created}
