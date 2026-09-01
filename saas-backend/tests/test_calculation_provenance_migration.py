from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _migration_module():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20260901_0059_calculation_provenance.py"
    spec = spec_from_file_location("calculation_provenance_migration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load calculation provenance migration.")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_calculation_provenance_migration_is_the_current_linear_revision():
    migration = _migration_module()

    assert migration.revision == "20260901_0059"
    assert migration.down_revision == "20260827_0058"
    assert set(migration._ORIGINS) == {
        "reported",
        "schofield_hw_1985",
        "mifflin_st_jeor_1990",
        "lee_2000",
        "poortmans_2005",
        "legacy_unknown",
        "unavailable",
    }


def test_migration_snapshot_formulas_match_new_pediatric_policy():
    migration = _migration_module()
    measurements = {
        "right_arm_relaxed_cm": 32,
        "right_thigh_cm": 55,
        "right_calf_cm": 38,
        "skinfold_triceps_mm": 10,
        "skinfold_thigh_mm": 15,
        "skinfold_calf_mm": 8,
    }

    bmr, bmr_origin = migration._bmr(sex="male", age=15, height_cm=170, weight_kg=60)
    poortmans, muscle_origin, alerts = migration._muscle(
        sex="male",
        age=15,
        height_cm=170,
        weight_kg=60,
        ethnicity="white",
        values=measurements,
    )
    blocked, blocked_origin, blocked_alerts = migration._muscle(
        sex="male",
        age=17,
        height_cm=170,
        weight_kg=60,
        ethnicity="white",
        values=measurements,
    )

    assert str(bmr) == "1723.74"
    assert bmr_origin == "schofield_hw_1985"
    assert poortmans is not None
    assert muscle_origin == "poortmans_2005"
    assert alerts == []
    assert blocked is None
    assert blocked_origin == "unavailable"
    assert "muscle_measurement_required" in blocked_alerts
