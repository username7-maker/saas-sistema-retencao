"""AI GYM OS MVP v3 schema

Revision ID: 20260214_0001
Revises:
Create Date: 2026-02-14 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260214_0001"
down_revision = None
branch_labels = None
depends_on = None


role_enum = sa.Enum(
    "owner",
    "manager",
    "salesperson",
    "receptionist",
    name="role_enum",
    native_enum=False,
)
member_status_enum = sa.Enum("active", "paused", "cancelled", name="member_status_enum", native_enum=False)
risk_level_enum = sa.Enum("green", "yellow", "red", name="risk_level_enum", native_enum=False)
checkin_source_enum = sa.Enum("turnstile", "manual", "import", name="checkin_source_enum", native_enum=False)
lead_stage_enum = sa.Enum(
    "new",
    "contact",
    "visit",
    "trial",
    "proposal",
    "won",
    "lost",
    name="lead_stage_enum",
    native_enum=False,
)
task_priority_enum = sa.Enum("low", "medium", "high", "urgent", name="task_priority_enum", native_enum=False)
task_status_enum = sa.Enum("todo", "doing", "done", "cancelled", name="task_status_enum", native_enum=False)
nps_sentiment_enum = sa.Enum("positive", "neutral", "negative", name="nps_sentiment_enum", native_enum=False)
nps_trigger_enum = sa.Enum(
    "after_signup_7d",
    "monthly",
    "yellow_risk",
    "post_cancellation",
    name="nps_trigger_enum",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("refresh_token_hash", sa.Text(), nullable=True),
        sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"], unique=False)
    op.create_index("ix_users_role_active", "users", ["role", "is_active"], unique=False)

    op.create_table(
        "members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("cpf_encrypted", sa.Text(), nullable=True),
        sa.Column("status", member_status_enum, nullable=False, server_default=sa.text("'active'")),
        sa.Column("plan_name", sa.String(length=100), nullable=False, server_default=sa.text("'Plano Base'")),
        sa.Column("monthly_fee", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("join_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("cancellation_date", sa.Date(), nullable=True),
        sa.Column("preferred_shift", sa.String(length=24), nullable=True),
        sa.Column("nps_last_score", sa.SmallInteger(), nullable=False, server_default=sa.text("7")),
        sa.Column("loyalty_months", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("risk_level", risk_level_enum, nullable=False, server_default=sa.text("'green'")),
        sa.Column("last_checkin_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="ck_members_risk_score_range"),
        sa.CheckConstraint("nps_last_score >= 0 AND nps_last_score <= 10", name="ck_members_nps_last_score_range"),
    )
    op.create_index("ix_members_email", "members", ["email"], unique=False)
    op.create_index("ix_members_status", "members", ["status"], unique=False)
    op.create_index("ix_members_join_date", "members", ["join_date"], unique=False)
    op.create_index("ix_members_deleted_at", "members", ["deleted_at"], unique=False)
    op.create_index("ix_members_assigned_user_id", "members", ["assigned_user_id"], unique=False)
    op.create_index("ix_members_risk_level_score", "members", ["risk_level", "risk_score"], unique=False)
    op.create_index("ix_members_status_last_checkin", "members", ["status", "last_checkin_at"], unique=False)

    op.create_table(
        "checkins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkin_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", checkin_source_enum, nullable=False, server_default=sa.text("'manual'")),
        sa.Column("hour_bucket", sa.SmallInteger(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.CheckConstraint("hour_bucket >= 0 AND hour_bucket <= 23", name="ck_checkins_hour_bucket_range"),
        sa.CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_checkins_weekday_range"),
        sa.UniqueConstraint("member_id", "checkin_at", name="uq_checkin_member_datetime"),
    )
    op.create_index("ix_checkins_member_id", "checkins", ["member_id"], unique=False)
    op.create_index("ix_checkins_checkin_at", "checkins", ["checkin_at"], unique=False)
    op.create_index("ix_checkins_member_date_desc", "checkins", ["member_id", "checkin_at"], unique=False)

    op.create_table(
        "risk_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level", risk_level_enum, nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("action_history", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("automation_stage", sa.String(length=32), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_risk_alerts_member_id", "risk_alerts", ["member_id"], unique=False)
    op.create_index("ix_risk_alerts_level", "risk_alerts", ["level"], unique=False)
    op.create_index("ix_risk_alerts_member_created", "risk_alerts", ["member_id", "created_at"], unique=False)
    op.create_index("ix_risk_alerts_level_resolved", "risk_alerts", ["level", "resolved"], unique=False)

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("converted_member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("stage", lead_stage_enum, nullable=False, server_default=sa.text("'new'")),
        sa.Column("estimated_value", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("acquisition_cost", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("lost_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["converted_member_id"], ["members.id"], ondelete="SET NULL"),
        sa.CheckConstraint("estimated_value >= 0", name="ck_leads_lead_estimated_value_non_negative"),
        sa.CheckConstraint("acquisition_cost >= 0", name="ck_leads_lead_acquisition_cost_non_negative"),
        sa.UniqueConstraint("converted_member_id", name="uq_leads_converted_member_id"),
    )
    op.create_index("ix_leads_owner_id", "leads", ["owner_id"], unique=False)
    op.create_index("ix_leads_email", "leads", ["email"], unique=False)
    op.create_index("ix_leads_source", "leads", ["source"], unique=False)
    op.create_index("ix_leads_stage", "leads", ["stage"], unique=False)
    op.create_index("ix_leads_deleted_at", "leads", ["deleted_at"], unique=False)
    op.create_index("ix_leads_stage_source", "leads", ["stage", "source"], unique=False)
    op.create_index("ix_leads_last_contact", "leads", ["last_contact_at"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", task_priority_enum, nullable=False, server_default=sa.text("'medium'")),
        sa.Column("status", task_status_enum, nullable=False, server_default=sa.text("'todo'")),
        sa.Column("kanban_column", sa.String(length=32), nullable=False, server_default=sa.text("'todo'")),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suggested_message", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_tasks_member_id", "tasks", ["member_id"], unique=False)
    op.create_index("ix_tasks_lead_id", "tasks", ["lead_id"], unique=False)
    op.create_index("ix_tasks_assigned_to_user_id", "tasks", ["assigned_to_user_id"], unique=False)
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)
    op.create_index("ix_tasks_deleted_at", "tasks", ["deleted_at"], unique=False)
    op.create_index("ix_tasks_status_assigned", "tasks", ["status", "assigned_to_user_id"], unique=False)
    op.create_index("ix_tasks_due_status", "tasks", ["due_date", "status"], unique=False)
    op.create_index("ix_tasks_kanban_column", "tasks", ["kanban_column"], unique=False)

    op.create_table(
        "nps_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("sentiment", nps_sentiment_enum, nullable=False),
        sa.Column("sentiment_summary", sa.Text(), nullable=True),
        sa.Column("trigger", nps_trigger_enum, nullable=False),
        sa.Column("response_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.CheckConstraint("score >= 0 AND score <= 10", name="ck_nps_responses_nps_score_range"),
    )
    op.create_index("ix_nps_responses_member_id", "nps_responses", ["member_id"], unique=False)
    op.create_index("ix_nps_responses_score", "nps_responses", ["score"], unique=False)
    op.create_index("ix_nps_member_date", "nps_responses", ["member_id", "response_date"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity", sa.String(length=80), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)
    op.create_index("ix_audit_logs_member_id", "audit_logs", ["member_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_action_entity_date", "audit_logs", ["action", "entity", "created_at"], unique=False)
    op.create_index("ix_audit_user_date", "audit_logs", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_user_date", table_name="audit_logs")
    op.drop_index("ix_audit_action_entity_date", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_member_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_nps_member_date", table_name="nps_responses")
    op.drop_index("ix_nps_responses_score", table_name="nps_responses")
    op.drop_index("ix_nps_responses_member_id", table_name="nps_responses")
    op.drop_table("nps_responses")

    op.drop_index("ix_tasks_kanban_column", table_name="tasks")
    op.drop_index("ix_tasks_due_status", table_name="tasks")
    op.drop_index("ix_tasks_status_assigned", table_name="tasks")
    op.drop_index("ix_tasks_deleted_at", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_assigned_to_user_id", table_name="tasks")
    op.drop_index("ix_tasks_lead_id", table_name="tasks")
    op.drop_index("ix_tasks_member_id", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_leads_last_contact", table_name="leads")
    op.drop_index("ix_leads_stage_source", table_name="leads")
    op.drop_index("ix_leads_deleted_at", table_name="leads")
    op.drop_index("ix_leads_stage", table_name="leads")
    op.drop_index("ix_leads_source", table_name="leads")
    op.drop_index("ix_leads_email", table_name="leads")
    op.drop_index("ix_leads_owner_id", table_name="leads")
    op.drop_table("leads")

    op.drop_index("ix_risk_alerts_level_resolved", table_name="risk_alerts")
    op.drop_index("ix_risk_alerts_member_created", table_name="risk_alerts")
    op.drop_index("ix_risk_alerts_level", table_name="risk_alerts")
    op.drop_index("ix_risk_alerts_member_id", table_name="risk_alerts")
    op.drop_table("risk_alerts")

    op.drop_index("ix_checkins_member_date_desc", table_name="checkins")
    op.drop_index("ix_checkins_checkin_at", table_name="checkins")
    op.drop_index("ix_checkins_member_id", table_name="checkins")
    op.drop_table("checkins")

    op.drop_index("ix_members_status_last_checkin", table_name="members")
    op.drop_index("ix_members_risk_level_score", table_name="members")
    op.drop_index("ix_members_assigned_user_id", table_name="members")
    op.drop_index("ix_members_deleted_at", table_name="members")
    op.drop_index("ix_members_join_date", table_name="members")
    op.drop_index("ix_members_status", table_name="members")
    op.drop_index("ix_members_email", table_name="members")
    op.drop_table("members")

    op.drop_index("ix_users_role_active", table_name="users")
    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
