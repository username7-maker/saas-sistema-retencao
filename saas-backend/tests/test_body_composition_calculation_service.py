from decimal import Decimal
from math import pi
from types import SimpleNamespace

import pytest

from app.services.body_composition_calculation_service import (
    calculate_basal_metabolic_rate,
    calculate_muscle_mass,
)
from app.services.body_composition_report_service import resolve_body_composition_persistence_fields


@pytest.mark.parametrize(
    ("sex", "age", "height", "weight", "expected", "origin"),
    [
        ("male", 9, 140, 35, 1282.97, "schofield_hw_1985"),
        ("female", 9, 140, 35, 1191.64, "schofield_hw_1985"),
        ("male", 10, 145, 40, 1364.44, "schofield_hw_1985"),
        ("female", 10, 145, 40, 1208.85, "schofield_hw_1985"),
        ("male", 18, 175, 70, 1893.10, "schofield_hw_1985"),
        ("female", 18, 165, 60, 1469.15, "schofield_hw_1985"),
        ("male", 19, 175, 70, 1703.75, "mifflin_st_jeor_1990"),
        ("female", 19, 165, 60, 1375.25, "mifflin_st_jeor_1990"),
    ],
)
def test_bmr_age_sex_boundaries(sex, age, height, weight, expected, origin):
    result = calculate_basal_metabolic_rate(sex=sex, age_years=age, height_cm=height, weight_kg=weight)

    assert result.value == Decimal(str(expected)).quantize(Decimal("0.01"))
    assert result.origin == origin
    assert result.formula_version is not None


def test_bmr_below_supported_age_is_unavailable():
    result = calculate_basal_metabolic_rate(sex="female", age_years=2, height_cm=90, weight_kg=13)

    assert result.value is None
    assert result.origin == "unavailable"
    assert "bmr_age_outside_supported_range" in result.alerts


def _muscle_measurements():
    return {
        "right_arm_relaxed_cm": 32,
        "right_thigh_cm": 55,
        "right_calf_cm": 38,
        "skinfold_triceps_mm": 10,
        "skinfold_thigh_mm": 15,
        "skinfold_calf_mm": 8,
    }


def test_poortmans_white_child_uses_all_corrected_measurements():
    result = calculate_muscle_mass(
        sex="male",
        age_years=15,
        height_cm=170,
        weight_kg=60,
        ethnicity="white",
        measurements=_muscle_measurements(),
    )
    arm = 32 - pi
    thigh = 55 - pi * 1.5
    calf = 38 - pi * 0.8
    expected = 1.7 * (0.0064 * arm**2 + 0.0032 * thigh**2 + 0.0015 * calf**2) + 2.56 + 0.136 * 15

    assert result.origin == "poortmans_2005"
    assert float(result.value) == pytest.approx(round(expected, 2))


@pytest.mark.parametrize(
    ("age", "ethnicity", "alert"),
    [
        (6, "white", "muscle_age_outside_validated_range"),
        (17, "white", "muscle_age_outside_validated_range"),
        (12, "black", "poortmans_population_not_validated"),
        (12, "asian", "poortmans_population_not_validated"),
    ],
)
def test_children_outside_poortmans_population_require_measurement(age, ethnicity, alert):
    result = calculate_muscle_mass(
        sex="female",
        age_years=age,
        height_cm=155,
        weight_kg=48,
        ethnicity=ethnicity,
        measurements=_muscle_measurements(),
    )

    assert result.value is None
    assert result.origin == "unavailable"
    assert "muscle_measurement_required" in result.alerts
    assert alert in result.alerts


def test_adult_lee_requires_all_six_measurements_and_keeps_bmi_warning():
    complete = calculate_muscle_mass(
        sex="male",
        age_years=30,
        height_cm=170,
        weight_kg=100,
        ethnicity="black",
        measurements=_muscle_measurements(),
    )
    incomplete_measurements = _muscle_measurements()
    incomplete_measurements.pop("skinfold_calf_mm")
    incomplete = calculate_muscle_mass(
        sex="male",
        age_years=30,
        height_cm=170,
        weight_kg=100,
        ethnicity="black",
        measurements=incomplete_measurements,
    )

    assert complete.origin == "lee_2000"
    assert complete.value is not None
    assert "lee_bmi_extrapolation" in complete.alerts
    assert incomplete.value is None
    assert "muscle_measurements_incomplete" in incomplete.alerts


def test_reported_device_values_have_absolute_precedence_on_reprocessing():
    existing = SimpleNamespace(
        basal_metabolic_rate_kcal=1777,
        basal_metabolic_rate_origin="reported",
        muscle_mass_kg=39.8,
        muscle_mass_origin="reported",
        sex="male",
        age_years=30,
        height_cm=175,
        weight_kg=80,
        anthropometry_ethnicity="white",
        **_muscle_measurements(),
    )
    resolved = resolve_body_composition_persistence_fields(
        {"sex": "male", "age_years": 30, "height_cm": 175, "weight_kg": 95},
        existing_evaluation=existing,
        explicit_fields={"weight_kg"},
    )

    assert resolved["basal_metabolic_rate_kcal"] == 1777
    assert resolved["basal_metabolic_rate_origin"] == "reported"
    assert resolved["muscle_mass_kg"] == 39.8
    assert resolved["muscle_mass_origin"] == "reported"


def test_explicit_manual_change_replaces_reported_value_and_remains_reported():
    existing = SimpleNamespace(
        basal_metabolic_rate_kcal=1777,
        basal_metabolic_rate_origin="reported",
        muscle_mass_kg=None,
        muscle_mass_origin="unavailable",
    )
    resolved = resolve_body_composition_persistence_fields(
        {
            "sex": "male",
            "age_years": 30,
            "height_cm": 175,
            "weight_kg": 80,
            "basal_metabolic_rate_kcal": 1801,
        },
        existing_evaluation=existing,
        explicit_fields={"sex", "age_years", "height_cm", "weight_kg", "basal_metabolic_rate_kcal"},
    )

    assert resolved["basal_metabolic_rate_kcal"] == 1801
    assert resolved["basal_metabolic_rate_origin"] == "reported"


def test_new_reported_values_win_even_when_fallback_inputs_are_complete():
    resolved = resolve_body_composition_persistence_fields(
        {
            "sex": "male",
            "age_years": 30,
            "height_cm": 175,
            "weight_kg": 80,
            "anthropometry_ethnicity": "white",
            "basal_metabolic_rate_kcal": 1900,
            "muscle_mass_kg": 42.5,
            **_muscle_measurements(),
        }
    )

    assert resolved["basal_metabolic_rate_kcal"] == 1900
    assert resolved["basal_metabolic_rate_origin"] == "reported"
    assert resolved["muscle_mass_kg"] == 42.5
    assert resolved["muscle_mass_origin"] == "reported"


def test_bioimpedance_fallback_uses_schofield_and_poortmans_only_when_eligible():
    eligible = resolve_body_composition_persistence_fields(
        {
            "sex": "female",
            "age_years": 12,
            "height_cm": 155,
            "weight_kg": 48,
            "anthropometry_ethnicity": "white",
            **_muscle_measurements(),
        }
    )
    age_17 = resolve_body_composition_persistence_fields(
        {
            "sex": "female",
            "age_years": 17,
            "height_cm": 165,
            "weight_kg": 58,
            "anthropometry_ethnicity": "white",
            **_muscle_measurements(),
        }
    )

    assert eligible["basal_metabolic_rate_origin"] == "schofield_hw_1985"
    assert eligible["muscle_mass_origin"] == "poortmans_2005"
    assert eligible["muscle_mass_kg"] is not None
    assert age_17["basal_metabolic_rate_origin"] == "schofield_hw_1985"
    assert age_17["muscle_mass_origin"] == "unavailable"
    assert age_17["muscle_mass_kg"] is None


def test_previously_calculated_value_can_be_recalculated_when_inputs_change():
    existing = SimpleNamespace(
        basal_metabolic_rate_kcal=1700,
        basal_metabolic_rate_origin="mifflin_st_jeor_1990",
        muscle_mass_kg=None,
        muscle_mass_origin="unavailable",
        sex="male",
        age_years=30,
        height_cm=175,
        weight_kg=70,
    )
    resolved = resolve_body_composition_persistence_fields(
        {"weight_kg": 80},
        existing_evaluation=existing,
        explicit_fields={"weight_kg"},
    )

    assert resolved["basal_metabolic_rate_kcal"] == Decimal("1748.75")
    assert resolved["basal_metabolic_rate_origin"] == "mifflin_st_jeor_1990"
