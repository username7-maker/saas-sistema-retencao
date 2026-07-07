from app.services.body_composition_anthropometry_service import (
    calculate_anthropometric_body_fat,
    resolve_body_fat_fields,
)


def test_male_navy_uses_abdomen_before_waist() -> None:
    result = calculate_anthropometric_body_fat(
        {
            "sex": "male",
            "height_cm": 180,
            "weight_kg": 82,
            "neck_cm": 40,
            "waist_cm": 78,
            "abdomen_cm": 90,
        }
    )

    assert result["navy_percent"] is not None
    assert result["body_fat_percent"] == result["navy_percent"]
    assert result["method"] in {"geneos_composite", "navy_circumference"}


def test_female_navy_does_not_replace_missing_waist_with_abdomen() -> None:
    result = calculate_anthropometric_body_fat(
        {
            "sex": "female",
            "height_cm": 165,
            "weight_kg": 65,
            "neck_cm": 34,
            "abdomen_cm": 82,
            "hip_cm": 98,
        }
    )

    assert result["navy_percent"] is None
    assert "anthropometry_incomplete" in result["flags"]


def test_inconsistent_geneos_does_not_become_official_without_review() -> None:
    resolved = resolve_body_fat_fields(
        {
            "sex": "male",
            "height_cm": 180,
            "weight_kg": 82,
            "neck_cm": 36,
            "waist_cm": 60,
            "abdomen_cm": 130,
            "body_fat_percent": 24,
            "preferred_body_fat_source": "geneos_composite",
        }
    )

    assert resolved["body_fat_used_source"] == "bioimpedance"
    assert resolved["body_fat_used_percent"] == 24
    assert resolved["body_fat_manual_review_required"] is True
    assert "anthropometry_inconsistent" in resolved["data_quality_flags_json"]


def test_reviewed_geneos_can_be_used_as_official_source() -> None:
    resolved = resolve_body_fat_fields(
        {
            "sex": "male",
            "height_cm": 180,
            "weight_kg": 82,
            "neck_cm": 39,
            "waist_cm": 86,
            "abdomen_cm": 88,
            "body_fat_percent": 25,
            "preferred_body_fat_source": "geneos_composite",
            "body_fat_manual_review_completed": True,
        }
    )

    assert resolved["body_fat_used_source"] == "anthropometry"
    assert resolved["body_fat_used_percent"] == resolved["body_fat_anthropometric_percent"]
    assert resolved["fat_mass_estimated_kg"] is not None
    assert resolved["lean_mass_estimated_kg"] is not None


def test_manual_override_is_explicit_measurement_source() -> None:
    resolved = resolve_body_fat_fields(
        {
            "sex": "male",
            "height_cm": 180,
            "weight_kg": 82,
            "body_fat_percent": 25,
            "body_fat_manual_override_percent": 21.5,
            "preferred_body_fat_source": "manual_override",
        }
    )

    assert resolved["body_fat_used_percent"] == 21.5
    assert resolved["body_fat_used_source"] == "manual_override"
    assert resolved["body_fat_method"] == "manual_override"
    assert resolved["measurement_source"] == "manual_override"
    assert resolved["measurement_protocol"] == "manual_override"


def test_supported_skinfold_protocol_becomes_official_anthropometry() -> None:
    resolved = resolve_body_fat_fields(
        {
            "sex": "male",
            "age_years": 31,
            "height_cm": 180,
            "weight_kg": 82,
            "body_fat_percent": 28,
            "preferred_body_fat_source": "geneos_composite",
            "measurement_protocol": "jackson_pollock_3_male_18_61",
            "skinfold_chest_mm": 12,
            "skinfold_abdominal_mm": 22,
            "skinfold_thigh_mm": 18,
        }
    )

    assert resolved["body_fat_used_source"] == "anthropometry"
    assert resolved["body_fat_method"] == "skinfold_protocol"
    assert resolved["body_fat_used_percent"] == resolved["body_fat_anthropometric_percent"]
    assert resolved["fat_mass_estimated_kg"] is not None


def test_petroski_male_protocol_matches_actuar_reference_case() -> None:
    resolved = resolve_body_fat_fields(
        {
            "sex": "male",
            "age_years": 22,
            "height_cm": 177,
            "weight_kg": 73.6,
            "body_fat_percent": 31.2,
            "preferred_body_fat_source": "geneos_composite",
            "measurement_protocol": "petroski_1995_male_18_66",
            "skinfold_triceps_mm": 9,
            "skinfold_subscapular_mm": 12,
            "skinfold_suprailiac_mm": 7,
            "skinfold_calf_mm": 10,
        }
    )

    assert resolved["body_fat_used_source"] == "anthropometry"
    assert resolved["body_fat_method"] == "skinfold_protocol"
    assert resolved["body_fat_used_percent"] == 12.49
    assert resolved["fat_mass_estimated_kg"] == 9.19
    assert resolved["lean_mass_estimated_kg"] == 64.41


def test_expanded_supported_protocols_match_reference_formulas() -> None:
    cases = [
        (
            "mcardle_1992_4_male_18_34",
            {
                "sex": "male",
                "age_years": 25,
                "weight_kg": 82,
                "skinfold_abdominal_mm": 22,
                "skinfold_suprailiac_mm": 14,
                "skinfold_triceps_mm": 12,
                "skinfold_thigh_mm": 18,
            },
            15.35,
        ),
        (
            "mcardle_1992_3_female_18_48",
            {
                "sex": "female",
                "age_years": 30,
                "weight_kg": 64,
                "skinfold_abdominal_mm": 18,
                "skinfold_triceps_mm": 20,
                "skinfold_suprailiac_mm": 16,
            },
            24.31,
        ),
        (
            "guedes_1985_3_male_18_30",
            {
                "sex": "male",
                "age_years": 24,
                "weight_kg": 82,
                "skinfold_triceps_mm": 12,
                "skinfold_abdominal_mm": 22,
                "skinfold_suprailiac_mm": 14,
            },
            17.6,
        ),
        (
            "guedes_1985_3_female_18_30",
            {
                "sex": "female",
                "age_years": 24,
                "weight_kg": 64,
                "skinfold_subscapular_mm": 15,
                "skinfold_suprailiac_mm": 16,
                "skinfold_thigh_mm": 24,
            },
            24.31,
        ),
        (
            "petroski_1995_female_18_51",
            {
                "sex": "female",
                "age_years": 32,
                "height_cm": 165,
                "weight_kg": 65,
                "skinfold_midaxillary_mm": 12,
                "skinfold_suprailiac_mm": 16,
                "skinfold_thigh_mm": 24,
                "skinfold_calf_mm": 18,
            },
            24.77,
        ),
        (
            "weltman_1988_female_obese_20_60",
            {
                "sex": "female",
                "age_years": 42,
                "height_cm": 165,
                "weight_kg": 80,
                "abdomen_cm": 98,
            },
            44.22,
        ),
        (
            "slaughter_1988_boys",
            {
                "sex": "male",
                "age_years": 12,
                "weight_kg": 42,
                "skinfold_triceps_mm": 10,
                "skinfold_calf_mm": 12,
            },
            17.17,
        ),
        (
            "slaughter_1988_girls",
            {
                "sex": "female",
                "age_years": 12,
                "weight_kg": 44,
                "skinfold_triceps_mm": 12,
                "skinfold_calf_mm": 14,
            },
            20.96,
        ),
        (
            "faulkner_1968_male_20_30",
            {
                "sex": "male",
                "age_years": 25,
                "weight_kg": 73.6,
                "skinfold_triceps_mm": 10,
                "skinfold_subscapular_mm": 12,
                "skinfold_suprailiac_mm": 14,
                "skinfold_abdominal_mm": 16,
            },
            13.74,
        ),
    ]

    for protocol, payload, expected_percent in cases:
        resolved = resolve_body_fat_fields(
            {
                "body_fat_percent": 30,
                "preferred_body_fat_source": "geneos_composite",
                "measurement_protocol": protocol,
                **payload,
            }
        )

        assert resolved["body_fat_used_source"] == "anthropometry"
        assert resolved["body_fat_method"] == "skinfold_protocol"
        assert resolved["body_fat_used_percent"] == expected_percent


def test_protocol_with_missing_business_fields_stays_manual_only() -> None:
    resolved = resolve_body_fat_fields(
        {
            "sex": "male",
            "age_years": 25,
            "height_cm": 180,
            "weight_kg": 82,
            "body_fat_percent": 24,
            "preferred_body_fat_source": "geneos_composite",
            "measurement_protocol": "weltman_1988_male_obese_20_60",
            "waist_cm": 98,
        }
    )

    assert resolved["body_fat_used_source"] == "bioimpedance"
    assert resolved["body_fat_used_percent"] == 24
    assert resolved["body_fat_method"] == "legacy_bioimpedance"
    assert "anthropometry_protocol_manual_only" in resolved["data_quality_flags_json"]
