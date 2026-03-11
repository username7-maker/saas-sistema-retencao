"""gym_id NOT NULL on nurturing_sequences, diagnosis_errors, objection_responses

Fixes tenant isolation gap: nullable gym_id allowed orphaned records
that could bypass multi-tenant filtering.

NOTE: downgrade restores nullable but cannot recover deleted orphaned rows.

Revision ID: 20260310_0017
Revises: 20260306_0016
Create Date: 2026-03-10
"""

import sqlalchemy as sa
from alembic import op

revision = "20260310_0017"
down_revision = "20260306_0016"
branch_labels = None
depends_on = None

_TABLES = ("nurturing_sequences", "diagnosis_errors", "objection_responses")


def upgrade() -> None:
    # Delete orphaned rows (gym_id IS NULL) before applying NOT NULL constraint.
    # These are records that lost their gym association and represent a data leak risk.
    for tbl_name in _TABLES:
        t = sa.table(tbl_name, sa.column("gym_id"))
        op.execute(sa.delete(t).where(t.c.gym_id.is_(None)))

    # Change ondelete from SET NULL to CASCADE and make gym_id NOT NULL.
    for table in _TABLES:
        # Drop existing FK constraint (naming convention: {table}_gym_id_fkey)
        op.drop_constraint(f"{table}_gym_id_fkey", table, type_="foreignkey")
        # Alter column to NOT NULL
        op.alter_column(
            table,
            "gym_id",
            existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        )
        # Recreate FK with CASCADE
        op.create_foreign_key(
            f"{table}_gym_id_fkey",
            table,
            "gyms",
            ["gym_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_constraint(f"{table}_gym_id_fkey", table, type_="foreignkey")
        op.alter_column(
            table,
            "gym_id",
            existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        )
        op.create_foreign_key(
            f"{table}_gym_id_fkey",
            table,
            "gyms",
            ["gym_id"],
            ["id"],
            ondelete="SET NULL",
        )
