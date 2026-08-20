"""cordex method os v1

Revision ID: 20260603_0047
Revises: 20260527_0046
Create Date: 2026-06-03
"""

from collections.abc import Sequence
import json
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260603_0047"
down_revision: str | None = "20260527_0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PILLAR = sa.Enum("acquisition", "sales", "post_sale", name="method_pillar_enum", native_enum=False)
PERSON_TYPE = sa.Enum("lead", "customer", "inactive_customer", "prospect", name="method_person_type_enum", native_enum=False)
EVENT_SOURCE = sa.Enum("manual", "import", "integration", "automation", "ai", name="method_event_source_enum", native_enum=False)
TASK_PRIORITY = sa.Enum("low", "medium", "high", "critical", name="method_task_priority_enum", native_enum=False)
TASK_STATUS = sa.Enum("open", "in_progress", "done", "dismissed", "expired", name="method_task_status_enum", native_enum=False)
ACTION_TYPE = sa.Enum("whatsapp", "call", "email", "in_person", "internal_note", "other", name="method_action_type_enum", native_enum=False)
ACTION_RESULT = sa.Enum("no_response", "responded", "scheduled", "bought", "returned", "renewed", "lost", "dismissed", "other", name="method_action_result_enum", native_enum=False)
REPORT_TYPE = sa.Enum("weekly", "monthly", "pilot", "internal", name="method_report_type_enum", native_enum=False)
IMPORT_TYPE = sa.Enum("people", "events", name="method_import_type_enum", native_enum=False)
IMPORT_STATUS = sa.Enum("previewed", "imported", "failed", name="method_import_status_enum", native_enum=False)


SEGMENTS = [
    {
        "id": UUID("10000000-0000-4000-8000-000000000001"),
        "slug": "academia",
        "name": "Academia",
        "description": "Academias e studios com recorrencia, frequencia e retencao como motor central.",
        "default_entry_pillar": "post_sale",
        "channels": ["WhatsApp", "Instagram", "indicacao", "visita presencial"],
        "questions": [
            "Qual seu objetivo principal?",
            "Qual horario costuma treinar?",
            "Ja treinou antes?",
            "Esta comparando com outra academia?",
        ],
        "signals": ["low_frequency", "no_checkin_7_days", "plan_expiring", "evaluation_pending"],
        "templates": {
            "retomada_frequencia": "Oi {nome}, senti sua falta nos treinos. Quer que eu te ajude a encaixar um horario esta semana?",
            "boas_vindas": "Oi {nome}, seja bem-vindo. Vamos alinhar objetivo, horario e primeiro passo?",
            "renovacao": "Oi {nome}, seu plano esta perto de vencer. Posso te ajudar a renovar sem interromper a rotina?",
        },
        "metrics": ["recuperacao", "churn", "frequencia", "retencao"],
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000002"),
        "slug": "clinica",
        "name": "Clinica",
        "description": "Clinicas que dependem de retorno, agenda ocupada e continuidade de tratamento.",
        "default_entry_pillar": "post_sale",
        "channels": ["WhatsApp", "telefone", "indicacao"],
        "questions": ["Qual sua queixa principal?", "Ha urgencia?", "Tem convenio?", "Qual disponibilidade?"],
        "signals": ["no_return_scheduled", "treatment_incomplete", "appointment_no_show"],
        "templates": {
            "remarcar_retorno": "Oi {nome}, ficou pendente remarcar seu retorno. Qual horario fica melhor para voce?",
            "confirmar_consulta": "Oi {nome}, passando para confirmar sua consulta e evitar desencontro de agenda.",
            "resgate_inativo": "Oi {nome}, quer que eu te ajude a retomar seu acompanhamento?",
        },
        "metrics": ["retorno", "agenda_ocupada", "recompra"],
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000003"),
        "slug": "estetica",
        "name": "Estetica",
        "description": "Clinicas e studios de estetica com pacotes, manutencao e recompra.",
        "default_entry_pillar": "post_sale",
        "channels": ["Instagram", "WhatsApp", "indicacao"],
        "questions": ["Qual procedimento voce procura?", "Qual objetivo?", "Ja fez esse tratamento antes?"],
        "signals": ["package_finished_no_repurchase", "customer_inactive", "maintenance_due"],
        "templates": {
            "manutencao": "Oi {nome}, sua manutencao ja esta no periodo ideal. Quer ver horarios disponiveis?",
            "recompra": "Oi {nome}, seu pacote terminou. Posso te mostrar a melhor continuidade para o resultado?",
            "reativacao": "Oi {nome}, faz um tempo que nao te vemos por aqui. Quer retomar seu plano?",
        },
        "metrics": ["recompra", "ticket", "ltv"],
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000004"),
        "slug": "escola_curso",
        "name": "Escola/Curso",
        "description": "Escolas e cursos com permanencia, presenca, renovacao e inadimplencia operacional.",
        "default_entry_pillar": "post_sale",
        "channels": ["site", "WhatsApp", "indicacao"],
        "questions": ["Qual seu objetivo?", "Qual seu nivel?", "Qual disponibilidade?", "Forma de pagamento?"],
        "signals": ["consecutive_absences", "payment_overdue", "low_participation"],
        "templates": {
            "faltas": "Oi {nome}, notei algumas faltas recentes. Quer ajuda para ajustar sua rotina de aulas?",
            "renovacao": "Oi {nome}, sua renovacao esta chegando. Posso te ajudar a manter a vaga ativa?",
            "regularizacao": "Oi {nome}, tem uma pendencia que pode travar sua continuidade. Posso te orientar?",
        },
        "metrics": ["evasao", "presenca", "renovacao"],
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000005"),
        "slug": "consorcio",
        "name": "Consorcio",
        "description": "Operacoes comerciais com simulacao, proposta, follow-up e fechamento consultivo.",
        "default_entry_pillar": "sales",
        "channels": ["indicacao", "WhatsApp", "trafego", "lista"],
        "questions": ["Qual objetivo?", "Qual credito desejado?", "Qual prazo?", "Tem entrada?"],
        "signals": ["simulation_no_response", "proposal_no_response", "followup_due"],
        "templates": {
            "simulacao": "Oi {nome}, vi sua simulacao. Posso te explicar os proximos passos de forma simples?",
            "proposta": "Oi {nome}, passando para acompanhar a proposta e tirar duvidas antes da decisao.",
            "followup": "Oi {nome}, faz sentido retomarmos sua analise hoje?",
        },
        "metrics": ["conversao", "propostas", "followups"],
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000006"),
        "slug": "servico_b2b_local",
        "name": "Servico B2B local",
        "description": "Servicos B2B locais com relacionamento, proposta, renovacao e contrato.",
        "default_entry_pillar": "sales",
        "channels": ["indicacao", "site", "WhatsApp", "reuniao"],
        "questions": ["Qual necessidade?", "Qual orcamento?", "Qual prazo?", "Quem decide?"],
        "signals": ["proposal_no_response", "contract_expiring", "followup_due"],
        "templates": {
            "proposta": "Oi {nome}, passando para acompanhar a proposta e entender se falta algo para avancarmos.",
            "renovacao": "Oi {nome}, seu contrato esta perto do fim. Quer revisar a renovacao comigo?",
            "diagnostico": "Oi {nome}, posso te ajudar a organizar o diagnostico e proximos passos?",
        },
        "metrics": ["fechamento", "ciclo_de_venda", "receita"],
    },
]


def _quote_sql(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _jsonb_sql(value: object) -> str:
    return f"{_quote_sql(json.dumps(value, ensure_ascii=True))}::jsonb"


def upgrade() -> None:
    op.create_table(
        "method_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("default_entry_pillar", PILLAR, server_default="post_sale", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_method_segments_slug_unique", "method_segments", ["slug"], unique=True)

    op.add_column("gyms", sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("gyms", sa.Column("cordex_status", sa.String(length=30), server_default="active", nullable=False))
    op.add_column("gyms", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("gyms", sa.Column("state", sa.String(length=40), nullable=True))
    op.add_column("gyms", sa.Column("main_contact_name", sa.String(length=160), nullable=True))
    op.add_column("gyms", sa.Column("main_contact_phone", sa.String(length=40), nullable=True))
    op.add_column("gyms", sa.Column("main_contact_email", sa.String(length=255), nullable=True))
    op.create_index("ix_gyms_segment_id", "gyms", ["segment_id"], unique=False)
    op.create_foreign_key("fk_gyms_segment_id_method_segments", "gyms", "method_segments", ["segment_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "method_segment_playbooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channels_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("qualification_questions_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("risk_opportunity_signals_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("message_templates_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("success_metrics_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["segment_id"], ["method_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_method_segment_playbooks_segment_unique", "method_segment_playbooks", ["segment_id"], unique=True)

    op.create_table(
        "method_client_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("active_pillars_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("""'{"acquisition": true, "sales": true, "post_sale": true}'::jsonb"""), nullable=False),
        sa.Column("entry_pillar", PILLAR, server_default="post_sale", nullable=False),
        sa.Column("toolkit_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("baseline_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("success_criteria_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("cadence_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["segment_id"], ["method_segments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_method_client_configs_gym_unique", "method_client_configs", ["gym_id"], unique=True)
    op.create_index("ix_method_client_configs_segment", "method_client_configs", ["segment_id"], unique=False)

    op.create_table(
        "method_people",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("person_type", PERSON_TYPE, server_default="lead", nullable=False),
        sa.Column("status", sa.String(length=80), server_default="active", nullable=False),
        sa.Column("source_channel", sa.String(length=80), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_method_people_gym_type_status", "method_people", ["gym_id", "person_type", "status"], unique=False)
    op.create_index("ix_method_people_gym_phone", "method_people", ["gym_id", "phone"], unique=False)
    op.create_index("ix_method_people_gym_external", "method_people", ["gym_id", "external_id"], unique=False)

    op.create_table(
        "method_operational_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pillar", PILLAR, nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("event_source", EVENT_SOURCE, server_default="manual", nullable=False),
        sa.Column("event_payload_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["method_people.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_method_events_gym_pillar_type", "method_operational_events", ["gym_id", "pillar", "event_type"], unique=False)
    op.create_index("ix_method_events_gym_occurred", "method_operational_events", ["gym_id", "occurred_at"], unique=False)
    op.create_index("ix_method_events_person", "method_operational_events", ["person_id"], unique=False)

    op.create_table(
        "method_operational_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pillar", PILLAR, nullable=False),
        sa.Column("task_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_role", sa.String(length=80), server_default="operacao", nullable=False),
        sa.Column("assigned_to", sa.String(length=120), nullable=True),
        sa.Column("priority", TASK_PRIORITY, server_default="medium", nullable=False),
        sa.Column("status", TASK_STATUS, server_default="open", nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suggested_message", sa.Text(), nullable=True),
        sa.Column("wa_me_link", sa.Text(), nullable=True),
        sa.Column("dismissal_reason", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requires_human_approval", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("ai_metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["method_people.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["method_operational_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_method_tasks_gym_status_due", "method_operational_tasks", ["gym_id", "status", "due_date"], unique=False)
    op.create_index("ix_method_tasks_gym_pillar", "method_operational_tasks", ["gym_id", "pillar"], unique=False)
    op.create_index("ix_method_tasks_person", "method_operational_tasks", ["person_id"], unique=False)
    op.create_index("ix_method_tasks_event", "method_operational_tasks", ["event_id"], unique=False)

    op.create_table(
        "method_human_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", ACTION_TYPE, nullable=False),
        sa.Column("action_summary", sa.Text(), nullable=False),
        sa.Column("result", ACTION_RESULT, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["method_people.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["method_operational_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_method_actions_gym_created", "method_human_actions", ["gym_id", "created_at"], unique=False)
    op.create_index("ix_method_actions_task", "method_human_actions", ["task_id"], unique=False)
    op.create_index("ix_method_actions_person", "method_human_actions", ["person_id"], unique=False)

    op.create_table(
        "method_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome_type", sa.String(length=80), nullable=False),
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["person_id"], ["method_people.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["method_operational_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["action_id"], ["method_human_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_method_outcomes_gym_type_measured", "method_outcomes", ["gym_id", "outcome_type", "measured_at"], unique=False)
    op.create_index("ix_method_outcomes_task", "method_outcomes", ["task_id"], unique=False)
    op.create_index("ix_method_outcomes_action", "method_outcomes", ["action_id"], unique=False)

    op.create_table(
        "method_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", REPORT_TYPE, nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("recommendations_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_method_reports_gym_type_period", "method_reports", ["gym_id", "report_type", "period_start", "period_end"], unique=False)

    op.create_table(
        "method_import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_type", IMPORT_TYPE, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("status", IMPORT_STATUS, nullable=False),
        sa.Column("column_mapping_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error_report_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_method_import_batches_gym_type_created", "method_import_batches", ["gym_id", "import_type", "created_at"], unique=False)

    for index, item in enumerate(SEGMENTS, start=1):
        op.execute(
            sa.text(
                "INSERT INTO method_segments "
                "(id, slug, name, description, default_entry_pillar, created_at, updated_at) "
                f"VALUES ({_quote_sql(item['id'])}, {_quote_sql(item['slug'])}, {_quote_sql(item['name'])}, "
                f"{_quote_sql(item['description'])}, {_quote_sql(item['default_entry_pillar'])}, now(), now())"
            )
        )
        op.execute(
            sa.text(
                "INSERT INTO method_segment_playbooks "
                "(id, segment_id, channels_json, qualification_questions_json, risk_opportunity_signals_json, "
                "message_templates_json, success_metrics_json, created_at, updated_at) "
                f"VALUES ({_quote_sql(UUID(f'20000000-0000-4000-8000-{index:012d}'))}, "
                f"{_quote_sql(item['id'])}, {_jsonb_sql(item['channels'])}, {_jsonb_sql(item['questions'])}, "
                f"{_jsonb_sql(item['signals'])}, {_jsonb_sql(item['templates'])}, {_jsonb_sql(item['metrics'])}, "
                "now(), now())"
            )
        )


def downgrade() -> None:
    op.drop_index("ix_method_import_batches_gym_type_created", table_name="method_import_batches")
    op.drop_table("method_import_batches")
    op.drop_index("ix_method_reports_gym_type_period", table_name="method_reports")
    op.drop_table("method_reports")
    op.drop_index("ix_method_outcomes_action", table_name="method_outcomes")
    op.drop_index("ix_method_outcomes_task", table_name="method_outcomes")
    op.drop_index("ix_method_outcomes_gym_type_measured", table_name="method_outcomes")
    op.drop_table("method_outcomes")
    op.drop_index("ix_method_actions_person", table_name="method_human_actions")
    op.drop_index("ix_method_actions_task", table_name="method_human_actions")
    op.drop_index("ix_method_actions_gym_created", table_name="method_human_actions")
    op.drop_table("method_human_actions")
    op.drop_index("ix_method_tasks_event", table_name="method_operational_tasks")
    op.drop_index("ix_method_tasks_person", table_name="method_operational_tasks")
    op.drop_index("ix_method_tasks_gym_pillar", table_name="method_operational_tasks")
    op.drop_index("ix_method_tasks_gym_status_due", table_name="method_operational_tasks")
    op.drop_table("method_operational_tasks")
    op.drop_index("ix_method_events_person", table_name="method_operational_events")
    op.drop_index("ix_method_events_gym_occurred", table_name="method_operational_events")
    op.drop_index("ix_method_events_gym_pillar_type", table_name="method_operational_events")
    op.drop_table("method_operational_events")
    op.drop_index("ix_method_people_gym_external", table_name="method_people")
    op.drop_index("ix_method_people_gym_phone", table_name="method_people")
    op.drop_index("ix_method_people_gym_type_status", table_name="method_people")
    op.drop_table("method_people")
    op.drop_index("ix_method_client_configs_segment", table_name="method_client_configs")
    op.drop_index("ix_method_client_configs_gym_unique", table_name="method_client_configs")
    op.drop_table("method_client_configs")
    op.drop_index("ix_method_segment_playbooks_segment_unique", table_name="method_segment_playbooks")
    op.drop_table("method_segment_playbooks")
    op.drop_constraint("fk_gyms_segment_id_method_segments", "gyms", type_="foreignkey")
    op.drop_index("ix_gyms_segment_id", table_name="gyms")
    op.drop_column("gyms", "main_contact_email")
    op.drop_column("gyms", "main_contact_phone")
    op.drop_column("gyms", "main_contact_name")
    op.drop_column("gyms", "state")
    op.drop_column("gyms", "city")
    op.drop_column("gyms", "cordex_status")
    op.drop_column("gyms", "segment_id")
    op.drop_index("ix_method_segments_slug_unique", table_name="method_segments")
    op.drop_table("method_segments")
