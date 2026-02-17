"""add gym multi-tenant scope

Revision ID: 20260217_0004
Revises: 20260216_0003
Create Date: 2026-02-17 00:04:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260217_0004"
down_revision = "20260216_0003"
branch_labels = None
depends_on = None

DEFAULT_GYM_ID = "11111111-1111-1111-1111-111111111111"


def upgrade() -> None:
    connection = op.get_bind()

    op.create_table(
        "gyms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_gyms_slug_unique", "gyms", ["slug"], unique=True)

    connection.execute(
        sa.text(
            """
            INSERT INTO gyms (id, name, slug, is_active, created_at, updated_at)
            VALUES (CAST(:gym_id AS uuid), 'Academia Principal', 'academia-principal', true, now(), now())
            ON CONFLICT (id) DO NOTHING
            """
        ),
        {"gym_id": DEFAULT_GYM_ID},
    )

    op.add_column("users", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("members", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("checkins", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("risk_alerts", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("leads", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("tasks", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("nps_responses", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("audit_logs", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("in_app_notifications", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("automation_rules", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("message_logs", sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=True))

    connection.execute(sa.text("UPDATE users SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    op.execute(
        sa.text(
            """
            UPDATE members m
            SET gym_id = u.gym_id
            FROM users u
            WHERE m.assigned_user_id = u.id AND m.gym_id IS NULL
            """
        )
    )
    connection.execute(sa.text("UPDATE members SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    op.execute(
        sa.text(
            """
            UPDATE checkins c
            SET gym_id = m.gym_id
            FROM members m
            WHERE c.member_id = m.id AND c.gym_id IS NULL
            """
        )
    )
    connection.execute(sa.text("UPDATE checkins SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    op.execute(
        sa.text(
            """
            UPDATE risk_alerts ra
            SET gym_id = m.gym_id
            FROM members m
            WHERE ra.member_id = m.id AND ra.gym_id IS NULL
            """
        )
    )
    connection.execute(sa.text("UPDATE risk_alerts SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    op.execute(
        sa.text(
            """
            UPDATE leads l
            SET gym_id = u.gym_id
            FROM users u
            WHERE l.owner_id = u.id AND l.gym_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE leads l
            SET gym_id = m.gym_id
            FROM members m
            WHERE l.converted_member_id = m.id AND l.gym_id IS NULL
            """
        )
    )
    connection.execute(sa.text("UPDATE leads SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    op.execute(
        sa.text(
            """
            UPDATE tasks t
            SET gym_id = m.gym_id
            FROM members m
            WHERE t.member_id = m.id AND t.gym_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tasks t
            SET gym_id = l.gym_id
            FROM leads l
            WHERE t.lead_id = l.id AND t.gym_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tasks t
            SET gym_id = u.gym_id
            FROM users u
            WHERE t.assigned_to_user_id = u.id AND t.gym_id IS NULL
            """
        )
    )
    connection.execute(sa.text("UPDATE tasks SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    op.execute(
        sa.text(
            """
            UPDATE nps_responses n
            SET gym_id = m.gym_id
            FROM members m
            WHERE n.member_id = m.id AND n.gym_id IS NULL
            """
        )
    )
    connection.execute(sa.text("UPDATE nps_responses SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    op.execute(
        sa.text(
            """
            UPDATE audit_logs a
            SET gym_id = u.gym_id
            FROM users u
            WHERE a.user_id = u.id AND a.gym_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE audit_logs a
            SET gym_id = m.gym_id
            FROM members m
            WHERE a.member_id = m.id AND a.gym_id IS NULL
            """
        )
    )
    connection.execute(sa.text("UPDATE audit_logs SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    op.execute(
        sa.text(
            """
            UPDATE in_app_notifications n
            SET gym_id = u.gym_id
            FROM users u
            WHERE n.user_id = u.id AND n.gym_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE in_app_notifications n
            SET gym_id = m.gym_id
            FROM members m
            WHERE n.member_id = m.id AND n.gym_id IS NULL
            """
        )
    )
    connection.execute(sa.text("UPDATE in_app_notifications SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    connection.execute(sa.text("UPDATE automation_rules SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    op.execute(
        sa.text(
            """
            UPDATE message_logs ml
            SET gym_id = m.gym_id
            FROM members m
            WHERE ml.member_id = m.id AND ml.gym_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE message_logs ml
            SET gym_id = ar.gym_id
            FROM automation_rules ar
            WHERE ml.automation_rule_id = ar.id AND ml.gym_id IS NULL
            """
        )
    )
    connection.execute(sa.text("UPDATE message_logs SET gym_id = CAST(:gym_id AS uuid) WHERE gym_id IS NULL"), {"gym_id": DEFAULT_GYM_ID})

    op.alter_column("users", "gym_id", nullable=False)
    op.alter_column("members", "gym_id", nullable=False)
    op.alter_column("checkins", "gym_id", nullable=False)
    op.alter_column("risk_alerts", "gym_id", nullable=False)
    op.alter_column("leads", "gym_id", nullable=False)
    op.alter_column("tasks", "gym_id", nullable=False)
    op.alter_column("nps_responses", "gym_id", nullable=False)
    op.alter_column("audit_logs", "gym_id", nullable=False)
    op.alter_column("in_app_notifications", "gym_id", nullable=False)
    op.alter_column("automation_rules", "gym_id", nullable=False)
    op.alter_column("message_logs", "gym_id", nullable=False)

    op.create_foreign_key("fk_users_gym_id_gyms", "users", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_members_gym_id_gyms", "members", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_checkins_gym_id_gyms", "checkins", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_risk_alerts_gym_id_gyms", "risk_alerts", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_leads_gym_id_gyms", "leads", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_tasks_gym_id_gyms", "tasks", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_nps_responses_gym_id_gyms", "nps_responses", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_audit_logs_gym_id_gyms", "audit_logs", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_in_app_notifications_gym_id_gyms", "in_app_notifications", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_automation_rules_gym_id_gyms", "automation_rules", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_message_logs_gym_id_gyms", "message_logs", "gyms", ["gym_id"], ["id"], ondelete="CASCADE")

    op.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_email"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_users_email"))

    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_gym_id", "users", ["gym_id"], unique=False)
    op.create_index("ix_users_gym_email", "users", ["gym_id", "email"], unique=True)

    op.create_index("ix_members_gym_id", "members", ["gym_id"], unique=False)
    op.create_index("ix_members_gym_status", "members", ["gym_id", "status"], unique=False)

    op.create_index("ix_checkins_gym_id", "checkins", ["gym_id"], unique=False)
    op.create_index("ix_checkins_gym_checkin_at", "checkins", ["gym_id", "checkin_at"], unique=False)

    op.create_index("ix_risk_alerts_gym_id", "risk_alerts", ["gym_id"], unique=False)
    op.create_index("ix_risk_alerts_gym_level", "risk_alerts", ["gym_id", "level"], unique=False)

    op.create_index("ix_leads_gym_id", "leads", ["gym_id"], unique=False)
    op.create_index("ix_leads_gym_stage", "leads", ["gym_id", "stage"], unique=False)

    op.create_index("ix_tasks_gym_id", "tasks", ["gym_id"], unique=False)
    op.create_index("ix_tasks_gym_status", "tasks", ["gym_id", "status"], unique=False)

    op.create_index("ix_nps_responses_gym_id", "nps_responses", ["gym_id"], unique=False)
    op.create_index("ix_nps_gym_response_date", "nps_responses", ["gym_id", "response_date"], unique=False)

    op.create_index("ix_audit_logs_gym_id", "audit_logs", ["gym_id"], unique=False)
    op.create_index("ix_audit_logs_gym_created", "audit_logs", ["gym_id", "created_at"], unique=False)

    op.create_index("ix_in_app_notifications_gym_id", "in_app_notifications", ["gym_id"], unique=False)
    op.create_index("ix_in_app_notifications_gym_created", "in_app_notifications", ["gym_id", "created_at"], unique=False)

    op.create_index("ix_automation_rules_gym_id", "automation_rules", ["gym_id"], unique=False)
    op.create_index("ix_automation_rules_gym_active", "automation_rules", ["gym_id", "is_active"], unique=False)

    op.create_index("ix_message_logs_gym_id", "message_logs", ["gym_id"], unique=False)
    op.create_index("ix_message_logs_gym_created", "message_logs", ["gym_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_message_logs_gym_created", table_name="message_logs")
    op.drop_index("ix_message_logs_gym_id", table_name="message_logs")
    op.drop_index("ix_automation_rules_gym_active", table_name="automation_rules")
    op.drop_index("ix_automation_rules_gym_id", table_name="automation_rules")
    op.drop_index("ix_in_app_notifications_gym_created", table_name="in_app_notifications")
    op.drop_index("ix_in_app_notifications_gym_id", table_name="in_app_notifications")
    op.drop_index("ix_audit_logs_gym_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_gym_id", table_name="audit_logs")
    op.drop_index("ix_nps_gym_response_date", table_name="nps_responses")
    op.drop_index("ix_nps_responses_gym_id", table_name="nps_responses")
    op.drop_index("ix_tasks_gym_status", table_name="tasks")
    op.drop_index("ix_tasks_gym_id", table_name="tasks")
    op.drop_index("ix_leads_gym_stage", table_name="leads")
    op.drop_index("ix_leads_gym_id", table_name="leads")
    op.drop_index("ix_risk_alerts_gym_level", table_name="risk_alerts")
    op.drop_index("ix_risk_alerts_gym_id", table_name="risk_alerts")
    op.drop_index("ix_checkins_gym_checkin_at", table_name="checkins")
    op.drop_index("ix_checkins_gym_id", table_name="checkins")
    op.drop_index("ix_members_gym_status", table_name="members")
    op.drop_index("ix_members_gym_id", table_name="members")
    op.drop_index("ix_users_gym_email", table_name="users")
    op.drop_index("ix_users_gym_id", table_name="users")

    op.drop_constraint("fk_message_logs_gym_id_gyms", "message_logs", type_="foreignkey")
    op.drop_constraint("fk_automation_rules_gym_id_gyms", "automation_rules", type_="foreignkey")
    op.drop_constraint("fk_in_app_notifications_gym_id_gyms", "in_app_notifications", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_gym_id_gyms", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_nps_responses_gym_id_gyms", "nps_responses", type_="foreignkey")
    op.drop_constraint("fk_tasks_gym_id_gyms", "tasks", type_="foreignkey")
    op.drop_constraint("fk_leads_gym_id_gyms", "leads", type_="foreignkey")
    op.drop_constraint("fk_risk_alerts_gym_id_gyms", "risk_alerts", type_="foreignkey")
    op.drop_constraint("fk_checkins_gym_id_gyms", "checkins", type_="foreignkey")
    op.drop_constraint("fk_members_gym_id_gyms", "members", type_="foreignkey")
    op.drop_constraint("fk_users_gym_id_gyms", "users", type_="foreignkey")

    op.drop_column("message_logs", "gym_id")
    op.drop_column("automation_rules", "gym_id")
    op.drop_column("in_app_notifications", "gym_id")
    op.drop_column("audit_logs", "gym_id")
    op.drop_column("nps_responses", "gym_id")
    op.drop_column("tasks", "gym_id")
    op.drop_column("leads", "gym_id")
    op.drop_column("risk_alerts", "gym_id")
    op.drop_column("checkins", "gym_id")
    op.drop_column("members", "gym_id")
    op.drop_column("users", "gym_id")

    op.drop_index("ix_gyms_slug_unique", table_name="gyms")
    op.drop_table("gyms")

    op.execute(sa.text("DROP INDEX IF EXISTS ix_users_email"))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_unique_constraint("uq_users_email", "users", ["email"])

