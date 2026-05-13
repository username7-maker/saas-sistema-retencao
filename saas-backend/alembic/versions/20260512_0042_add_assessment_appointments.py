"""add assessment appointments

Revision ID: 20260512_0042
Revises: 20260507_0041
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260512_0042"
down_revision: str | None = "20260507_0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assessment_appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluator_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assessment_type", sa.String(length=60), server_default="physical_assessment", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="scheduled", nullable=False),
        sa.Column("payment_status", sa.String(length=24), server_default="unknown", nullable=False),
        sa.Column("evaluator_name_raw", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=60), server_default="manual", nullable=False),
        sa.Column("external_reference", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["evaluator_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gym_id", "external_reference", name="uq_assessment_appointments_gym_external_reference"),
    )
    op.create_index("ix_assessment_appointments_gym_id", "assessment_appointments", ["gym_id"])
    op.create_index("ix_assessment_appointments_member_id", "assessment_appointments", ["member_id"])
    op.create_index("ix_assessment_appointments_gym_scheduled", "assessment_appointments", ["gym_id", "scheduled_at"])
    op.create_index("ix_assessment_appointments_member_scheduled", "assessment_appointments", ["member_id", "scheduled_at"])
    op.create_index("ix_assessment_appointments_gym_status", "assessment_appointments", ["gym_id", "status"])
    op.create_index("ix_assessment_appointments_gym_payment", "assessment_appointments", ["gym_id", "payment_status"])
    op.create_index("ix_assessment_appointments_evaluator", "assessment_appointments", ["evaluator_user_id"])


def downgrade() -> None:
    op.drop_index("ix_assessment_appointments_evaluator", table_name="assessment_appointments")
    op.drop_index("ix_assessment_appointments_gym_payment", table_name="assessment_appointments")
    op.drop_index("ix_assessment_appointments_gym_status", table_name="assessment_appointments")
    op.drop_index("ix_assessment_appointments_member_scheduled", table_name="assessment_appointments")
    op.drop_index("ix_assessment_appointments_gym_scheduled", table_name="assessment_appointments")
    op.drop_index("ix_assessment_appointments_member_id", table_name="assessment_appointments")
    op.drop_index("ix_assessment_appointments_gym_id", table_name="assessment_appointments")
    op.drop_table("assessment_appointments")
