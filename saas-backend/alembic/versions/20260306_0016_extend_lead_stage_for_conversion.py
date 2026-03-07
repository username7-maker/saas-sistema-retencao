"""extend lead stage for conversion

Revision ID: 20260306_0016
Revises: 20260306_0015
Create Date: 2026-03-06
"""

import sqlalchemy as sa
from alembic import op


revision = "20260306_0016"
down_revision = "20260306_0015"
branch_labels = None
depends_on = None


OLD_LEAD_STAGE = sa.Enum(
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

NEW_LEAD_STAGE = sa.Enum(
    "new",
    "contact",
    "visit",
    "trial",
    "proposal",
    "meeting_scheduled",
    "proposal_sent",
    "won",
    "lost",
    name="lead_stage_enum",
    native_enum=False,
)


def upgrade() -> None:
    op.alter_column(
        "leads",
        "stage",
        existing_type=OLD_LEAD_STAGE,
        type_=NEW_LEAD_STAGE,
        existing_nullable=False,
        existing_server_default=sa.text("'new'"),
    )


def downgrade() -> None:
    op.execute("UPDATE leads SET stage = 'proposal' WHERE stage IN ('meeting_scheduled', 'proposal_sent')")
    op.alter_column(
        "leads",
        "stage",
        existing_type=NEW_LEAD_STAGE,
        type_=OLD_LEAD_STAGE,
        existing_nullable=False,
        existing_server_default=sa.text("'new'"),
    )
