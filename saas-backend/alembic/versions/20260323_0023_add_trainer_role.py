"""Add trainer role support for users

Revision ID: 20260323_0023
Revises: 20260323_0022
Create Date: 2026-03-23 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_0023"
down_revision = "20260323_0022"
branch_labels = None
depends_on = None


_ROLE_VALUES_UPGRADE = ("OWNER", "MANAGER", "SALESPERSON", "RECEPTIONIST", "TRAINER")
_ROLE_VALUES_DOWNGRADE = ("OWNER", "MANAGER", "SALESPERSON", "RECEPTIONIST")


def _drop_role_check_constraints() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT c.conname
            FROM pg_constraint AS c
            JOIN pg_class AS t ON t.oid = c.conrelid
            JOIN pg_namespace AS n ON n.oid = t.relnamespace
            WHERE t.relname = 'users'
              AND n.nspname = current_schema()
              AND c.contype = 'c'
              AND pg_get_constraintdef(c.oid) ILIKE '%role%'
            """
        )
    )
    for constraint_name in rows.scalars():
        op.drop_constraint(constraint_name, "users", type_="check")


def _create_role_check_constraint(name: str, values: tuple[str, ...]) -> None:
    allowed = ", ".join(f"'{value}'" for value in values)
    op.create_check_constraint(name, "users", f"role IN ({allowed})")


def upgrade() -> None:
    op.execute("UPDATE users SET role = UPPER(role) WHERE role IS NOT NULL")
    _drop_role_check_constraints()
    _create_role_check_constraint("ck_users_role_enum", _ROLE_VALUES_UPGRADE)


def downgrade() -> None:
    bind = op.get_bind()
    trainer_exists = bind.execute(sa.text("SELECT 1 FROM users WHERE UPPER(role) = 'TRAINER' LIMIT 1")).scalar()
    if trainer_exists:
        raise RuntimeError("Cannot downgrade while users.role contains 'TRAINER'.")

    op.execute("UPDATE users SET role = UPPER(role) WHERE role IS NOT NULL")
    _drop_role_check_constraints()
    _create_role_check_constraint("ck_users_role_enum", _ROLE_VALUES_DOWNGRADE)
