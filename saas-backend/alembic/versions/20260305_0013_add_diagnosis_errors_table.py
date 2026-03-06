"""add diagnosis_errors table

Revision ID: 20260305_0013
Revises: 20260305_0012
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "20260305_0013"
down_revision = "20260305_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnosis_errors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("gym_id", UUID(as_uuid=True), sa.ForeignKey("gyms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("prospect_email", sa.String(length=255), nullable=False),
        sa.Column("prospect_name", sa.String(length=120), nullable=True),
        sa.Column("endpoint", sa.String(length=80), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("traceback_snippet", sa.Text(), nullable=True),
        sa.Column("payload", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_diagnosis_errors_gym_id", "diagnosis_errors", ["gym_id"])
    op.create_index("ix_diagnosis_errors_prospect_email", "diagnosis_errors", ["prospect_email"])
    op.create_index(
        "ix_diagnosis_errors_gym_created",
        "diagnosis_errors",
        ["gym_id", "created_at"],
    )
    op.create_index(
        "ix_diagnosis_errors_email_created",
        "diagnosis_errors",
        ["prospect_email", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_diagnosis_errors_email_created", table_name="diagnosis_errors")
    op.drop_index("ix_diagnosis_errors_gym_created", table_name="diagnosis_errors")
    op.drop_index("ix_diagnosis_errors_prospect_email", table_name="diagnosis_errors")
    op.drop_index("ix_diagnosis_errors_gym_id", table_name="diagnosis_errors")
    op.drop_table("diagnosis_errors")
