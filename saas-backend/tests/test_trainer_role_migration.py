from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _migration_module():
    migration_path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20260323_0023_add_trainer_role.py"
    spec = spec_from_file_location("trainer_role_migration", migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load trainer role migration module.")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_recreates_constraint_with_trainer():
    migration = _migration_module()

    with (
        patch.object(migration.op, "execute") as execute_sql,
        patch.object(migration, "_drop_role_check_constraints") as drop_constraints,
        patch.object(migration, "_create_role_check_constraint") as create_constraint,
    ):
        migration.upgrade()

    execute_sql.assert_called_once_with("UPDATE users SET role = UPPER(role) WHERE role IS NOT NULL")
    drop_constraints.assert_called_once_with()
    create_constraint.assert_called_once_with(
        "ck_users_role_enum",
        ("OWNER", "MANAGER", "SALESPERSON", "RECEPTIONIST", "TRAINER"),
    )


def test_downgrade_blocks_when_trainer_rows_exist():
    migration = _migration_module()
    bind = MagicMock()
    bind.execute.return_value.scalar.return_value = 1

    with (
        patch.object(migration.op, "get_bind", return_value=bind),
        patch.object(migration, "_drop_role_check_constraints") as drop_constraints,
        patch.object(migration, "_create_role_check_constraint") as create_constraint,
    ):
        with pytest.raises(RuntimeError, match="users.role contains 'TRAINER'"):
            migration.downgrade()

    drop_constraints.assert_not_called()
    create_constraint.assert_not_called()


def test_drop_role_constraints_uses_raw_sql_block():
    migration = _migration_module()

    with patch.object(migration.op, "execute") as execute_sql:
        migration._drop_role_check_constraints()

    execute_sql.assert_called_once()
    sql = execute_sql.call_args.args[0]
    assert "ALTER TABLE users DROP CONSTRAINT IF EXISTS %I" in sql
    assert "pg_get_constraintdef(c.oid) ILIKE '%role%'" in sql
