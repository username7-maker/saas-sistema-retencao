from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AutopilotAction, GymAutopilotSettings, Lead, LeadStage, Member, MemberConsentRecord, MemberStatus, MessageLog, Task
from app.services.autopilot_settings_service import get_or_create_autopilot_settings

SENSITIVE_TERMS = {
    "cancelar",
    "cancelamento",
    "reclamacao",
    "reclamação",
    "processo",
    "advogado",
    "chargeback",
    "ja paguei",
    "já paguei",
    "cobranca indevida",
    "cobrança indevida",
    "nao autorizo",
    "não autorizo",
    "parar",
    "sair",
    "remover",
    "falar com gerente",
    "humano",
    "lesao",
    "lesão",
    "dor forte",
    "emergencia",
    "emergência",
    "assedio",
    "assédio",
    "agressao",
    "agressão",
}


@dataclass
class SafetyResult:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    scheduled_for: datetime | None = None
    settings: GymAutopilotSettings | None = None


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def contains_sensitive_text(text: str | None) -> bool:
    normalized = (text or "").strip().lower()
    return any(term in normalized for term in SENSITIVE_TERMS)


def _member_has_whatsapp_consent(db: Session, *, gym_id: UUID, member_id: UUID) -> bool:
    record = db.scalar(
        select(MemberConsentRecord)
        .where(
            MemberConsentRecord.gym_id == gym_id,
            MemberConsentRecord.member_id == member_id,
            MemberConsentRecord.consent_type.in_(["whatsapp_consent", "communication", "marketing"]),
        )
        .order_by(MemberConsentRecord.created_at.desc())
        .limit(1)
    )
    if record is None:
        return False
    if record.status != "accepted":
        return False
    if record.expires_at and record.expires_at < _now():
        return False
    return True


def _within_business_hours(settings: GymAutopilotSettings, now: datetime) -> bool:
    start_hour, start_minute = (int(part) for part in settings.business_hours_start.split(":"))
    end_hour, end_minute = (int(part) for part in settings.business_hours_end.split(":"))
    start = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    end = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    return start <= now <= end


def _next_business_time(settings: GymAutopilotSettings, now: datetime) -> datetime:
    start_hour, start_minute = (int(part) for part in settings.business_hours_start.split(":"))
    candidate = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    if now >= candidate:
        candidate = candidate + timedelta(days=1)
    return candidate


def _recent_auto_messages_count(db: Session, *, gym_id: UUID, member_id: UUID | None, lead_id: UUID | None, window: timedelta) -> int:
    filters = [
        MessageLog.gym_id == gym_id,
        MessageLog.channel.in_(["whatsapp", "kommo"]),
        MessageLog.direction == "outbound",
        MessageLog.created_at >= _now() - window,
        MessageLog.status.in_(["pending", "sent", "delivered", "read"]),
    ]
    if member_id:
        filters.append(MessageLog.member_id == member_id)
    elif lead_id:
        filters.append(MessageLog.lead_id == lead_id)
    else:
        return 0
    return int(db.scalar(select(func.count()).select_from(MessageLog).where(*filters)) or 0)


def _recent_human_task_activity(db: Session, *, gym_id: UUID, member_id: UUID | None, lead_id: UUID | None, cooldown_hours: int) -> bool:
    filters = [
        Task.gym_id == gym_id,
        Task.deleted_at.is_(None),
        Task.updated_at >= _now() - timedelta(hours=cooldown_hours),
        Task.extra_data["source"].astext != "autopilot",
    ]
    if member_id:
        filters.append(Task.member_id == member_id)
    elif lead_id:
        filters.append(Task.lead_id == lead_id)
    else:
        return False
    return bool(db.scalar(select(func.count()).select_from(Task).where(*filters)) or 0)


def _pending_duplicate_action(db: Session, *, gym_id: UUID, policy_key: str, member_id: UUID | None, lead_id: UUID | None) -> bool:
    filters = [
        AutopilotAction.gym_id == gym_id,
        AutopilotAction.policy_key == policy_key,
        AutopilotAction.status.in_(["planned", "scheduled", "executing", "sent", "awaiting_outcome"]),
    ]
    if member_id:
        filters.append(AutopilotAction.member_id == member_id)
    elif lead_id:
        filters.append(AutopilotAction.lead_id == lead_id)
    else:
        return False
    return bool(db.scalar(select(func.count()).select_from(AutopilotAction).where(*filters)) or 0)


def check_autopilot_safety(
    db: Session,
    *,
    gym_id: UUID,
    domain: str,
    policy_key: str,
    action_type: str,
    member: Member | None = None,
    lead: Lead | None = None,
    message_text: str | None = None,
    require_auto_send: bool = False,
    ignore_recent_human_activity: bool = False,
) -> SafetyResult:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    reasons: list[str] = []
    now = _now()
    member_id = member.id if member else None
    lead_id = lead.id if lead else None

    if not settings.autopilot_enabled:
        reasons.append("autopilot_disabled")
    domain_enabled = {
        "retention": settings.retention_enabled,
        "finance": settings.finance_enabled,
        "sales": settings.sales_enabled,
        "commercial": settings.sales_enabled,
        "onboarding": settings.onboarding_enabled,
        "assessment": settings.assessment_enabled,
        "nps": settings.nps_enabled,
        "support": settings.nps_enabled,
    }.get(domain, True)
    if not domain_enabled:
        reasons.append(f"{domain}_disabled")
    if require_auto_send and not settings.autopilot_auto_send_enabled:
        reasons.append("auto_send_disabled")
    if action_type == "close_existing_task" and not settings.autopilot_auto_close_enabled:
        reasons.append("auto_close_disabled")
    if message_text and contains_sensitive_text(message_text):
        reasons.append("sensitive_text")
    if member and member.status == MemberStatus.CANCELLED:
        reasons.append("member_cancelled")
    if lead and lead.stage in {LeadStage.WON, LeadStage.LOST}:
        reasons.append("lead_closed")
    if require_auto_send and member and not _member_has_whatsapp_consent(db, gym_id=gym_id, member_id=member.id):
        reasons.append("missing_member_whatsapp_consent")
    if require_auto_send and lead:
        reasons.append("lead_consent_not_supported_v1")
    if require_auto_send and not _within_business_hours(settings, now):
        return SafetyResult(False, [*reasons, "outside_business_hours"], scheduled_for=_next_business_time(settings, now), settings=settings)
    if require_auto_send:
        weekly_limit = settings.max_auto_messages_per_member_per_week if member else settings.max_auto_messages_per_lead_per_week
        if _recent_auto_messages_count(db, gym_id=gym_id, member_id=member_id, lead_id=lead_id, window=timedelta(days=7)) >= weekly_limit:
            reasons.append("weekly_message_limit")
    if _pending_duplicate_action(db, gym_id=gym_id, policy_key=policy_key, member_id=member_id, lead_id=lead_id):
        reasons.append("duplicate_pending_action")
    if not ignore_recent_human_activity and _recent_human_task_activity(
        db,
        gym_id=gym_id,
        member_id=member_id,
        lead_id=lead_id,
        cooldown_hours=settings.human_recent_activity_cooldown_hours,
    ):
        reasons.append("recent_human_activity")

    return SafetyResult(allowed=not reasons, reasons=reasons, settings=settings)
