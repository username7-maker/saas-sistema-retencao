from app.services.assessment_anthropometry_service import preview_anthropometric_assessment
from app.services.body_composition_protocols import protocol_catalog

_VALUES = {
    "height_cm": (170, "cm"),
    "weight_kg": (65, "kg"),
    "neck_cm": (36, "cm"),
    "waist_cm": (78, "cm"),
    "hip_cm": (94, "cm"),
    "abdomen_cm": (82, "cm"),
    "shoulders_cm": (100, "cm"),
    "chest_cm": (92, "cm"),
    "arm_cm": (30, "cm"),
    "right_arm_relaxed_cm": (30, "cm"),
    "right_thigh_cm": (52, "cm"),
    "right_calf_cm": (36, "cm"),
    "skinfold_chest_mm": (12, "mm"),
    "skinfold_midaxillary_mm": (12, "mm"),
    "skinfold_subscapular_mm": (12, "mm"),
    "skinfold_triceps_mm": (12, "mm"),
    "skinfold_biceps_mm": (8, "mm"),
    "skinfold_abdominal_mm": (16, "mm"),
    "skinfold_suprailiac_mm": (12, "mm"),
    "skinfold_thigh_mm": (16, "mm"),
    "skinfold_calf_mm": (12, "mm"),
}
_MUSCLE_FIELDS = {
    "right_arm_relaxed_cm",
    "right_thigh_cm",
    "right_calf_cm",
    "skinfold_triceps_mm",
    "skinfold_thigh_mm",
    "skinfold_calf_mm",
}


def _measurement(field: str) -> dict:
    value, unit = _VALUES.get(field, (12, "mm"))
    return {
        "attempts": [value, value],
        "unit": unit,
        "side": "not_applicable" if field in {"height_cm", "weight_kg"} else "right",
    }


def _reference_age(protocol: dict) -> int:
    minimum = protocol.get("age_min")
    maximum = protocol.get("age_max")
    if minimum is not None and maximum is not None and minimum <= 12 <= maximum:
        return 12
    if minimum is not None and minimum >= 18:
        upper = maximum or 30
        return 19 if upper >= 19 else upper
    if minimum is not None:
        return minimum
    return 30


def test_all_32_supported_protocols_produce_body_fat_bmr_and_policy_compliant_muscle_mass():
    supported = [protocol for protocol in protocol_catalog() if protocol.get("supported")]

    assert len(supported) == 32
    for protocol in supported:
        age = _reference_age(protocol)
        fields = {"height_cm", "weight_kg", *protocol.get("required_fields", []), *_MUSCLE_FIELDS}
        preview = preview_anthropometric_assessment(
            {
                "sex_for_formula": protocol.get("sex") or "male",
                "age_years": age,
                "measurement_protocol": protocol["key"],
                "anthropometry_ethnicity": "white",
                "anthropometry_maturity": "pubertal",
                "calculate_muscle_mass": True,
                "measurements": {field: _measurement(field) for field in fields},
            }
        )

        assert preview["results"]["body_fat_pct"] is not None, protocol["key"]
        assert preview["results"]["basal_metabolic_rate"] is not None, protocol["key"]
        assert preview["basal_metabolic_rate_origin"] == (
            "schofield_hw_1985" if age <= 18 else "mifflin_st_jeor_1990"
        ), protocol["key"]
        if 7 <= age <= 16:
            assert preview["muscle_mass_origin"] == "poortmans_2005", protocol["key"]
            assert preview["results"]["muscle_mass_kg"] is not None, protocol["key"]
        elif age >= 18:
            assert preview["muscle_mass_origin"] == "lee_2000", protocol["key"]
            assert preview["results"]["muscle_mass_kg"] is not None, protocol["key"]
        else:
            assert preview["muscle_mass_origin"] == "unavailable", protocol["key"]
