"""extend body composition evaluations for premium report v1

Revision ID: 20260414_0030
Revises: 20260401_0029
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260414_0030"
down_revision = "20260401_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("body_composition_evaluations", sa.Column("measured_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("age_years", sa.Integer(), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("sex", sa.String(length=10), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("height_cm", sa.Numeric(6, 2), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("parsing_confidence", sa.Numeric(5, 4), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("data_quality_flags_json", JSONB(), nullable=True))
    op.add_column(
        "body_composition_evaluations",
        sa.Column("reviewer_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("body_composition_evaluations", sa.Column("import_batch_id", sa.String(length=120), nullable=True))

    op.create_check_constraint(
        "ck_body_composition_evaluations_bce_parsing_confidence_range",
        "body_composition_evaluations",
        "parsing_confidence IS NULL OR (parsing_confidence >= 0 AND parsing_confidence <= 1)",
    )

    op.execute(
        """
        UPDATE body_composition_evaluations
        SET
          measured_at = (evaluation_date::timestamp AT TIME ZONE 'UTC'),
          parsing_confidence = ocr_confidence
        WHERE evaluation_date IS NOT NULL
          AND (measured_at IS NULL OR parsing_confidence IS NULL)
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_body_composition_evaluations_bce_parsing_confidence_range",
        "body_composition_evaluations",
        type_="check",
    )
    for column_name in (
        "import_batch_id",
        "reviewer_user_id",
        "data_quality_flags_json",
        "parsing_confidence",
        "height_cm",
        "sex",
        "age_years",
        "measured_at",
    ):
        op.drop_column("body_composition_evaluations", column_name)
