from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch


def _migration_module():
    migration_path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20260323_0022_actuar_sync_v2.py"
    spec = spec_from_file_location("actuar_sync_v2_migration", migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load actuar sync v2 migration module.")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_downgrade_remaps_new_statuses_before_recreating_legacy_constraint():
    migration = _migration_module()

    with (
        patch.object(migration.op, "drop_constraint") as drop_constraint,
        patch.object(migration, "_drop_actuar_sync_status_constraints") as drop_status_constraints,
        patch.object(migration.op, "execute") as execute_sql,
        patch.object(migration.op, "create_check_constraint") as create_constraint,
        patch.object(migration.op, "alter_column"),
        patch.object(migration.op, "drop_column"),
        patch.object(migration.op, "drop_index"),
        patch.object(migration.op, "drop_table"),
    ):
        migration.downgrade()

    drop_constraint.assert_called_once_with(migration._ACTUAR_SYNC_JOB_FK, "body_composition_evaluations", type_="foreignkey")
    drop_status_constraints.assert_called_once_with()
    remap_calls = [
        call.args[0]
        for call in execute_sql.call_args_list
        if call.args and "UPDATE body_composition_evaluations" in call.args[0]
    ]
    assert remap_calls, "Expected downgrade to remap v2 statuses back to legacy statuses."
    remap_sql = remap_calls[0]
    assert "WHEN 'sync_pending' THEN 'pending'" in remap_sql
    assert "WHEN 'synced_to_actuar' THEN 'synced'" in remap_sql
    assert "WHEN 'manual_sync_required' THEN 'skipped'" in remap_sql
    create_constraint.assert_called_once_with(
        "ck_body_composition_evaluations_bce_actuar_sync_status_valid",
        "body_composition_evaluations",
        "actuar_sync_status IN ('disabled', 'pending', 'exported', 'synced', 'failed', 'skipped')",
    )
