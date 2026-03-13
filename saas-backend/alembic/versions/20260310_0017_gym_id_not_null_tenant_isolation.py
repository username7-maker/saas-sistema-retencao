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


def _drop_gym_fk_constraint(table_name: str) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_class r ON r.oid = c.confrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY (c.conkey)
            WHERE c.contype = 'f'
              AND t.relname = :table_name
              AND r.relname = 'gyms'
              AND a.attname = 'gym_id'
            """
        ),
        {"table_name": table_name},
    ).fetchall()
    for (constraint_name,) in rows:
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")


def upgrade() -> None:
    # Delete orphaned rows (gym_id IS NULL) before applying NOT NULL constraint.
    # These are records that lost their gym association and represent a data leak risk.
    for tbl_name in _TABLES:
        t = sa.table(tbl_name, sa.column("gym_id"))
        op.execute(sa.delete(t).where(t.c.gym_id.is_(None)))

    # Change ondelete from SET NULL to CASCADE and make gym_id NOT NULL.
    for table in _TABLES:
        _drop_gym_fk_constraint(table)
        # Alter column to NOT NULL
        op.alter_column(
            table,
            "gym_id",
            existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        )
        # Recreate FK with CASCADE
        op.create_foreign_key(
            f"fk_{table}_gym_id_gyms",
            table,
            "gyms",
            ["gym_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    for table in _TABLES:
        _drop_gym_fk_constraint(table)
        op.alter_column(
            table,
            "gym_id",
            existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        )
        op.create_foreign_key(
            f"fk_{table}_gym_id_gyms",
            table,
            "gyms",
            ["gym_id"],
            ["id"],
            ondelete="SET NULL",
        )
