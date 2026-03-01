import logging
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Member, MemberStatus, RiskLevel, Task, TaskPriority, TaskStatus
from app.models.automation_rule import AutomationAction, AutomationRule, AutomationTrigger
from app.models.enums import LeadStage
from app.models.lead import Lead
from app.models.message_log import MessageLog
from app.services.notification_service import create_notification
from app.services.whatsapp_service import render_template, send_whatsapp_sync
from app.utils.email import send_email


logger = logging.getLogger(__name__)


def list_automation_rules(
    db: Session,
    *,
    active_only: bool = False,
    trigger_type: str | None = None,
) -> list[AutomationRule]:
    stmt = select(AutomationRule)
    if active_only:
        stmt = stmt.where(AutomationRule.is_active.is_(True))
    if trigger_type:
        stmt = stmt.where(AutomationRule.trigger_type == trigger_type)
    return list(db.scalars(stmt.order_by(AutomationRule.created_at.asc())).all())


def get_automation_rule(db: Session, rule_id: UUID) -> AutomationRule | None:
    return db.get(AutomationRule, rule_id)


def create_automation_rule(db: Session, *, data: dict) -> AutomationRule:
    rule = AutomationRule(**data)
    db.add(rule)
    db.flush()
    return rule


def update_automation_rule(db: Session, rule_id: UUID, *, data: dict) -> AutomationRule | None:
    rule = db.get(AutomationRule, rule_id)
    if not rule:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(rule, key, value)
    db.add(rule)
    db.flush()
    return rule


def delete_automation_rule(db: Session, rule_id: UUID) -> bool:
    rule = db.get(AutomationRule, rule_id)
    if not rule:
        return False
    db.delete(rule)
    db.flush()
    return True


def execute_rule_for_member(
    db: Session,
    rule: AutomationRule,
    member: Member,
) -> dict:
    now = datetime.now(tz=timezone.utc)
    action_type = rule.action_type
    action_config = rule.action_config
    result = {"rule_id": str(rule.id), "member_id": str(member.id), "action": action_type, "status": "skipped"}

    template_vars = _build_template_vars(member)

    if action_type == AutomationAction.SEND_WHATSAPP:
        if not member.phone:
            result["status"] = "skipped"
            result["reason"] = "no_phone"
            return result
        template_name = action_config.get("template") or action_config.get("template_name") or "custom"
        extra_vars = action_config.get("extra_vars", {})
        if not isinstance(extra_vars, dict):
            extra_vars = {}
        # Backward compatibility for older rules saved with {"message": "..."}.
        if "mensagem" not in extra_vars and action_config.get("message"):
            extra_vars["mensagem"] = str(action_config.get("message"))
        message = render_template(template_name, {**template_vars, **extra_vars})
        log = send_whatsapp_sync(
            db,
            phone=member.phone,
            message=message,
            member_id=member.id,
            automation_rule_id=rule.id,
            template_name=template_name,
        )
        result["status"] = log.status
        result["message_log_id"] = str(log.id)

    elif action_type == AutomationAction.SEND_EMAIL:
        if not member.email:
            result["status"] = "skipped"
            result["reason"] = "no_email"
            return result
        subject = action_config.get("subject", "Mensagem da sua academia")
        body_template = action_config.get("body", "Ola {nome}, temos uma mensagem para voce.")
        body = _render(body_template, template_vars)
        sent = send_email(member.email, subject, body)
        result["status"] = "sent" if sent else "failed"
        _log_message(db, member.id, rule.id, "email", member.email, body, "sent" if sent else "failed")

    elif action_type == AutomationAction.CREATE_TASK:
        title_template = action_config.get("title", "Acao automatica para {nome}")
        title = _render(title_template, template_vars)
        description = action_config.get("description", "Tarefa criada por automacao.")
        priority_str = action_config.get("priority", "high")
        try:
            priority = TaskPriority(priority_str)
        except ValueError:
            priority = TaskPriority.HIGH

        existing = db.scalar(
            select(Task).where(
                Task.member_id == member.id,
                Task.title == title,
                Task.status.in_([TaskStatus.TODO, TaskStatus.DOING]),
                Task.deleted_at.is_(None),
            )
        )
        if existing:
            result["status"] = "skipped"
            result["reason"] = "task_already_exists"
            return result

        suggested_msg = action_config.get("suggested_message", "")
        if suggested_msg:
            suggested_msg = _render(suggested_msg, template_vars)

        task = Task(
            member_id=member.id,
            assigned_to_user_id=member.assigned_user_id,
            title=title,
            description=description,
            priority=priority,
            status=TaskStatus.TODO,
            kanban_column=TaskStatus.TODO.value,
            suggested_message=suggested_msg or None,
        )
        db.add(task)
        db.flush()
        result["status"] = "created"
        result["task_id"] = str(task.id)

    elif action_type == AutomationAction.NOTIFY:
        title = _render(action_config.get("title", "Alerta automatico"), template_vars)
        message = _render(action_config.get("message", "Acao necessaria para {nome}"), template_vars)
        notification = create_notification(
            db,
            member_id=member.id,
            user_id=member.assigned_user_id,
            title=title,
            message=message,
            category=action_config.get("category", "retention"),
        )
        result["status"] = "notified"
        result["notification_id"] = str(notification.id)

    rule.executions_count = (rule.executions_count or 0) + 1
    rule.last_executed_at = now
    db.add(rule)

    return result


def run_automation_rules(db: Session) -> list[dict]:
    rules = list_automation_rules(db, active_only=True)
    all_results: list[dict] = []

    for rule in rules:
        try:
            members = _find_matching_members(db, rule)
        except Exception:
            logger.exception("Erro ao avaliar gatilho da regra %s", rule.id)
            all_results.append(
                {
                    "rule_id": str(rule.id),
                    "member_id": None,
                    "status": "error",
                    "reason": "trigger_eval_failed",
                }
            )
            continue
        for member in members:
            try:
                result = execute_rule_for_member(db, rule, member)
                all_results.append(result)
            except Exception:
                logger.exception(
                    "Erro ao executar regra %s para membro %s", rule.id, member.id
                )
                all_results.append({
                    "rule_id": str(rule.id),
                    "member_id": str(member.id),
                    "status": "error",
                })

    db.commit()
    return all_results


def _find_matching_members(db: Session, rule: AutomationRule) -> list[Member]:
    trigger = rule.trigger_type
    config = rule.trigger_config
    now = datetime.now(tz=timezone.utc)

    base_stmt = select(Member).where(
        Member.deleted_at.is_(None),
        Member.status == MemberStatus.ACTIVE,
        Member.gym_id == rule.gym_id,
    )

    if trigger == AutomationTrigger.RISK_LEVEL_CHANGE:
        target_level = _coerce_risk_level(config.get("level"), default="red")
        return list(db.scalars(
            base_stmt.where(Member.risk_level == RiskLevel(target_level))
        ).all())

    if trigger == AutomationTrigger.INACTIVITY_DAYS:
        days = _coerce_int(config.get("days", config.get("threshold_days")), default=7, minimum=0)
        cutoff = now - timedelta(days=days)
        return list(db.scalars(
            base_stmt.where(
                (Member.last_checkin_at <= cutoff) | Member.last_checkin_at.is_(None)
            )
        ).all())

    if trigger == AutomationTrigger.NPS_SCORE:
        max_score = _coerce_int(config.get("max_score", config.get("threshold_value")), default=6, minimum=0)
        return list(db.scalars(
            base_stmt.where(Member.nps_last_score <= max_score)
        ).all())

    if trigger == AutomationTrigger.BIRTHDAY:
        today = now.date()
        # Match members whose extra_data["date_of_birth"] has the same month/day as today.
        # The value is expected in "YYYY-MM-DD" format stored in JSONB.
        members = list(db.scalars(base_stmt).all())
        result = []
        for m in members:
            dob_str = (m.extra_data or {}).get("date_of_birth")
            if not dob_str:
                continue
            try:
                from datetime import date as dt_date
                dob = dt_date.fromisoformat(str(dob_str))
                if dob.month == today.month and dob.day == today.day:
                    result.append(m)
            except (ValueError, TypeError):
                continue
        return result

    if trigger == AutomationTrigger.LEAD_STALE:
        stale_days = _coerce_int(config.get("stale_days", config.get("threshold_days")), default=7, minimum=1)
        cutoff = now - timedelta(days=stale_days)
        terminal_stages = [LeadStage.WON, LeadStage.LOST]
        stale_leads = list(db.scalars(
            select(Lead).where(
                Lead.gym_id == rule.gym_id,
                Lead.deleted_at.is_(None),
                Lead.stage.not_in(terminal_stages),
                Lead.updated_at <= cutoff,
            )
        ).all())
        # For LEAD_STALE, the action is applied to the assigned member of the lead if available,
        # otherwise we return an empty list (task/notification not tied to a specific member).
        # We build synthetic Member-like objects from lead owners' assigned members.
        # For simplicity: find members who own these stale leads (by lead.owner_id → user → members).
        # To avoid complexity, return active members whose leads are stale (match by gym only).
        # We return an empty list for member-based actions since leads aren't members.
        # Instead, we store the lead reference in extra_data for the task engine.
        # Returning [] is safe — the caller will not execute actions for 0 members.
        # Future: implement a lead-scoped action runner.
        _ = stale_leads  # consumed above for future use
        return []

    if trigger == AutomationTrigger.CHECKIN_STREAK:
        streak_days = _coerce_int(config.get("streak_days", config.get("threshold_days")), default=7, minimum=1)
        # Find members who have checked in on at least streak_days distinct days
        # within the last streak_days days.
        from app.models.checkin import Checkin
        from sqlalchemy import distinct, cast
        from sqlalchemy.dialects.postgresql import DATE as PG_DATE
        cutoff = now - timedelta(days=streak_days)
        subq = (
            select(Checkin.member_id, func.count(distinct(cast(Checkin.checkin_at, PG_DATE))).label("days_count"))
            .where(Checkin.checkin_at >= cutoff)
            .group_by(Checkin.member_id)
            .having(func.count(distinct(cast(Checkin.checkin_at, PG_DATE))) >= streak_days)
            .subquery()
        )
        return list(db.scalars(
            base_stmt.join(subq, Member.id == subq.c.member_id)
        ).all())

    return []


def _coerce_int(value: object, *, default: int, minimum: int | None = None) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None and parsed < minimum:
        return minimum
    return parsed


def _coerce_risk_level(value: object, *, default: str = "red") -> str:
    raw = str(value or default).strip().lower()
    allowed = {level.value for level in RiskLevel}
    if raw in allowed:
        return raw
    logger.warning("Nivel de risco invalido na automacao: %s. Usando default=%s", raw, default)
    return default


def _render(template: str, vars: dict) -> str:
    """Safe template renderer: replaces {key} with vars[key], leaves unknown keys untouched."""

    def replace(match: re.Match) -> str:
        key = match.group(1)
        return str(vars.get(key, match.group(0)))

    return re.sub(r"\{(\w+)\}", replace, template)


def _build_template_vars(member: Member) -> dict:
    now = datetime.now(tz=timezone.utc)
    days_inactive = 0
    if member.last_checkin_at:
        ref = member.last_checkin_at
        if ref.tzinfo is None:
            from datetime import timezone as tz
            ref = ref.replace(tzinfo=tz.utc)
        days_inactive = max(0, (now - ref).days)

    return {
        "nome": member.full_name,
        "plano": member.plan_name,
        "dias": str(days_inactive),
        "score": str(member.risk_score),
        "nps": str(member.nps_last_score),
        "email": member.email or "",
        "telefone": member.phone or "",
        "mensagem": "",
    }


def _log_message(
    db: Session,
    member_id: UUID | None,
    rule_id: UUID | None,
    channel: str,
    recipient: str,
    content: str,
    status: str,
) -> MessageLog:
    log = MessageLog(
        member_id=member_id,
        automation_rule_id=rule_id,
        channel=channel,
        recipient=recipient,
        content=content,
        status=status,
    )
    db.add(log)
    db.flush()
    return log


def seed_default_rules(db: Session, gym_id: UUID) -> list[AutomationRule]:
    existing = db.scalar(
        select(func.count()).select_from(AutomationRule).where(AutomationRule.gym_id == gym_id)
    )
    if existing and existing > 0:
        return []

    defaults = [
        {
            "name": "Risco Vermelho → WhatsApp",
            "description": "Envia mensagem WhatsApp quando aluno entra em risco vermelho",
            "trigger_type": AutomationTrigger.RISK_LEVEL_CHANGE,
            "trigger_config": {"level": "red"},
            "action_type": AutomationAction.SEND_WHATSAPP,
            "action_config": {"template": "risk_red"},
        },
        {
            "name": "Risco Amarelo → Tarefa de Ligacao",
            "description": "Cria tarefa para recepcionista ligar quando aluno entra em risco amarelo",
            "trigger_type": AutomationTrigger.RISK_LEVEL_CHANGE,
            "trigger_config": {"level": "yellow"},
            "action_type": AutomationAction.CREATE_TASK,
            "action_config": {
                "title": "Ligar para {nome} - Risco Amarelo",
                "description": "Aluno em risco amarelo. Score: {score}. Entrar em contato.",
                "priority": "high",
                "suggested_message": "Ola {nome}, tudo bem? Notamos sua ausencia e gostavamos de saber como podemos te ajudar.",
            },
        },
        {
            "name": "7 dias inativo → WhatsApp",
            "description": "Envia WhatsApp apos 7 dias sem check-in",
            "trigger_type": AutomationTrigger.INACTIVITY_DAYS,
            "trigger_config": {"days": 7},
            "action_type": AutomationAction.SEND_WHATSAPP,
            "action_config": {"template": "reengagement_7d"},
        },
        {
            "name": "NPS baixo → Tarefa Follow-up",
            "description": "Cria tarefa de follow-up quando NPS < 7",
            "trigger_type": AutomationTrigger.NPS_SCORE,
            "trigger_config": {"max_score": 6},
            "action_type": AutomationAction.CREATE_TASK,
            "action_config": {
                "title": "Follow-up NPS baixo - {nome}",
                "description": "Aluno com NPS {nps}. Agendar conversa para entender insatisfacao.",
                "priority": "high",
            },
        },
        {
            "name": "3 dias inativo → Notificacao",
            "description": "Notifica equipe apos 3 dias sem check-in",
            "trigger_type": AutomationTrigger.INACTIVITY_DAYS,
            "trigger_config": {"days": 3},
            "action_type": AutomationAction.NOTIFY,
            "action_config": {
                "title": "Aluno inativo: {nome}",
                "message": "{nome} esta sem treinar ha {dias} dias. Score de risco: {score}.",
                "category": "retention",
            },
        },
    ]

    rules = []
    for data in defaults:
        rule = AutomationRule(**{**data, "gym_id": gym_id})
        db.add(rule)
        rules.append(rule)

    db.flush()
    return rules
