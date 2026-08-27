from datetime import UTC, datetime
from math import pi
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.assessment_anthropometry_report_service import build_anthropometric_report_payload
from app.services.assessment_anthropometry_service import preview_anthropometric_assessment
from app.services.premium_report_service import render_premium_report_html


def measurement(value: float, unit: str, side: str = "right") -> dict:
    return {"attempts": [value, value], "unit": unit, "side": side}


def slaughter_payload(*, calculate_muscle_mass: bool = True, ethnicity: str = "black") -> dict:
    measurements = {
        "height_cm": measurement(170, "cm", "not_applicable"),
        "weight_kg": measurement(60, "kg", "not_applicable"),
        "skinfold_triceps_mm": measurement(10, "mm"),
        "skinfold_subscapular_mm": measurement(12, "mm"),
    }
    if calculate_muscle_mass:
        measurements.update(
            {
                "right_arm_relaxed_cm": measurement(32, "cm"),
                "right_thigh_cm": measurement(55, "cm"),
                "right_calf_cm": measurement(38, "cm"),
                "skinfold_thigh_mm": measurement(15, "mm"),
                "skinfold_calf_mm": measurement(8, "mm"),
            }
        )
    return {
        "sex_for_formula": "male",
        "age_years": 15,
        "measurement_protocol": "slaughter_1988_boys_black_white_6_17",
        "anthropometry_ethnicity": ethnicity,
        "anthropometry_maturity": "prepubertal",
        "calculate_muscle_mass": calculate_muscle_mass,
        "measurements": measurements,
    }


def test_slaughter_choices_muscle_mass_and_juvenile_bmr_are_calculated():
    preview = preview_anthropometric_assessment(slaughter_payload())

    assert float(preview["results"]["body_fat_pct"]) == pytest.approx(19.55)
    assert float(preview["results"]["basal_metabolic_rate"]) == pytest.approx(1592.5)
    assert preview["results"]["muscle_mass_kg"] is not None
    assert "lee_age_extrapolation" in preview["snapshot"]["flags"]
    assert preview["snapshot"]["inputs"]["anthropometry_ethnicity"] == "black"
    assert preview["snapshot"]["inputs"]["anthropometry_maturity"] == "prepubertal"
    assert preview["snapshot"]["muscle_mass_calculation"]["measurement_side"] == "right"
    assert float(preview["snapshot"]["muscle_mass_calculation"]["corrected_circumferences_cm"]["arm"]) == pytest.approx(
        32 - pi,
        abs=0.01,
    )
    assert "0.00744*CAG^2" in preview["snapshot"]["muscle_mass_calculation"]["formula"]


@pytest.mark.parametrize(
    ("ethnicity", "coefficient"),
    [("white", 0.0), ("black", 1.1), ("asian", -2.0)],
)
def test_lee_uses_published_ethnicity_coefficients(ethnicity: str, coefficient: float):
    payload = slaughter_payload(ethnicity=ethnicity)
    payload["age_years"] = 30
    payload["measurement_protocol"] = "jackson_pollock_3_male_18_61"
    payload["measurements"].update(
        {
            "skinfold_chest_mm": measurement(10, "mm"),
            "skinfold_abdominal_mm": measurement(18, "mm"),
            "skinfold_thigh_mm": measurement(15, "mm"),
        }
    )
    payload["measurements"]["height_cm"] = measurement(180, "cm", "not_applicable")
    payload["measurements"]["weight_kg"] = measurement(80, "kg", "not_applicable")
    preview = preview_anthropometric_assessment(payload)

    arm = 32 - pi * 1.0
    thigh = 55 - pi * 1.5
    calf = 38 - pi * 0.8
    expected = 1.8 * (0.00744 * arm**2 + 0.00088 * thigh**2 + 0.00441 * calf**2) + 2.4 - 0.048 * 30 + coefficient + 7.8
    assert float(preview["results"]["muscle_mass_kg"]) == pytest.approx(round(expected, 2))


def test_muscle_mass_remains_unavailable_when_not_selected():
    preview = preview_anthropometric_assessment(slaughter_payload(calculate_muscle_mass=False))

    assert preview["results"]["muscle_mass_kg"] is None
    assert preview["indicator_origins"]["muscle_mass_kg"] == "unavailable"
    assert preview["snapshot"]["muscle_mass_calculation"]["enabled"] is False
    assert "muscle_mass_kg" in preview["snapshot"]["unavailable_metrics"]


def test_lee_female_uses_zero_sex_coefficient():
    payload = slaughter_payload(ethnicity="white")
    payload["sex_for_formula"] = "female"
    payload["age_years"] = 30
    payload["measurement_protocol"] = "jackson_pollock_3_female_18_55"
    payload["measurements"].update(
        {
            "skinfold_suprailiac_mm": measurement(12, "mm"),
            "skinfold_thigh_mm": measurement(15, "mm"),
        }
    )
    preview = preview_anthropometric_assessment(payload)

    arm = 32 - pi * 1.0
    thigh = 55 - pi * 1.5
    calf = 38 - pi * 0.8
    expected = 1.7 * (0.00744 * arm**2 + 0.00088 * thigh**2 + 0.00441 * calf**2) - 0.048 * 30 + 7.8
    assert float(preview["results"]["muscle_mass_kg"]) == pytest.approx(round(expected, 2))
    assert preview["snapshot"]["muscle_mass_calculation"]["sex_coefficient"] == "0"


@pytest.mark.parametrize("missing_field", ["anthropometry_ethnicity", "anthropometry_maturity"])
def test_slaughter_rejects_missing_population_choices(missing_field: str):
    payload = slaughter_payload(calculate_muscle_mass=False)
    payload[missing_field] = None

    with pytest.raises(HTTPException) as exc_info:
        preview_anthropometric_assessment(payload)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "anthropometry_choice_invalid"
    assert exc_info.value.detail["field"] == missing_field


def test_slaughter_black_prepubertal_uses_3_2_intercept():
    preview = preview_anthropometric_assessment(slaughter_payload(calculate_muscle_mass=False))

    expected = 1.21 * 22 - 0.008 * 22**2 - 3.2
    assert float(preview["results"]["body_fat_pct"]) == pytest.approx(round(expected, 2))


@pytest.mark.parametrize(
    ("ethnicity", "maturity", "intercept"),
    [
        ("white", "prepubertal", 1.7),
        ("white", "pubertal", 3.4),
        ("white", "postpubertal", 5.5),
        ("black", "prepubertal", 3.2),
        ("black", "pubertal", 5.2),
        ("black", "postpubertal", 6.8),
    ],
)
def test_slaughter_supports_all_male_population_branches(ethnicity: str, maturity: str, intercept: float):
    payload = slaughter_payload(calculate_muscle_mass=False, ethnicity=ethnicity)
    payload["anthropometry_maturity"] = maturity
    preview = preview_anthropometric_assessment(payload)

    expected = 1.21 * 22 - 0.008 * 22**2 - intercept
    assert float(preview["results"]["body_fat_pct"]) == pytest.approx(round(expected, 2))


def test_slaughter_uses_linear_branch_above_35_mm():
    payload = slaughter_payload(calculate_muscle_mass=False)
    payload["measurements"]["skinfold_triceps_mm"] = measurement(20, "mm")
    payload["measurements"]["skinfold_subscapular_mm"] = measurement(20, "mm")
    preview = preview_anthropometric_assessment(payload)

    assert float(preview["results"]["body_fat_pct"]) == pytest.approx(round(0.783 * 40 + 1.6, 2))


def test_lee_marks_obesity_extrapolation():
    payload = slaughter_payload()
    payload["measurements"]["weight_kg"] = measurement(100, "kg", "not_applicable")
    preview = preview_anthropometric_assessment(payload, member=SimpleNamespace(birthdate=None, height_cm=None))

    assert "lee_bmi_extrapolation" in preview["snapshot"]["flags"]


def test_premium_report_contains_lee_muscle_mass_bmr_source_and_warning():
    assessment = SimpleNamespace(
        id=uuid4(),
        assessment_date=datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
        created_at=datetime(2026, 8, 27, 12, 0, tzinfo=UTC),
        measurement_protocol="slaughter_1988_boys_black_white_6_17",
        formula_version="anthropometry-v2:slaughter:lee-2000-complete-v1",
        assessment_method="manual_anthropometry",
        record_origin="cordex",
        sex_used_for_formula="male",
        age_used_for_formula=15,
        height_cm=170,
        weight_kg=60,
        bmi=20.76,
        body_fat_pct=19.55,
        fat_mass_kg=11.73,
        lean_mass_kg=48.27,
        muscle_mass_kg=31.42,
        waist_hip_ratio=None,
        basal_metabolic_rate=1592.5,
        observations=None,
        anthropometry_snapshot_json={"flags": ["lee_age_extrapolation"], "measurements": {}},
        extra_data={},
    )
    member = SimpleNamespace(
        full_name="Aluno Slaughter", gym=SimpleNamespace(name="Academia Teste"), assigned_user=None
    )

    payload = build_anthropometric_report_payload(member, assessment)
    report = payload.parameters["report"]
    metrics = [
        metric
        for section in ("primary_cards", "composition_metrics", "muscle_fat_metrics")
        for metric in report[section]
    ]
    muscle_metric = next(metric for metric in metrics if metric["key"] == "muscle_mass_kg")
    bmr_metric = next(metric for metric in metrics if metric["key"] == "basal_metabolic_rate_kcal")
    html = render_premium_report_html(payload)

    assert muscle_metric["label"] == "Massa muscular esqueletica estimada - Lee et al. (2000)"
    assert muscle_metric["source_label"] == "Calculado por antropometria - Lee et al. (2000)"
    assert bmr_metric["label"] == "TMB estimada"
    assert bmr_metric["unit"] == "kcal/dia"
    assert payload.parameters["muscle_mass_extrapolation_flags"] == ["lee_age_extrapolation"]
    assert "Lee et al. (2000)" in html
    assert "massa livre de gordura e massa magra" in html

    assessment.muscle_mass_kg = None
    assessment.anthropometry_snapshot_json = {"flags": [], "measurements": {}}
    without_muscle = build_anthropometric_report_payload(member, assessment)
    without_muscle_report = without_muscle.parameters["report"]
    without_muscle_metrics = [
        metric
        for section in ("primary_cards", "composition_metrics", "muscle_fat_metrics")
        for metric in without_muscle_report[section]
    ]

    assert all(metric["key"] != "muscle_mass_kg" for metric in without_muscle_metrics)
    assert without_muscle.parameters["muscle_mass_formula"] is None
    assert "Massa muscular nao foi calculada" in without_muscle.parameters["methodological_note"]
