"""add trainer role

Revision ID: 20260424_0020
Revises: 20260313_0019
Create Date: 2026-04-24 00:00:00.000000
"""

from alembic import op


revision = "20260424_0020"
down_revision = "20260313_0019"
branch_labels = None
depends_on = None


ROLE_VALUES = "'owner', 'manager', 'salesperson', 'receptionist', 'trainer'"
DOWN_ROLE_VALUES = "'owner', 'manager', 'salesperson', 'receptionist'"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        f"""
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            FOR constraint_name IN
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'users'::regclass
                  AND contype = 'c'
                  AND pg_get_constraintdef(oid) LIKE '%role%'
            LOOP
                EXECUTE format('ALTER TABLE users DROP CONSTRAINT IF EXISTS %I', constraint_name);
            END LOOP;

            ALTER TABLE users
                ADD CONSTRAINT ck_users_role_enum
                CHECK (role IN ({ROLE_VALUES}));
        END $$;
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("UPDATE users SET role = 'receptionist' WHERE role = 'trainer'")
    op.execute(
        f"""
        DO $$
        BEGIN
            ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role_enum;
            ALTER TABLE users
                ADD CONSTRAINT ck_users_role_enum
                CHECK (role IN ({DOWN_ROLE_VALUES}));
        END $$;
        """
    )
