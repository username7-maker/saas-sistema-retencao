"""add ai triage recommendations

Revision ID: 20260418_0031
Revises: 20260414_0030
Create Date: 2026-04-18 14:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260418_0031"
down_revision = "20260414_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_triage_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_domain", sa.String(length=32), nullable=False),
        sa.Column("source_entity_kind", sa.String(length=16), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("priority_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("suggestion_state", sa.String(length=24), nullable=False, server_default="suggested"),
        sa.Column("approval_state", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("execution_state", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("outcome_state", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_triage_recommendations")),
        sa.UniqueConstraint(
            "gym_id",
            "source_domain",
            "source_entity_kind",
            "source_entity_id",
            name="uq_ai_triage_recommendation_natural_key",
        ),
    )
    op.create_index(
        "ix_ai_triage_recommendations_gym_active_priority",
        "ai_triage_recommendations",
        ["gym_id", "is_active", "priority_score"],
        unique=False,
    )
    op.create_index(
        "ix_ai_triage_recommendations_source",
        "ai_triage_recommendations",
        ["source_domain", "source_entity_kind", "source_entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_triage_recommendations_gym_id"),
        "ai_triage_recommendations",
        ["gym_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_triage_recommendations_member_id"),
        "ai_triage_recommendations",
        ["member_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_triage_recommendations_lead_id"),
        "ai_triage_recommendations",
        ["lead_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_triage_recommendations_lead_id"), table_name="ai_triage_recommendations")
    op.drop_index(op.f("ix_ai_triage_recommendations_member_id"), table_name="ai_triage_recommendations")
    op.drop_index(op.f("ix_ai_triage_recommendations_gym_id"), table_name="ai_triage_recommendations")
    op.drop_index("ix_ai_triage_recommendations_source", table_name="ai_triage_recommendations")
    op.drop_index("ix_ai_triage_recommendations_gym_active_priority", table_name="ai_triage_recommendations")
    op.drop_table("ai_triage_recommendations")
