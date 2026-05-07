from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from app.models import MemberStatus, RiskLevel
from app.services.retention_stage_service import (
    RETENTION_STAGE_ATTENTION,
    RETENTION_STAGE_COLD_BASE,
    RETENTION_STAGE_MANAGER_ESCALATION,
    RETENTION_STAGE_MONITORING,
    RETENTION_STAGE_REACTIVATION,
    RETENTION_STAGE_RECOVERY,
    calculate_member_retention_stage,
    normalize_retention_stage,
    retention_stage_meta,
)


LIFECYCLE_CANCELLED = "cancelled"
LIFECYCLE_PAUSED = "paused"
LIFECYCLE_ONBOARDING = "onboarding"
LIFECYCLE_ACTIVE = "active"
LIFECYCLE_ATTENTION = "attention"
LIFECYCLE_RECOVERY = "recovery"
LIFECYCLE_REACTIVATION = "reactivation"
LIFECYCLE_MANAGER_ESCALATION = "manager_escalation"
LIFECYCLE_COLD_BASE = "cold_base"


@dataclass(frozen=True)
class LifecycleMeta:
    stage: str
    label: str
    operational_lane: str
    priority: int
    recommended_owner_role: str
    recommended_queue: str
    next_focus: str


LIFECYCLE_META: dict[str, LifecycleMeta] = {
    LIFECYCLE_CANCELLED: LifecycleMeta(
        LIFECYCLE_CANCELLED,
        "Cancelado",
        "closed",
        0,
        "manager",
        "historico",
        "Manter historico e acionar winback apenas em campanha.",
    ),
    LIFECYCLE_PAUSED: LifecycleMeta(
        LIFECYCLE_PAUSED,
        "Pausado",
        "paused",
        30,
        "receptionist",
        "operacao",
        "Acompanhar retorno combinado ou revisar permanencia.",
    ),
    LIFECYCLE_ONBOARDING: LifecycleMeta(
        LIFECYCLE_ONBOARDING,
        "Onboarding D0-D30",
        "onboarding",
        75,
        "receptionist",
        "onboarding",
        "Garantir treino, primeira avaliacao, rotina e feedback inicial.",
    ),
    LIFECYCLE_ACTIVE: LifecycleMeta(
        LIFECYCLE_ACTIVE,
        "Ativo em rotina",
        "routine",
        20,
        "trainer",
        "professor",
        "Manter evolucao, treino atualizado e reavaliacao no prazo.",
    ),
    LIFECYCLE_ATTENTION: LifecycleMeta(
        LIFECYCLE_ATTENTION,
        "Atencao",
        "attention",
        80,
        "receptionist",
        "retencao",
        "Contato leve para evitar que vire recuperacao.",
    ),
    LIFECYCLE_RECOVERY: LifecycleMeta(
        LIFECYCLE_RECOVERY,
        "Recuperacao",
        "recovery",
        95,
        "receptionist",
        "retencao",
        "Contato ativo e tentativa de agendar retorno.",
    ),
    LIFECYCLE_REACTIVATION: LifecycleMeta(
        LIFECYCLE_REACTIVATION,
        "Reativacao 30+",
        "reactivation",
        70,
        "trainer",
        "retencao",
        "Oferecer retorno guiado com professor ou avaliacao.",
    ),
    LIFECYCLE_MANAGER_ESCALATION: LifecycleMeta(
        LIFECYCLE_MANAGER_ESCALATION,
        "Escalacao gerente",
        "manager_escalation",
        90,
        "manager",
        "gestao",
        "Gerente revisa permanencia, plano, trancamento ou cancelamento.",
    ),
    LIFECYCLE_COLD_BASE: LifecycleMeta(
        LIFECYCLE_COLD_BASE,
        "Base fria",
        "cold_base",
        5,
        "manager",
        "campanha",
        "Nao poluir fila diaria; trabalhar em campanha de winback.",
    ),
}


RETENTION_TO_LIFECYCLE = {
    RETENTION_STAGE_MONITORING: LIFECYCLE_ACTIVE,
    RETENTION_STAGE_ATTENTION: LIFECYCLE_ATTENTION,
    RETENTION_STAGE_RECOVERY: LIFECYCLE_RECOVERY,
    RETENTION_STAGE_REACTIVATION: LIFECYCLE_REACTIVATION,
    RETENTION_STAGE_MANAGER_ESCALATION: LIFECYCLE_MANAGER_ESCALATION,
    RETENTION_STAGE_COLD_BASE: LIFECYCLE_COLD_BASE,
}


def build_member_lifecycle_state(member: Any, *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(tz=timezone.utc)
    status = _enum_value(getattr(member, "status", None))
    join_days = _days_since_join(getattr(member, "join_date", None), current)
    retention_stage, days_without_checkin = _resolve_retention_stage(member, current)
    onboarding_status = str(getattr(member, "onboarding_status", "") or "").lower()
    risk_level = _enum_value(getattr(member, "risk_level", None))

    if status == MemberStatus.CANCELLED.value:
        stage = LIFECYCLE_CANCELLED
        reason = "Aluno cancelado; deve sair da fila diaria e ficar em historico/winback."
    elif status == MemberStatus.PAUSED.value:
        stage = LIFECYCLE_PAUSED
        reason = "Aluno pausado; acompanhamento deve respeitar combinacao de retorno."
    elif _is_onboarding_window(onboarding_status, join_days):
        stage = LIFECYCLE_ONBOARDING
        reason = f"Aluno em D{join_days or 0} de onboarding; foco e ativacao inicial."
    else:
        stage = RETENTION_TO_LIFECYCLE.get(retention_stage, LIFECYCLE_ACTIVE)
        if stage == LIFECYCLE_ACTIVE and risk_level == RiskLevel.YELLOW.value:
            stage = LIFECYCLE_ATTENTION
        if stage == LIFECYCLE_ACTIVE and risk_level == RiskLevel.RED.value:
            stage = LIFECYCLE_RECOVERY
        reason = _build_reason(stage, days_without_checkin, risk_level)

    meta = LIFECYCLE_META[stage]
    return {
        "lifecycle_stage": meta.stage,
        "lifecycle_label": meta.label,
        "operational_lane": meta.operational_lane,
        "lifecycle_priority": meta.priority,
        "recommended_owner_role": meta.recommended_owner_role,
        "recommended_queue": meta.recommended_queue,
        "next_focus": meta.next_focus,
        "reason": reason,
        "days_since_join": join_days,
        "days_without_checkin": days_without_checkin,
        "retention_stage": retention_stage,
        "retention_stage_label": retention_stage_meta(retention_stage).label,
        "is_daily_queue_default": stage not in {LIFECYCLE_CANCELLED, LIFECYCLE_COLD_BASE},
    }


def member_lifecycle_field(member: Any, key: str) -> Any:
    return build_member_lifecycle_state(member).get(key)


def _resolve_retention_stage(member: Any, now: datetime) -> tuple[str, int | None]:
    stored = normalize_retention_stage(getattr(member, "retention_stage", None))
    calculated, days = calculate_member_retention_stage(member, now=now)
    return stored or calculated, days


def _is_onboarding_window(onboarding_status: str, join_days: int | None) -> bool:
    if onboarding_status not in {"active", "at_risk"}:
        return False
    if join_days is None:
        return True
    return join_days <= 30


def _days_since_join(join_date: date | None, now: datetime) -> int | None:
    if not join_date:
        return None
    return max(0, (now.date() - join_date).days)


def _build_reason(stage: str, days_without_checkin: int | None, risk_level: str | None) -> str:
    if stage == LIFECYCLE_ACTIVE:
        return "Aluno ativo sem sinal operacional urgente."
    if days_without_checkin is None:
        return "Sem referencia confiavel de check-in; revisar dados antes de agir."
    if stage == LIFECYCLE_ATTENTION:
        return f"{days_without_checkin} dias sem check-in ou risco amarelo; agir antes de virar recuperacao."
    if stage == LIFECYCLE_RECOVERY:
        return f"{days_without_checkin} dias sem check-in ou risco vermelho; contato ativo necessario."
    if stage == LIFECYCLE_REACTIVATION:
        return f"{days_without_checkin} dias sem check-in; tratar como reativacao, nao lembrete simples."
    if stage == LIFECYCLE_MANAGER_ESCALATION:
        return f"{days_without_checkin} dias sem check-in; gerente deve revisar permanencia."
    if stage == LIFECYCLE_COLD_BASE:
        return f"{days_without_checkin} dias sem check-in; trabalhar em campanha, fora da fila diaria."
    if risk_level:
        return f"Estado definido por risco {risk_level}."
    return "Estado operacional calculado a partir dos sinais atuais."


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", value)
