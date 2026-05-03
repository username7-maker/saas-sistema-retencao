from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models import Lead, LeadStage, Member, MemberStatus, RiskLevel


@dataclass
class AutopilotDecision:
    decision: str
    domain: str
    policy_key: str
    action_type: str
    template_key: str | None = None
    confidence: float = 0.0
    reason: str = ""
    next_timeout_hours: int = 48
    owner_role: str | None = None
    priority: str = "medium"
    metadata: dict = field(default_factory=dict)


def _days_without_checkin(member: Member) -> int | None:
    if not member.last_checkin_at:
        return None
    now = datetime.now(tz=timezone.utc)
    checkin_at = member.last_checkin_at
    if checkin_at.tzinfo is None:
        checkin_at = checkin_at.replace(tzinfo=timezone.utc)
    return max(0, (now - checkin_at).days)


def build_retention_policy(member: Member) -> AutopilotDecision:
    days = _days_without_checkin(member)
    if member.status != MemberStatus.ACTIVE:
        return AutopilotDecision("ignore", "retention", "retention_ineligible", "no_op", reason="Membro nao ativo")
    if days is None:
        return AutopilotDecision("ignore", "retention", "retention_no_checkin_history", "no_op", reason="Sem historico suficiente")
    if days >= 14 and member.risk_level == RiskLevel.RED:
        return AutopilotDecision(
            decision="create_human_task",
            domain="retention",
            policy_key="retention_inactive_d14_high_risk",
            action_type="create_human_task",
            confidence=0.9,
            reason=f"Aluno em alto risco ha {days} dias sem check-in",
            owner_role="reception",
            priority="high",
            metadata={"days_without_checkin": days},
        )
    if days >= 7:
        return AutopilotDecision(
            decision="auto_execute",
            domain="retention",
            policy_key="retention_inactive_d7",
            action_type="send_whatsapp",
            template_key="retention_d7",
            confidence=0.86,
            reason=f"Aluno ha {days} dias sem check-in, tentativa D7 segura se consentimento estiver OK",
            next_timeout_hours=48,
            metadata={"days_without_checkin": days},
        )
    if days >= 3:
        return AutopilotDecision(
            decision="auto_execute",
            domain="retention",
            policy_key="retention_inactive_d3",
            action_type="send_whatsapp",
            template_key="retention_d3",
            confidence=0.9,
            reason=f"Aluno ha {days} dias sem check-in, lembrete leve D3",
            next_timeout_hours=48,
            metadata={"days_without_checkin": days},
        )
    return AutopilotDecision("ignore", "retention", "retention_monitoring", "no_op", reason="Aluno ainda em monitoramento")


def build_finance_policy(*, days_overdue: int, disputed: bool = False) -> AutopilotDecision:
    if disputed:
        return AutopilotDecision(
            decision="create_human_task",
            domain="finance",
            policy_key="finance_payment_dispute_or_sensitive",
            action_type="create_human_task",
            confidence=0.99,
            reason="Contestacao financeira exige humano",
            owner_role="manager",
            priority="urgent",
        )
    if days_overdue >= 1:
        return AutopilotDecision(
            decision="auto_execute",
            domain="finance",
            policy_key="finance_payment_overdue_d1",
            action_type="send_whatsapp",
            template_key="finance_overdue_d1",
            confidence=0.82,
            reason=f"Recebivel vencido ha {days_overdue} dia(s)",
            next_timeout_hours=48,
            owner_role="reception",
            priority="high",
            metadata={"days_overdue": days_overdue},
        )
    return AutopilotDecision("ignore", "finance", "finance_not_overdue", "no_op", reason="Pagamento nao vencido")


def build_sales_policy(lead: Lead, *, event_type: str) -> AutopilotDecision:
    if event_type == "lead_created" and lead.stage == LeadStage.NEW:
        return AutopilotDecision(
            decision="assisted_human",
            domain="commercial",
            policy_key="sales_new_lead_d0",
            action_type="create_human_task",
            template_key="sales_new_lead_d0",
            confidence=0.72,
            reason="Lead novo entra em atendimento humano na V1 ate consentimento de lead estar formalizado",
            owner_role="salesperson",
            priority="high",
        )
    if event_type == "lead_replied":
        return AutopilotDecision(
            decision="create_human_task",
            domain="commercial",
            policy_key="sales_lead_replied",
            action_type="create_human_task",
            confidence=0.88,
            reason="Lead respondeu e deve receber acao comercial humana",
            owner_role="salesperson",
            priority="high",
        )
    if event_type in {"lead_won", "lead_lost"}:
        return AutopilotDecision(
            decision="auto_resolve",
            domain="commercial",
            policy_key=f"sales_{event_type}",
            action_type="close_existing_task",
            confidence=0.95,
            reason="Mudanca final de etapa permite fechar follow-ups comerciais redundantes",
        )
    return AutopilotDecision("ignore", "commercial", "sales_no_policy", "no_op", reason="Evento comercial sem policy V1")


def render_template(template_key: str, *, first_name: str) -> str:
    templates = {
        "retention_d3": "Oi, {first_name}! Sentimos sua falta por aqui. Consegue treinar hoje ou amanha?",
        "retention_d7": "Oi, {first_name}! Vi que voce ficou alguns dias sem treinar. Posso te ajudar a retomar sua rotina essa semana?",
        "finance_overdue_d1": "Oi, {first_name}! Passando para lembrar que existe uma pendencia no seu plano. Posso te enviar as opcoes para regularizar?",
        "sales_new_lead_d0": "Oi, {first_name}! Vi seu interesse na academia. Posso te ajudar a escolher o melhor plano?",
        "onboarding_d0": "Bem-vindo(a), {first_name}! Estamos felizes em ter voce com a gente. Qualquer duvida para comecar, e so responder por aqui.",
        "assessment_pending": "Oi, {first_name}! Sua avaliacao fisica esta pendente. Quer que eu te ajude a agendar um horario?",
    }
    template = templates.get(template_key, "{first_name}, podemos te ajudar?")
    return template.format(first_name=first_name.strip() or "tudo bem")

