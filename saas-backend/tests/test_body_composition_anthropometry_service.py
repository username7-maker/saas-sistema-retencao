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

    assert resolved["body_fat_bioimpedance_percent"] == 24
    assert resolved["body_fat_used_source"] is None
    assert resolved["body_fat_used_percent"] is None
    assert resolved["body_fat_method"] is None
    assert resolved["body_fat_manual_review_required"] is True
    assert "anthropometry_inconsistent" in resolved["data_quality_flags_json"]
    assert "anthropometry_needs_review" in resolved["data_quality_flags_json"]


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


def test_petroski_female_protocol_matches_actuar_operational_case() -> None:
    resolved = resolve_body_fat_fields(
        {
            "sex": "female",
            "age_years": 33,
            "height_cm": 173,
            "weight_kg": 79.5,
            "body_fat_percent": 31.2,
            "preferred_body_fat_source": "geneos_composite",
            "measurement_protocol": "petroski_1995_female_18_51",
            "skinfold_midaxillary_mm": 35,
            "skinfold_suprailiac_mm": 24,
            "skinfold_thigh_mm": 43,
            "skinfold_calf_mm": 27,
            "skinfold_subscapular_mm": 90,
            "skinfold_triceps_mm": 80,
        }
    )

    assert resolved["body_fat_used_source"] == "anthropometry"
    assert resolved["body_fat_method"] == "skinfold_protocol"
    assert resolved["body_fat_used_percent"] == 27.39
    assert resolved["fat_mass_estimated_kg"] == 21.78
    assert resolved["lean_mass_estimated_kg"] == 57.72


def test_legacy_bioimpedance_preference_does_not_override_selected_protocol() -> None:
    resolved = resolve_body_fat_fields(
        {
            "sex": "male",
            "age_years": 22,
            "height_cm": 177,
            "weight_kg": 73.6,
            "body_fat_percent": 31.2,
            "preferred_body_fat_source": "bioimpedance",
            "measurement_protocol": "petroski_1995_male_18_66",
            "skinfold_triceps_mm": 9,
            "skinfold_subscapular_mm": 12,
            "skinfold_suprailiac_mm": 7,
            "skinfold_calf_mm": 10,
        }
    )

    assert resolved["preferred_body_fat_source"] == "bioimpedance"
    assert resolved["body_fat_bioimpedance_percent"] == 31.2
    assert resolved["body_fat_used_source"] == "anthropometry"
    assert resolved["body_fat_method"] == "skinfold_protocol"
    assert resolved["body_fat_used_percent"] == 12.49


def test_raw_exam_percent_becomes_official_when_only_bioimpedance_exists() -> None:
    resolved = resolve_body_fat_fields(
        {
            "sex": "male",
            "age_years": 22,
            "height_cm": 177,
            "weight_kg": 73.6,
            "body_fat_percent": 31.2,
            "preferred_body_fat_source": "bioimpedance",
        }
    )

    assert resolved["preferred_body_fat_source"] == "bioimpedance"
    assert resolved["body_fat_bioimpedance_percent"] == 31.2
    assert resolved["body_fat_used_percent"] == 31.2
    assert resolved["body_fat_used_source"] == "bioimpedance"
    assert resolved["body_fat_method"] == "legacy_bioimpedance"
    assert resolved.get("measurement_source") == "bioimpedance"


def test_default_geneos_falls_back_to_bioimpedance_when_no_measurements_exist() -> None:
    resolved = resolve_body_fat_fields(
        {
            "sex": "male",
            "age_years": 22,
            "height_cm": 177,
            "weight_kg": 73.6,
            "body_fat_percent": 24.8,
            "preferred_body_fat_source": "geneos_composite",
        }
    )

    assert resolved["preferred_body_fat_source"] == "geneos_composite"
    assert resolved["body_fat_bioimpedance_percent"] == 24.8
    assert resolved["body_fat_used_percent"] == 24.8
    assert resolved["body_fat_used_source"] == "bioimpedance"
    assert resolved["body_fat_method"] == "legacy_bioimpedance"
    assert resolved.get("measurement_source") == "bioimpedance"


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
                "age_years": 33,
                "height_cm": 173,
                "weight_kg": 79.5,
                "skinfold_midaxillary_mm": 35,
                "skinfold_suprailiac_mm": 24,
                "skinfold_thigh_mm": 43,
                "skinfold_calf_mm": 27,
                # Regression guard: Actuar/Afig marks these four fields as
                # required for body fat. Triceps/subscapular do not enter.
                "skinfold_subscapular_mm": 90,
                "skinfold_triceps_mm": 80,
            },
            27.39,
        ),
        (
            "petroski_1995_female_18_51",
            {
                "sex": "female",
                "height_cm": 173,
                "weight_kg": 79.5,
                "skinfold_midaxillary_mm": 35,
                "skinfold_suprailiac_mm": 24,
                "skinfold_thigh_mm": 43,
                "skinfold_calf_mm": 27,
            },
            27.39,
        ),
        (
            "weltman_1988_female_obese_20_60",
            {
                "sex": "female",
                "age_years": 42,
                "height_cm": 165,
                "weight_kg": 80,
                "waist_cm": 90,
                "abdomen_cm": 98,
            },
            43.78,
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


def test_weltman_male_requires_both_afig_abdominal_circumferences() -> None:
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

    assert resolved["body_fat_bioimpedance_percent"] == 24
    assert resolved["body_fat_used_source"] is None
    assert resolved["body_fat_used_percent"] is None
    assert resolved["body_fat_method"] is None
    assert resolved["body_fat_manual_review_required"] is True
    assert "anthropometry_protocol_manual_only" not in resolved["data_quality_flags_json"]
    assert "anthropometry_incomplete" in resolved["data_quality_flags_json"]
    assert "anthropometry_needs_review" in resolved["data_quality_flags_json"]


def test_weltman_protocols_match_confirmed_afig_field_contract_and_persist_selection() -> None:
    female = resolve_body_fat_fields(
        {
            "sex": "female",
            "age_years": 42,
            "height_cm": 165,
            "weight_kg": 80,
            "waist_cm": 90,
            "abdomen_cm": 98,
            "preferred_body_fat_source": "anthropometry",
            "measurement_protocol": "weltman_1988_female_obese_20_60",
        }
    )
    male = resolve_body_fat_fields(
        {
            "sex": "male",
            "age_years": 40,
            "weight_kg": 100,
            "waist_cm": 98,
            "abdomen_cm": 110,
            "preferred_body_fat_source": "anthropometry",
            "measurement_protocol": "weltman_1988_male_obese_20_60",
        }
    )

    assert female["measurement_protocol"] == "weltman_1988_female_obese_20_60"
    assert female["body_fat_used_percent"] == 43.78
    assert male["measurement_protocol"] == "weltman_1988_male_obese_20_60"
    assert male["body_fat_used_percent"] == 32.58


def test_newly_effective_protocols_match_reference_cases() -> None:
    base = {
        "preferred_body_fat_source": "anthropometry",
        "weight_kg": 60,
        "skinfold_triceps_mm": 12,
        "skinfold_subscapular_mm": 14,
    }
    cases = [
        ("mcardle_1992_female_9_12", {"sex": "female", "age_years": 10}, 29.82),
        ("mcardle_1992_female_13_16", {"sex": "female", "age_years": 14}, 28.93),
        ("mcardle_1992_male_9_12", {"sex": "male", "age_years": 10}, 28.12),
        ("mcardle_1992_male_13_16", {"sex": "male", "age_years": 14}, 25.57),
        ("guedes_1985_boys_white_prepuberal_6_11", {"sex": "male", "age_years": 10}, 24.35),
        ("guedes_1985_boys_white_puberal_12_16", {"sex": "male", "age_years": 14}, 22.65),
        ("guedes_1985_boys_white_postpuberal_17_18", {"sex": "male", "age_years": 17}, 20.55),
        ("guedes_1985_boys_black_prepuberal_6_11", {"sex": "male", "age_years": 10}, 22.85),
        ("guedes_1985_boys_black_puberal_12_16", {"sex": "male", "age_years": 14}, 20.85),
        ("guedes_1985_boys_black_postpuberal_17_18", {"sex": "male", "age_years": 17}, 19.25),
        ("guedes_1985_girls_sum_under_35", {"sex": "female", "age_years": 14}, 23.29),
        (
            "slaughter_1988_boys_black_white_6_17",
            {
                "sex": "male",
                "age_years": 10,
                "anthropometry_ethnicity": "black",
                "anthropometry_maturity": "prepubertal",
            },
            22.85,
        ),
        ("slaughter_1988_girls_black_white_6_17", {"sex": "female", "age_years": 14}, 23.29),
    ]

    for protocol, extra, expected in cases:
        resolved = resolve_body_fat_fields({**base, **extra, "measurement_protocol": protocol})
        assert resolved["body_fat_used_source"] == "anthropometry", protocol
        assert resolved["body_fat_method"] == "skinfold_protocol", protocol
        assert resolved["body_fat_used_percent"] == expected, protocol
