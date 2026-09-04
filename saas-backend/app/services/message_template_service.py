from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from string import Formatter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GymMessageTemplateOverride, RoleEnum, User


@dataclass(frozen=True)
class MessageTemplateDefinition:
    key: str
    domain: str
    channel: str
    objective: str
    content: str
    allowed_variables: tuple[str, ...]
    required_variables: tuple[str, ...] = ("first_name",)
    version: str = "1.0.0"
    active: bool = True


def _template(
    key: str, domain: str, objective: str, content: str, *, channel: str = "whatsapp"
) -> MessageTemplateDefinition:
    allowed = ("first_name", "plan", "days_inactive", "next_step", "responsible", "risk", "nps", "date", "gym_name")
    return MessageTemplateDefinition(key, domain, channel, objective, content, allowed)


TEMPLATES: dict[str, MessageTemplateDefinition] = {
    item.key: item
    for item in (
        _template(
            "retention.reengagement",
            "retention",
            "Retomar a rotina",
            "Oi, {first_name}! Sentimos sua falta por aqui. Podemos ajudar você a retomar sua rotina esta semana?",
        ),
        _template(
            "retention.risk",
            "retention",
            "Acolher aluno em risco",
            "Oi, {first_name}! Queremos entender como está sua experiência e ajudar no próximo passo. Podemos conversar?",
        ),
        _template(
            "retention.nps_low",
            "retention",
            "Acolher avaliação baixa",
            "Oi, {first_name}. Obrigado pelo seu feedback. Queremos ouvir você e entender como podemos melhorar sua experiência.",
        ),
        _template(
            "onboarding.welcome",
            "onboarding",
            "Dar boas-vindas",
            "Oi, {first_name}! Seja bem-vindo(a). Conte com a nossa equipe para começar sua rotina com segurança e clareza.",
        ),
        _template(
            "onboarding.checkin",
            "onboarding",
            "Acompanhar início",
            "Oi, {first_name}! Como foi seu início por aqui? Se precisar de ajuda com sua rotina, estamos à disposição.",
        ),
        _template(
            "commercial.new_lead",
            "commercial",
            "Iniciar atendimento comercial",
            "Oi, {first_name}! Recebemos seu interesse. Posso entender seu objetivo e explicar as opções que combinam com sua rotina?",
        ),
        _template(
            "commercial.followup",
            "commercial",
            "Retomar conversa comercial",
            "Oi, {first_name}! Passando para saber se ficou alguma dúvida e ajudar você no próximo passo, sem compromisso.",
        ),
        _template(
            "commercial.objection",
            "commercial",
            "Responder objeção",
            "Entendi, {first_name}. Obrigado por explicar. Posso esclarecer esse ponto e mostrar as opções disponíveis?",
        ),
        _template(
            "finance.overdue",
            "finance",
            "Informar pendência",
            "Oi, {first_name}. Identificamos uma pendência no seu plano. Podemos conferir a situação com você e orientar a regularização?",
        ),
        _template(
            "finance.dispute",
            "finance",
            "Encaminhar contestação",
            "Oi, {first_name}. Recebemos sua observação e vamos conferir a situação com cuidado. Um responsável dará continuidade ao atendimento.",
        ),
        _template(
            "assessment.followup",
            "assessment",
            "Acompanhar avaliação",
            "Oi, {first_name}! Sua avaliação está pronta. Nossa equipe pode revisar os resultados com você e alinhar os próximos passos.",
        ),
        _template(
            "assessment.reassessment",
            "assessment",
            "Convidar para reavaliação",
            "Oi, {first_name}! Está na hora de acompanhar sua evolução. Vamos agendar sua próxima avaliação?",
        ),
        _template(
            "booking.reminder",
            "onboarding",
            "Lembrar agendamento",
            "Oi, {first_name}! Lembrando do seu atendimento em {date}. Se precisar ajustar o horário, avise nossa equipe.",
        ),
        _template(
            "support.reply",
            "support",
            "Responder atendimento",
            "Oi, {first_name}! Recebemos sua mensagem e vamos ajudar. Pode nos contar um pouco mais sobre o que precisa?",
        ),
        _template(
            "personal.guidance",
            "training",
            "Orientação do professor",
            "Oi, {first_name}! Revisei seu acompanhamento. Vamos alinhar o próximo passo com o professor antes de fazer qualquer ajuste.",
        ),
        _template(
            "weekly.briefing",
            "retention",
            "Resumo semanal",
            "Olá! O resumo operacional da semana está disponível no Cordex para revisão da equipe.",
        ),
        _template(
            "birthday.greeting",
            "retention",
            "Parabenizar aniversário",
            "Feliz aniversário, {first_name}! Desejamos um ótimo novo ciclo. Conte com a nossa equipe!",
        ),
    )
}


ROLE_DOMAINS: dict[RoleEnum, set[str]] = {
    RoleEnum.OWNER: {"retention", "onboarding", "commercial", "finance", "assessment", "support", "training"},
    RoleEnum.MANAGER: {"retention", "onboarding", "commercial", "finance", "assessment", "support", "training"},
    RoleEnum.RECEPTIONIST: {"retention", "onboarding", "support"},
    RoleEnum.SALESPERSON: {"commercial"},
    RoleEnum.TRAINER: {"assessment", "training"},
}


def get_template_definition(template_key: str) -> MessageTemplateDefinition:
    try:
        definition = TEMPLATES[template_key]
    except KeyError as exc:
        raise ValueError("Template de mensagem desconhecido") from exc
    if not definition.active:
        raise ValueError("Template de mensagem inativo")
    return definition


def ensure_domain_permission(user: User, domain: str) -> None:
    if domain not in ROLE_DOMAINS.get(user.role, set()):
        raise PermissionError("Seu perfil não pode usar mensagens deste domínio")


def effective_template(db: Session, gym_id: UUID, template_key: str) -> tuple[MessageTemplateDefinition, str, str]:
    definition = get_template_definition(template_key)
    override = db.scalar(
        select(GymMessageTemplateOverride).where(
            GymMessageTemplateOverride.gym_id == gym_id,
            GymMessageTemplateOverride.template_key == template_key,
            GymMessageTemplateOverride.is_active.is_(True),
        )
    )
    if override:
        return definition, override.content, "template_gym_override"
    return definition, definition.content, "template_default"


def validate_template_content(definition: MessageTemplateDefinition, content: str) -> None:
    if not content.strip():
        raise ValueError("A mensagem não pode ficar vazia")
    if len(content) > 2000:
        raise ValueError("A mensagem deve ter no máximo 2.000 caracteres")
    fields = {field for _, field, _, _ in Formatter().parse(content) if field}
    unsupported = fields - set(definition.allowed_variables)
    if unsupported:
        raise ValueError(f"Variáveis não permitidas: {', '.join(sorted(unsupported))}")


def render_message(definition: MessageTemplateDefinition, content: str, variables: Mapping[str, object]) -> str:
    validate_template_content(definition, content)
    missing = [name for name in definition.required_variables if not str(variables.get(name) or "").strip()]
    if missing:
        raise ValueError(f"Dados obrigatórios ausentes: {', '.join(missing)}")
    referenced = {field for _, field, _, _ in Formatter().parse(content) if field}
    missing_referenced = [name for name in referenced if not str(variables.get(name) or "").strip()]
    if missing_referenced:
        raise ValueError(f"Dados usados pelo template estão ausentes: {', '.join(sorted(missing_referenced))}")
    safe_values = {name: str(variables.get(name) or "") for name in definition.allowed_variables}
    return content.format_map(safe_values).strip()
