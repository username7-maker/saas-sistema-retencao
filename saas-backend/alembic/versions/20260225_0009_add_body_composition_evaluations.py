"""add body_composition_evaluations table

Revision ID: 20260225_0009
Revises: 20260222_0008
Create Date: 2026-02-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20260225_0009"
down_revision = "20260222_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "body_composition_evaluations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gym_id",
            UUID(as_uuid=True),
            sa.ForeignKey("gyms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "member_id",
            UUID(as_uuid=True),
            sa.ForeignKey("members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evaluation_date", sa.Date(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("body_fat_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("lean_mass_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("muscle_mass_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("body_water_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("visceral_fat_level", sa.Numeric(5, 1), nullable=True),
        sa.Column("bmi", sa.Numeric(5, 2), nullable=True),
        sa.Column("basal_metabolic_rate_kcal", sa.Numeric(8, 2), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="tezewa"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("report_file_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="bce_weight_positive"),
        sa.CheckConstraint(
            "body_fat_percent IS NULL OR (body_fat_percent >= 0 AND body_fat_percent <= 100)",
            name="bce_fat_range",
        ),
        sa.CheckConstraint(
            "body_water_percent IS NULL OR (body_water_percent >= 0 AND body_water_percent <= 100)",
            name="bce_water_range",
        ),
        sa.CheckConstraint("source IN ('tezewa', 'manual')", name="bce_source_valid"),
    )
    op.create_index(
        "ix_bce_gym_member_date",
        "body_composition_evaluations",
        ["gym_id", "member_id", "evaluation_date"],
    )
    op.create_index(
        "ix_bce_member_id",
        "body_composition_evaluations",
        ["member_id"],
    )
    op.create_index(
        "ix_bce_gym_id",
        "body_composition_evaluations",
        ["gym_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_bce_gym_id", table_name="body_composition_evaluations")
    op.drop_index("ix_bce_member_id", table_name="body_composition_evaluations")
    op.drop_index("ix_bce_gym_member_date", table_name="body_composition_evaluations")
    op.drop_table("body_composition_evaluations")
