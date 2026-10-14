import json
import uuid
from datetime import date
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from app.core.dependencies import get_current_user
from app.database import get_db
from app.schemas.body_composition import (
    BodyCompositionFieldMetadata,
    BodyCompositionImageOcrPayload,
    BodyCompositionImageParseResultRead,
    BodyCompositionCaptureMetadata,
    BodyCompositionOcrValues,
    BodyCompositionOcrWarning,
    BodyCompositionRangeValue,
)
from app.services.document_image_preprocessing import DocumentPreprocessingResult

MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def test_small_blurred_receipt_is_read_with_mandatory_field_review():
    from app.services.body_composition_image_parse_service import _complete_parse_request

    capture = BodyCompositionCaptureMetadata(
        capture_mode="single",
        quality_codes=["document_blurred"],
        regional_quality={"receipt_short_side_raw": 248.0},
    )
    result = _complete_parse_request(
        _ai_parse_result(), started_at=perf_counter(), provider="openai",
        image_width=1000, image_height=3400, capture_metadata=capture,
    )

    issue = next(item for item in result.validation_issues if item.code == "image_resolution_manual_review_required")
    assert issue.severity == "critical"
    assert "weight_kg" in issue.fields
    assert "body_fat_kg" in issue.fields
    assert result.values.weight_kg == 84.5
    assert result.needs_review is True


def test_clear_small_receipt_does_not_require_resolution_review():
    from app.services.body_composition_image_parse_service import _complete_parse_request

    capture = BodyCompositionCaptureMetadata(
        capture_mode="single",
        quality_codes=[],
        regional_quality={"receipt_short_side_raw": 248.0},
    )
    result = _complete_parse_request(
        _ai_parse_result(), started_at=perf_counter(), provider="openai",
        image_width=1000, image_height=3400, capture_metadata=capture,
    )
    assert not any(item.code == "image_resolution_manual_review_required" for item in result.validation_issues)


def _local_ocr_payload(weight_kg: float = 14.41) -> BodyCompositionImageOcrPayload:
    return BodyCompositionImageOcrPayload(
        device_profile="tezewa_receipt_v1",
        device_model="Tezewa",
        values=BodyCompositionOcrValues(
            weight_kg=weight_kg,
            body_fat_kg=19.46,
            body_fat_percent=23.0,
            waist_hip_ratio=0.88,
            health_score=62,
        ),
        ranges={
            "weight_kg": BodyCompositionRangeValue(min=61.7, max=75.5),
            "body_fat_kg": BodyCompositionRangeValue(min=7.55, max=14.41),
        },
        warnings=[
            BodyCompositionOcrWarning(
                field="weight_kg",
                message="OCR local veio ambiguo para peso.",
                severity="critical",
            )
        ],
        confidence=0.48,
        raw_text="Weight (kg) 14.41 7.55-14.41",
        needs_review=True,
    )


def _ai_parse_result(weight_kg: float = 84.5) -> BodyCompositionImageParseResultRead:
    return BodyCompositionImageParseResultRead(
        device_profile="tezewa_receipt_v1",
        device_model="Tezewa",
        values=BodyCompositionOcrValues(
            weight_kg=weight_kg,
            body_fat_kg=19.46,
            body_fat_percent=23.0,
            waist_hip_ratio=0.88,
            target_weight_kg=68.3,
            weight_control_kg=-16.1,
            muscle_control_kg=-7.8,
            fat_control_kg=-8.3,
            total_energy_kcal=3008.0,
            physical_age=26,
            health_score=62,
        ),
        ranges={
            "weight_kg": BodyCompositionRangeValue(min=61.7, max=75.5),
            "body_fat_kg": BodyCompositionRangeValue(min=7.55, max=14.41),
            "body_fat_percent": BodyCompositionRangeValue(min=11.0, max=21.0),
        },
        warnings=[],
        confidence=0.94,
        raw_text="Body composition Weight 84.5",
        needs_review=False,
        engine="ai_assisted",
        fallback_used=False,
    )


def _ai_parse_result_with_extra_values() -> BodyCompositionImageParseResultRead:
    payload = _ai_parse_result()
    payload.values.inorganic_salt_kg = 3.2
    payload.values.muscle_mass_kg = 37.2
    payload.values.protein_kg = 17.7
    payload.values.body_water_kg = 43.3
    payload.values.visceral_fat_level = 9.1
    payload.values.bmi = 26.7
    payload.values.basal_metabolic_rate_kcal = 1880.0
    payload.values.skeletal_muscle_kg = 35.6
    payload.values.total_energy_kcal = 3008.0
    payload.values.physical_age = 26
    return payload


def _strict_ai_result(
    *,
    age_years: int = 40,
    sex: str = "male",
    height_cm: float = 180,
    weight_kg: float = 81,
    bmi: float = 25,
    body_water_kg: float | None = 45,
) -> BodyCompositionImageParseResultRead:
    values = BodyCompositionOcrValues(
        age_years=age_years,
        sex=sex,
        height_cm=height_cm,
        weight_kg=weight_kg,
        bmi=bmi,
        body_water_kg=body_water_kg,
    )
    metadata = {
        "age_years": BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.95,
            label="Age",
            evidence=f"Age {age_years}",
            suggested_value=age_years,
        ),
        "sex": BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.95,
            label="Sex",
            evidence=f"Sex {'Male' if sex == 'male' else 'Female'}",
            suggested_value=sex,
        ),
        "height_cm": BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.95,
            label="Height (cm)",
            evidence=f"Height (cm) {height_cm}",
            suggested_value=height_cm,
        ),
        "weight_kg": BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.95,
            label="Weight (kg)",
            evidence=f"Weight (kg) {weight_kg}",
            suggested_value=weight_kg,
        ),
        "bmi": BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.95,
            label="BMI",
            evidence=f"BMI {bmi}",
            suggested_value=bmi,
        ),
    }
    if body_water_kg is not None:
        metadata["body_water_kg"] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.95,
            label="Body water (kg)",
            evidence=f"Body water (kg) {body_water_kg}",
            suggested_value=body_water_kg,
        )
    return BodyCompositionImageParseResultRead(
        device_profile="tezewa_receipt_v1",
        values=values,
        confidence=0.95,
        engine="ai_assisted",
        field_metadata=metadata,
    )


def _validate_strict(
    result: BodyCompositionImageParseResultRead,
    *,
    evaluation_date: date = date(2026, 9, 3),
    member_birthdate: date | None = date(1986, 9, 3),
    member_sex: str | None = "male",
    member_height_cm: float | None = 180,
    previous_weight_kg: float | None = 80,
) -> BodyCompositionImageParseResultRead:
    from app.services.body_composition_image_parse_service import _validate_ai_first_result

    with patch(
        "app.services.body_composition_image_parse_service.settings.body_composition_image_ai_validation_enabled",
        True,
    ):
        return _validate_ai_first_result(
            result,
            extraction_origin="ai_image",
            evaluation_date=evaluation_date,
            member_birthdate=member_birthdate,
            member_sex=member_sex,
            member_height_cm=member_height_cm,
            previous_weight_kg=previous_weight_kg,
        )


class TestImageParseService:
    def test_recovery_targets_plausible_value_without_valid_evidence(self):
        primary = _strict_ai_result()
        primary.field_metadata["height_cm"] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.9,
            label="Height",
            evidence=None,
            suggested_value=180,
        )

        from app.services.body_composition_image_parse_service import _recovery_read_fields

        assert "height_cm" in _recovery_read_fields(primary)

    def test_recovery_disagreement_does_not_override_verified_primary_value(self):
        primary = _strict_ai_result(weight_kg=81)
        recovery = _strict_ai_result(weight_kg=91)

        from app.services.body_composition_image_parse_service import _merge_ai_recovery_result

        merged = _merge_ai_recovery_result(primary, recovery)

        assert merged.values.weight_kg == 81
        assert merged.field_metadata["weight_kg"].state == "accepted"
        assert any(
            issue.code == "ai_enhancement_disagreement_ignored" and issue.severity == "warning"
            for issue in merged.validation_issues
        )

        validated = _validate_strict(merged)
        assert validated.field_metadata["weight_kg"].state == "accepted"
        assert not any(issue.severity == "critical" for issue in validated.validation_issues)

    def test_recovery_detects_conflicting_sex_and_printed_time(self):
        primary = _strict_ai_result(sex="male")
        primary.values.measured_at = "2026-09-03T08:18:00"
        primary.field_metadata["measured_at"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Test time", evidence="Test time 2026-09-03 08:18",
            suggested_value="2026-09-03T08:18:00",
        )
        recovery = _strict_ai_result(sex="female")
        recovery.values.measured_at = "2026-09-03T09:18:00"
        recovery.field_metadata["measured_at"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Test time", evidence="Test time 2026-09-03 09:18",
            suggested_value="2026-09-03T09:18:00",
        )

        from app.services.body_composition_image_parse_service import _merge_ai_recovery_result

        merged = _merge_ai_recovery_result(primary, recovery)

        assert merged.values.sex == "male"
        assert merged.values.measured_at == "2026-09-03T08:18:00"
        assert merged.field_metadata["sex"].state == "accepted"
        assert {
            issue.fields[0]
            for issue in merged.validation_issues
            if issue.code == "ai_enhancement_disagreement_ignored"
        } >= {
            "sex", "measured_at",
        }
        assert all(
            issue.severity == "warning"
            for issue in merged.validation_issues
            if issue.code == "ai_enhancement_disagreement_ignored"
            and issue.fields[0] in {"sex", "measured_at"}
        )

    def test_recovery_treats_equivalent_local_and_utc_times_as_equal(self):
        primary = _strict_ai_result()
        primary.values.measured_at = "2026-09-03T22:18:00"
        recovery = _strict_ai_result()
        recovery.values.measured_at = "2026-09-04T01:18:00+00:00"

        from app.services.body_composition_image_parse_service import _merge_ai_recovery_result

        merged = _merge_ai_recovery_result(primary, recovery)

        assert not any(
            issue.code == "ai_enhancement_conflict" and issue.fields == ["measured_at"]
            for issue in merged.validation_issues
        )

    def test_recovery_replaces_primary_value_with_invalid_evidence(self):
        primary = _strict_ai_result()
        primary.field_metadata["height_cm"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Height", evidence=None, suggested_value=180,
        )
        recovery = _strict_ai_result()

        from app.services.body_composition_image_parse_service import _merge_ai_recovery_result

        merged = _merge_ai_recovery_result(primary, recovery)

        assert merged.values.height_cm == 180
        assert merged.field_metadata["height_cm"].evidence == "Height (cm) 180"

    def test_value_column_disagreement_prefers_range_free_read_with_review(self):
        from app.services.body_composition_image_parse_service import _reconcile_value_column_read

        primary = _strict_ai_result(weight_kg=81)
        focused = _strict_ai_result(weight_kg=91)

        result = _reconcile_value_column_read(primary, focused)

        assert result.values.weight_kg == 91
        assert result.field_metadata["weight_kg"].state == "conflict"
        assert result.field_metadata["weight_kg"].suggested_value == 91
        assert any(
            issue.code == "ai_value_column_corrected" and "weight_kg" in issue.fields
            for issue in result.validation_issues
        )
        assert result.needs_review is True

    def test_value_column_can_restore_missing_measured_field(self):
        from app.services.body_composition_image_parse_service import _reconcile_value_column_read

        primary = _strict_ai_result()
        focused = _strict_ai_result()
        focused.values.inorganic_salt_kg = 2.9
        focused.field_metadata["inorganic_salt_kg"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Inorganic salt", evidence="Inorganic salt 2.9", suggested_value=2.9,
        )

        result = _reconcile_value_column_read(primary, focused)

        assert result.values.inorganic_salt_kg == 2.9
        assert result.field_metadata["inorganic_salt_kg"].state == "accepted"

    def test_missing_value_column_confirmation_preserves_verified_primary(self):
        from app.services.body_composition_image_parse_service import _reconcile_value_column_read

        result = _reconcile_value_column_read(_strict_ai_result(), None)

        assert result.values.weight_kg == 81
        assert result.values.bmi == 25.0
        assert any(issue.code == "ai_value_column_second_read_unavailable" for issue in result.validation_issues)

    def test_ai_evidence_rejects_number_from_preceding_row(self):
        from app.services.body_composition_image_parse_service import _ai_metadata_validation_error

        metadata = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Muscle mass", evidence="Inorganic salt 2.9 Muscle mass 23.4",
            suggested_value=2.9,
        )
        assert _ai_metadata_validation_error("muscle_mass_kg", 2.9, metadata) == "ai_evidence_row_mismatch"

    def test_parse_checks_independent_value_column_before_accepting_table_values(self):
        primary = _strict_ai_result()
        focused = _strict_ai_result()
        with patch(
            "app.services.body_composition_image_parse_service.settings.body_composition_image_ai_validation_enabled",
            True,
        ), patch(
            "app.services.body_composition_image_parse_service.settings.openai_api_key", "test-openai-key",
        ), patch(
            "app.services.body_composition_image_parse_service._image_ai_available", return_value=True,
        ), patch(
            "app.services.body_composition_image_parse_service.preprocess_receipt_image", return_value=None,
        ), patch(
            "app.services.body_composition_image_parse_service.build_receipt_value_column_image",
            return_value=b"cropped-value-column",
        ), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            side_effect=[primary, focused],
        ) as mock_provider:
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image", media_type="image/jpeg",
                device_profile="tezewa_receipt_v1", evaluation_date=date(2026, 9, 3),
                member_sex="male", member_height_cm=180,
            )

        assert mock_provider.call_count == 2
        assert mock_provider.call_args_list[1].kwargs["value_column_only"] is True
        assert mock_provider.call_args_list[1].kwargs["images"][0][0] == b"cropped-value-column"
        assert result.values.weight_kg == 81
        assert result.values.bmi == 25

    def test_retries_with_safe_enhancement_only_when_essential_fields_are_missing(self):
        primary = _strict_ai_result()
        primary.values.age_years = None
        primary.values.sex = None
        primary.values.height_cm = None
        primary.values.bmi = None
        for field_name in ("age_years", "sex", "height_cm", "bmi"):
            primary.field_metadata.pop(field_name, None)
        recovered = _strict_ai_result()
        preprocessing = DocumentPreprocessingResult(
            image_bytes=b"primary-enhanced",
            media_type="image/jpeg",
            applied=True,
            method="original+clahe",
            confidence=0.8,
            source_width=1920,
            source_height=1080,
            output_width=1920,
            output_height=1080,
            recovery_image_bytes=b"recovery-high-contrast",
            recovery_media_type="image/jpeg",
            recovery_method="thermal_adaptive_threshold+unsharp",
        )

        with patch(
            "app.services.body_composition_image_parse_service.settings.body_composition_image_ai_validation_enabled",
            True,
        ), patch(
            "app.services.body_composition_image_parse_service.settings.openai_api_key",
            "test-openai-key",
        ), patch(
            "app.services.body_composition_image_parse_service._image_ai_available",
            return_value=True,
        ), patch(
            "app.services.body_composition_image_parse_service.preprocess_receipt_image",
            return_value=preprocessing,
        ), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            side_effect=[primary, recovered],
        ) as mock_provider:
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                evaluation_date=date(2026, 9, 3),
                member_birthdate=None,
                member_sex=None,
                member_height_cm=None,
            )

        assert mock_provider.call_count == 2
        assert mock_provider.call_args_list[0].kwargs["images"][0][0] == b"primary-enhanced"
        assert mock_provider.call_args_list[1].kwargs["images"][0][0] == b"recovery-high-contrast"
        assert result.values.age_years == 40
        assert result.values.height_cm == 180
        # A missing second crop must not erase a separately validated read.
        assert result.values.bmi == 25
        assert result.processing.enhancement_retry_used is True
        assert result.processing.enhancement_variant == "thermal_adaptive_threshold+unsharp"

    def test_recovery_failure_keeps_primary_ai_result(self):
        primary = _strict_ai_result()
        primary.values.bmi = None
        primary.field_metadata.pop("bmi", None)
        preprocessing = DocumentPreprocessingResult(
            image_bytes=b"primary-enhanced",
            media_type="image/jpeg",
            applied=True,
            method="original+clahe",
            confidence=0.8,
            source_width=1920,
            source_height=1080,
            output_width=1920,
            output_height=1080,
            recovery_image_bytes=b"recovery-high-contrast",
            recovery_media_type="image/jpeg",
            recovery_method="thermal_adaptive_threshold+unsharp",
        )

        with patch(
            "app.services.body_composition_image_parse_service.settings.body_composition_image_ai_validation_enabled",
            True,
        ), patch(
            "app.services.body_composition_image_parse_service.settings.openai_api_key",
            "test-openai-key",
        ), patch(
            "app.services.body_composition_image_parse_service._image_ai_available",
            return_value=True,
        ), patch(
            "app.services.body_composition_image_parse_service.preprocess_receipt_image",
            return_value=preprocessing,
        ), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            side_effect=[primary, TimeoutError("recovery timed out")],
        ):
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                evaluation_date=date(2026, 9, 3),
                member_birthdate=date(1986, 9, 3),
                member_sex="male",
                member_height_cm=180,
            )

        assert result.values.weight_kg == 81
        assert any(issue.code == "ai_value_column_second_read_unavailable" for issue in result.validation_issues)
        assert result.processing.primary_engine == "ai_image"
        assert result.processing.enhancement_retry_used is False

    def test_strict_parse_keeps_member_context_out_of_provider_request(self):
        with patch(
            "app.services.body_composition_image_parse_service.settings.body_composition_image_ai_validation_enabled",
            True,
        ), patch(
            "app.services.body_composition_image_parse_service.settings.openai_api_key",
            "test-openai-key",
        ), patch(
            "app.services.body_composition_image_parse_service._image_ai_available",
            return_value=True,
        ), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            return_value=_strict_ai_result(),
        ) as mock_provider:
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=_local_ocr_payload(),
                evaluation_date=date(2026, 9, 3),
                member_birthdate=date(1986, 9, 3),
                member_sex="male",
                member_height_cm=180,
                previous_weight_kg=80,
            )

        assert mock_provider.call_args.kwargs["local_ocr_result"] is None
        assert result.values.age_years == 40
        assert result.values.sex == "male"
        assert result.values.height_cm == 180
        assert result.processing.primary_engine == "ai_image"

    def test_strict_mode_derives_age_on_birthday_and_day_before(self):
        on_birthday = _validate_strict(
            _strict_ai_result(age_years=40),
            evaluation_date=date(2026, 9, 3),
            member_birthdate=date(1986, 9, 3),
        )
        before_birthday = _validate_strict(
            _strict_ai_result(age_years=39),
            evaluation_date=date(2026, 9, 2),
            member_birthdate=date(1986, 9, 3),
        )

        assert on_birthday.values.age_years == 40
        assert before_birthday.values.age_years == 39
        assert on_birthday.field_metadata["age_years"].origin == "derived"

    def test_strict_mode_uses_evidenced_photo_age_when_birthdate_is_missing(self):
        result = _validate_strict(_strict_ai_result(), member_birthdate=None)

        assert result.values.age_years == 40
        assert result.field_metadata["age_years"].origin == "ai_image"
        assert not any(issue.code == "age_manual_confirmation_required" for issue in result.validation_issues)

    def test_strict_mode_requires_manual_age_without_birthdate_or_photo_evidence(self):
        payload = _strict_ai_result()
        payload.field_metadata["age_years"] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.99,
            label="Age",
            evidence=None,
            suggested_value=40,
        )

        result = _validate_strict(payload, member_birthdate=None)

        assert result.values.age_years is None
        assert result.field_metadata["age_years"].origin == "manual"
        assert any(issue.code == "age_manual_confirmation_required" for issue in result.validation_issues)

    def test_strict_mode_never_uses_physical_age_as_chronological_age(self):
        payload = _strict_ai_result(age_years=26)
        payload.field_metadata["age_years"] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.99,
            label="Physical age",
            evidence="Physical age 26",
            suggested_value=26,
        )

        result = _validate_strict(payload)

        assert result.values.age_years == 40
        assert any(issue.code == "physical_age_used_as_chronological_age" for issue in result.validation_issues)

    def test_strict_mode_discards_ai_value_without_evidence(self):
        payload = _strict_ai_result()
        payload.field_metadata["weight_kg"] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.99,
            label="Weight (kg)",
            evidence=None,
            suggested_value=81,
        )

        result = _validate_strict(payload)

        assert result.values.weight_kg is None
        assert result.field_metadata["weight_kg"].state == "unavailable"
        assert any(issue.code == "ai_value_without_evidence" for issue in result.validation_issues)

    def test_missing_photo_age_evidence_does_not_block_derived_profile_age(self):
        payload = _strict_ai_result()
        payload.field_metadata["age_years"] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.99,
            label="Age",
            evidence=None,
            suggested_value=40,
        )

        result = _validate_strict(payload)

        assert result.values.age_years == 40
        issue = next(issue for issue in result.validation_issues if issue.code == "ai_value_without_evidence")
        assert issue.severity == "warning"
        assert result.needs_review is False

    def test_strict_mode_accepts_two_centimeter_height_delta_and_blocks_above_it(self):
        accepted = _validate_strict(_strict_ai_result(height_cm=182), member_height_cm=180)
        conflicted = _validate_strict(_strict_ai_result(height_cm=182.1), member_height_cm=180)

        assert accepted.values.height_cm == 180
        assert not any(issue.code == "height_profile_conflict" for issue in accepted.validation_issues)
        assert conflicted.values.height_cm == 180
        assert conflicted.field_metadata["height_cm"].suggested_value == 182.1
        assert any(issue.code == "height_profile_conflict" for issue in conflicted.validation_issues)

    def test_strict_mode_uses_evidenced_photo_height_when_profile_is_invalid(self):
        result = _validate_strict(_strict_ai_result(height_cm=178), member_height_cm=80)

        assert result.values.height_cm == 178
        assert result.field_metadata["height_cm"].origin == "ai_image"
        assert result.field_metadata["height_cm"].suggested_value == 178
        assert not any(issue.code == "height_manual_confirmation_required" for issue in result.validation_issues)

    def test_strict_mode_uses_evidenced_photo_sex_when_profile_is_missing(self):
        result = _validate_strict(_strict_ai_result(sex="female"), member_sex=None)

        assert result.values.sex == "female"
        assert result.field_metadata["sex"].origin == "ai_image"
        assert not any(issue.code == "sex_manual_confirmation_required" for issue in result.validation_issues)

    def test_strict_mode_rejects_male_when_evidence_says_female(self):
        payload = _strict_ai_result(sex="male")
        payload.field_metadata["sex"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Sex", evidence="Sex: Female", suggested_value="male",
        )

        result = _validate_strict(payload, member_sex=None)

        assert result.values.sex is None
        assert any(issue.code == "ai_evidence_value_mismatch" for issue in result.validation_issues)

    def test_strict_mode_validates_bmi_with_configured_tolerance(self):
        accepted = _validate_strict(_strict_ai_result(weight_kg=81, height_cm=180, bmi=25.5))
        conflicted = _validate_strict(_strict_ai_result(weight_kg=81, height_cm=180, bmi=25.6))

        assert not any(issue.code == "bmi_consistency_conflict" for issue in accepted.validation_issues)
        bmi_issue = next(issue for issue in conflicted.validation_issues if issue.code == "bmi_consistency_conflict")
        assert bmi_issue.fields == ["weight_kg", "height_cm", "bmi"]
        assert bmi_issue.severity == "critical"

    def test_strict_mode_warns_only_above_twenty_percent_previous_weight_change(self):
        boundary = _validate_strict(
            _strict_ai_result(weight_kg=120, bmi=37.04),
            previous_weight_kg=100,
        )
        above = _validate_strict(
            _strict_ai_result(weight_kg=120.1, bmi=37.07),
            previous_weight_kg=100,
        )

        assert not any(issue.code == "weight_previous_variation" for issue in boundary.validation_issues)
        warning = next(issue for issue in above.validation_issues if issue.code == "weight_previous_variation")
        assert warning.severity == "warning"
        assert above.values.weight_kg == 120.1

    def test_strict_mode_marks_calculated_water_percentage_as_derived(self):
        result = _validate_strict(_strict_ai_result(weight_kg=90, bmi=27.78, body_water_kg=45))

        assert result.values.body_water_percent == 50
        assert result.field_metadata["body_water_percent"].origin == "derived"
        assert result.field_metadata["body_water_percent"].state == "accepted"

    def test_strict_mode_maps_skeletal_muscle_from_body_parameters_to_percent(self):
        payload = _strict_ai_result(weight_kg=90, bmi=27.78, body_water_kg=45)
        payload.values.basal_metabolic_rate_kcal = 1880
        payload.values.skeletal_muscle_percent = 38.2
        payload.field_metadata["body_water_kg"] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.95,
            label="Body moisture",
            evidence="Body moisture 45",
            suggested_value=45,
        )
        payload.field_metadata["basal_metabolic_rate_kcal"] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.95,
            label="Basic metabolism",
            evidence="Basic metabolism 1880",
            suggested_value=1880,
        )
        payload.field_metadata["skeletal_muscle_percent"] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted",
            confidence=0.95,
            label="Skeletal muscle",
            evidence="Body parameters (%) Skeletal muscle 38.2",
            suggested_value=38.2,
        )

        result = _validate_strict(payload)

        assert result.values.body_water_kg == 45
        assert result.values.basal_metabolic_rate_kcal == 1880
        assert result.values.skeletal_muscle_percent == 38.2
        assert result.values.skeletal_muscle_kg is None
        rejected_fields = {
            issue.fields[0]
            for issue in result.validation_issues
            if issue.code == "ai_label_field_mismatch" and issue.fields
        }
        assert not {"body_water_kg", "basal_metabolic_rate_kcal", "skeletal_muscle_percent"} & rejected_fields

    def test_strict_mode_supports_real_tezewa_narrow_receipt_labels(self):
        """Covers the receipt structure without retaining its identifier or image."""
        payload = _strict_ai_result(
            age_years=44,
            sex="female",
            height_cm=158,
            weight_kg=65.1,
            bmi=26.1,
            body_water_kg=35.8,
        )
        payload.values.measured_at = "2026-08-25T08:18:00"
        payload.values.body_fat_kg = 21.12
        payload.values.body_fat_percent = 32.4
        payload.values.waist_hip_ratio = 0.86
        payload.values.fat_free_mass_kg = 44.0
        payload.values.inorganic_salt_kg = 2.9
        payload.values.muscle_mass_kg = 23.4
        payload.values.protein_kg = 10.0
        payload.values.visceral_fat_level = 7.0
        payload.values.basal_metabolic_rate_kcal = 1366
        payload.values.skeletal_muscle_percent = 25.7
        payload.values.target_weight_kg = 58.1
        payload.values.weight_control_kg = -7.0
        payload.values.muscle_control_kg = -2.1
        payload.values.fat_control_kg = -4.9
        payload.values.total_energy_kcal = 2185.6
        payload.values.physical_age = 44
        payload.values.health_score = 72

        def metadata(label: str, evidence: str, value: object) -> BodyCompositionFieldMetadata:
            return BodyCompositionFieldMetadata(
                origin="ai_image",
                state="accepted",
                confidence=0.95,
                label=label,
                evidence=evidence,
                suggested_value=value,
            )

        payload.field_metadata.update(
            {
                "age_years": metadata("Age", "Age: 44", 44),
                "sex": metadata("Sex", "Sex: Woman", "female"),
                "height_cm": metadata("Height", "Height: 158cm", 158),
                "weight_kg": metadata("Weight", "Weight: 65.1kg", 65.1),
                "measured_at": metadata("Test time", "Test time: 2026-08-25 08:18", "2026-08-25T08:18:00"),
                "body_fat_kg": metadata("Body fat (kg)", "Body fat (kg) 21.12", 21.12),
                "body_fat_percent": metadata("Body fat ratio", "Body fat ratio (%) 32.4", 32.4),
                "waist_hip_ratio": metadata("Waist hip", "Waist hip 0.86", 0.86),
                "fat_free_mass_kg": metadata("Fat free", "Fat free 44.0 (kg)", 44.0),
                "inorganic_salt_kg": metadata("Inorganic salt", "Inorganic salt 2.9", 2.9),
                "muscle_mass_kg": metadata("Muscle mass", "Muscle mass (kg) 23.4", 23.4),
                "protein_kg": metadata("Protein", "Protein (kg) 10.0", 10.0),
                "body_water_kg": metadata("(kg)", "(kg) Body moisture 35.8", 35.8),
                "visceral_fat_level": metadata("Visceral fat", "Visceral fat 7.0", 7.0),
                "basal_metabolic_rate_kcal": metadata("Basal metabolism", "Basal metabolism 1366", 1366),
                "bmi": metadata("BMI", "BMI 26.1", 26.1),
                "skeletal_muscle_percent": metadata("Skeletal muscle", "Body parameters (%) Skeletal muscle 25.7", 25.7),
                "target_weight_kg": metadata("Target weight", "Target weight (kg) 58.1kg", 58.1),
                "weight_control_kg": metadata("Weight control", "Weight control (kg) -7.0kg", -7.0),
                "muscle_control_kg": metadata("Muscle control", "Muscle control (kg) -2.1kg", -2.1),
                "fat_control_kg": metadata("Fat control", "Fat control (kg) -4.9kg", -4.9),
                "total_energy_kcal": metadata("Total energy consumption", "Total energy consumption 2185.6", 2185.6),
                "physical_age": metadata("Physical age", "Physical age 44", 44),
                "health_score": metadata("Health score", "Health score 72", 72),
            }
        )

        result = _validate_strict(
            payload,
            evaluation_date=date(2026, 8, 25),
            member_birthdate=None,
            member_sex=None,
            member_height_cm=None,
            previous_weight_kg=None,
        )

        assert result.values.age_years == 44
        assert result.values.physical_age == 44
        assert result.values.sex == "female"
        assert result.values.height_cm == 158
        assert result.values.weight_kg == 65.1
        assert result.values.bmi == 26.1
        assert result.values.fat_free_mass_kg == 44.0
        assert result.values.body_water_kg == 35.8
        assert result.values.basal_metabolic_rate_kcal == 1366
        assert result.values.skeletal_muscle_percent == 25.7
        assert result.values.skeletal_muscle_kg is None
        assert result.needs_review is False

    def test_strict_mode_rejects_range_endpoints_as_principal_measurements(self):
        payload = _strict_ai_result(weight_kg=65.1, bmi=26.1, body_water_kg=35.8)
        payload.values.muscle_mass_kg = 18.0
        payload.values.basal_metabolic_rate_kcal = 1053
        payload.values.skeletal_muscle_percent = 13.2
        payload.ranges.update(
            {
                "muscle_mass_kg": BodyCompositionRangeValue(min=18.0, max=20.6),
                "basal_metabolic_rate_kcal": BodyCompositionRangeValue(min=1053, max=1346),
                "skeletal_muscle_percent": BodyCompositionRangeValue(min=13.2, max=24.8),
            }
        )
        payload.field_metadata.update(
            {
                "muscle_mass_kg": BodyCompositionFieldMetadata(
                    origin="ai_image",
                    state="accepted",
                    confidence=0.95,
                    label="Muscle mass (kg)",
                    evidence="Muscle mass (kg) 18.0~20.6",
                    suggested_value=18.0,
                ),
                "basal_metabolic_rate_kcal": BodyCompositionFieldMetadata(
                    origin="ai_image",
                    state="accepted",
                    confidence=0.95,
                    label="Basal metabolism",
                    evidence="Basal metabolism 1053~1346",
                    suggested_value=1053,
                ),
                "skeletal_muscle_percent": BodyCompositionFieldMetadata(
                    origin="ai_image",
                    state="accepted",
                    confidence=0.95,
                    label="Skeletal muscle",
                    evidence="Body parameters (%) Skeletal muscle 13.2~24.8",
                    suggested_value=13.2,
                ),
            }
        )

        result = _validate_strict(
            payload,
            evaluation_date=date(2026, 8, 25),
            member_birthdate=None,
            member_sex=None,
            member_height_cm=None,
            previous_weight_kg=None,
        )

        assert result.values.muscle_mass_kg is None
        assert result.values.basal_metabolic_rate_kcal is None
        assert result.values.skeletal_muscle_percent is None
        rejected_fields = {
            issue.fields[0]
            for issue in result.validation_issues
            if issue.code == "ai_range_endpoint_used_as_value" and issue.fields
        }
        assert rejected_fields == {
            "muscle_mass_kg",
            "basal_metabolic_rate_kcal",
            "skeletal_muscle_percent",
        }
        assert result.needs_review is True

    def test_normalization_discards_ai_value_supported_only_by_a_printed_range(self):
        from app.services.body_composition_image_parse_service import _normalize_ai_payload

        result = _normalize_ai_payload(
            {
                "values": {"basal_metabolic_rate_kcal": 1053},
                "ranges": {"basal_metabolic_rate_kcal": {"min": 1053, "max": 1346}},
                "warnings": [],
                "field_metadata": {
                    "basal_metabolic_rate_kcal": {
                        "origin": "ai_image",
                        "state": "accepted",
                        "confidence": 0.95,
                        "label": "Basal metabolism",
                        "evidence": "Basal metabolism 1053~1346",
                        "suggested_value": 1053,
                    }
                },
            },
            device_profile="tezewa_receipt_v1",
            local_ocr_result=None,
        )

        assert result.values.basal_metabolic_rate_kcal is None
        assert result.field_metadata["basal_metabolic_rate_kcal"].state == "unavailable"
        assert any(
            warning.field == "basal_metabolic_rate_kcal" and warning.severity == "critical"
            for warning in result.warnings
        )

    def test_normalization_discards_range_endpoint_when_ocr_loses_the_separator(self):
        from app.services.body_composition_image_parse_service import _normalize_ai_payload

        result = _normalize_ai_payload(
            {
                "values": {"muscle_mass_kg": 18.0},
                "ranges": {"muscle_mass_kg": {"min": 18.0, "max": 20.6}},
                "field_metadata": {
                    "muscle_mass_kg": {
                        "origin": "ai_image",
                        "state": "accepted",
                        "confidence": 0.95,
                        "label": "Muscle mass (kg)",
                        "evidence": "Muscle mass (kg) 18.0 20.6",
                        "suggested_value": 18.0,
                    }
                },
            },
            device_profile="tezewa_receipt_v1",
            local_ocr_result=None,
        )

        assert result.values.muscle_mass_kg is None
        assert result.needs_review is True

    def test_normalization_keeps_measured_value_that_legitimately_equals_range_endpoint(self):
        from app.services.body_composition_image_parse_service import _normalize_ai_payload

        result = _normalize_ai_payload(
            {
                "values": {"inorganic_salt_kg": 2.9},
                "ranges": {"inorganic_salt_kg": {"min": 2.4, "max": 2.9}},
                "field_metadata": {
                    "inorganic_salt_kg": {
                        "origin": "ai_image",
                        "state": "accepted",
                        "confidence": 0.95,
                        "label": "Inorganic salt",
                        "evidence": "Inorganic salt 2.9",
                        "suggested_value": 2.9,
                    }
                },
            },
            device_profile="tezewa_receipt_v1",
            local_ocr_result=None,
        )

        assert result.values.inorganic_salt_kg == 2.9
        assert result.field_metadata["inorganic_salt_kg"].state == "accepted"
        assert not any(warning.field == "inorganic_salt_kg" for warning in result.warnings)

    def test_normalization_ignores_degenerate_ai_range_for_measured_value(self):
        from app.services.body_composition_image_parse_service import _normalize_ai_payload

        result = _normalize_ai_payload(
            {
                "values": {"waist_hip_ratio": 0.86},
                "ranges": {"waist_hip_ratio": {"min": 0.86, "max": 0.86}},
                "field_metadata": {
                    "waist_hip_ratio": {
                        "origin": "ai_image",
                        "state": "accepted",
                        "confidence": 0.95,
                        "label": "Waist hip 0.86",
                        "evidence": "Waist hip 0.86",
                        "suggested_value": 0.86,
                    }
                },
            },
            device_profile="tezewa_receipt_v1",
            local_ocr_result=None,
        )

        assert result.values.waist_hip_ratio == 0.86
        assert result.field_metadata["waist_hip_ratio"].state == "accepted"
        assert not any(warning.field == "waist_hip_ratio" for warning in result.warnings)

    def test_strict_mode_rejects_degree_separated_range_without_ranges_payload(self):
        payload = _strict_ai_result()
        payload.values.waist_hip_ratio = 0.75
        payload.values.muscle_mass_kg = 18.0
        payload.values.basal_metabolic_rate_kcal = 1053
        for field_name, label, evidence, value in (
            ("waist_hip_ratio", "Waist hip", "Waist hip 0.75°0.85", 0.75),
            ("muscle_mass_kg", "Muscle mass (kg)", "Muscle mass (kg) 18.0°20.6", 18.0),
            ("basal_metabolic_rate_kcal", "Basal metabolism", "Basal metabolism 1053°1346", 1053),
        ):
            payload.field_metadata[field_name] = BodyCompositionFieldMetadata(
                origin="ai_image", state="accepted", confidence=0.95,
                label=label, evidence=evidence, suggested_value=value,
            )

        result = _validate_strict(payload)

        assert result.values.waist_hip_ratio is None
        assert result.values.muscle_mass_kg is None
        assert result.values.basal_metabolic_rate_kcal is None
        rejected = {
            issue.fields[0] for issue in result.validation_issues
            if issue.code == "ai_range_endpoint_used_as_value" and issue.fields
        }
        assert rejected == {"waist_hip_ratio", "muscle_mass_kg", "basal_metabolic_rate_kcal"}

    def test_strict_mode_accepts_measured_bmr_joined_to_thermal_receipt_label(self):
        payload = _strict_ai_result()
        payload.values.basal_metabolic_rate_kcal = 1366
        payload.ranges["basal_metabolic_rate_kcal"] = BodyCompositionRangeValue(min=1053, max=1346)
        payload.field_metadata["basal_metabolic_rate_kcal"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Basal metabolism", evidence="Basal metabolism1366 1053~1346",
            suggested_value=1366,
        )

        result = _validate_strict(payload)

        assert result.values.basal_metabolic_rate_kcal == 1366
        assert result.field_metadata["basal_metabolic_rate_kcal"].state == "accepted"

    def test_strict_mode_rejects_goal_weight_as_current_weight(self):
        payload = _strict_ai_result()
        payload.values.bmi = None
        payload.values.weight_kg = 58.1
        payload.field_metadata["weight_kg"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Target weight", evidence="Target weight 58.1", suggested_value=58.1,
        )

        result = _validate_strict(payload)

        assert result.values.weight_kg is None
        assert any(issue.code == "ai_label_field_mismatch" for issue in result.validation_issues)

    def test_strict_mode_checks_printed_time_and_date_against_selected_date(self):
        payload = _strict_ai_result()
        payload.values.evaluation_date = "2026-09-02"
        payload.values.measured_at = "2026-09-02T11:00:00"
        payload.field_metadata["evaluation_date"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Test time", evidence="Test time 2026-09-02 08:18", suggested_value="2026-09-02",
        )
        payload.field_metadata["measured_at"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Test time", evidence="Test time 2026-09-02 08:18", suggested_value="2026-09-02T11:00:00",
        )

        result = _validate_strict(payload)

        assert result.values.measured_at is None
        assert result.values.evaluation_date == "2026-09-03"
        assert any(issue.code == "evaluation_date_receipt_conflict" for issue in result.validation_issues)

    def test_strict_mode_checks_printed_timestamp_even_without_separate_date(self):
        payload = _strict_ai_result()
        payload.values.measured_at = "2026-09-02T08:18:00"
        payload.field_metadata["measured_at"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Test time", evidence="Test time 2026-09-02 08:18",
            suggested_value="2026-09-02T08:18:00",
        )

        result = _validate_strict(payload)

        assert result.values.evaluation_date == "2026-09-03"
        assert result.field_metadata["evaluation_date"].suggested_value == "2026-09-02"
        assert any(issue.code == "evaluation_date_receipt_conflict" for issue in result.validation_issues)

    def test_strict_mode_checks_both_printed_dates_when_they_disagree(self):
        payload = _strict_ai_result()
        payload.values.evaluation_date = "2026-09-03"
        payload.values.measured_at = "2026-09-02T08:18:00"
        payload.field_metadata["evaluation_date"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Test time", evidence="Test time 2026-09-03 08:18",
            suggested_value="2026-09-03",
        )
        payload.field_metadata["measured_at"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Test time", evidence="Test time 2026-09-02 08:18",
            suggested_value="2026-09-02T08:18:00",
        )

        result = _validate_strict(payload)

        assert any(issue.code == "evaluation_date_receipt_conflict" for issue in result.validation_issues)

    def test_strict_mode_matches_timezone_aware_timestamp_to_local_receipt_time(self):
        payload = _strict_ai_result()
        payload.values.measured_at = "2026-09-04T01:18:00+00:00"
        payload.field_metadata["measured_at"] = BodyCompositionFieldMetadata(
            origin="ai_image", state="accepted", confidence=0.95,
            label="Test time", evidence="Test time 2026-09-03 22:18",
            suggested_value="2026-09-04T01:18:00+00:00",
        )

        result = _validate_strict(payload)

        assert result.values.measured_at == "2026-09-04T01:18:00+00:00"
        assert result.field_metadata["measured_at"].state == "accepted"
        assert not any(issue.code == "evaluation_date_receipt_conflict" for issue in result.validation_issues)

    def test_recovery_read_includes_missing_receipt_fields(self):
        from app.services.body_composition_image_parse_service import _recovery_read_fields

        payload = _strict_ai_result()
        assert {"inorganic_salt_kg", "waist_hip_ratio", "muscle_mass_kg", "basal_metabolic_rate_kcal"}.issubset(
            set(_recovery_read_fields(payload))
        )

    def test_strict_mode_flags_inconsistent_body_fat_and_fat_free_mass(self):
        payload = _strict_ai_result()
        payload.values.body_fat_kg = 35.0
        payload.values.body_fat_percent = 20.0
        payload.values.fat_free_mass_kg = 40.0
        for field_name, label in (
            ("body_fat_kg", "Body fat (kg)"),
            ("body_fat_percent", "Body fat ratio (%)"),
            ("fat_free_mass_kg", "Fat free weight (kg)"),
        ):
            value = getattr(payload.values, field_name)
            payload.field_metadata[field_name] = BodyCompositionFieldMetadata(
                origin="ai_image", state="accepted", confidence=0.95,
                label=label, evidence=f"{label} {value}", suggested_value=value,
            )

        result = _validate_strict(payload)

        codes = {issue.code for issue in result.validation_issues}
        assert "body_fat_consistency_conflict" in codes
        assert "fat_free_mass_consistency_conflict" in codes

    def test_prefers_openai_provider_when_available(self):
        with patch("app.services.body_composition_image_parse_service.settings.openai_api_key", "test-openai-key"), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            return_value=_ai_parse_result(),
        ) as mock_parse, patch(
            "app.services.body_composition_image_parse_service._image_ai_available",
            return_value=True,
        ):
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=_local_ocr_payload(),
            )

        assert result.values.weight_kg == 84.5
        mock_parse.assert_called_once()

    def test_discards_ai_water_percent_and_calculates_it_from_printed_kg_values(self):
        ai_result = _ai_parse_result_with_extra_values()
        ai_result.values.body_water_percent = 99.0

        with patch("app.services.body_composition_image_parse_service.settings.openai_api_key", "test-openai-key"), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            return_value=ai_result,
        ), patch(
            "app.services.body_composition_image_parse_service._image_ai_available",
            return_value=True,
        ):
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=None,
            )

        assert result.values.body_water_kg == 43.3
        assert result.values.weight_kg == 84.5
        assert result.values.body_water_percent == 51.2
        assert "body_water_percent" not in result.ranges

    @patch("app.services.body_composition_image_parse_service._parse_with_claude_vision")
    @patch("app.services.body_composition_image_parse_service._image_ai_available", return_value=True)
    def test_prefers_ai_value_over_bad_local_conflict(self, _mock_available, mock_parse):
        mock_parse.return_value = _ai_parse_result()

        from app.services.body_composition_image_parse_service import parse_body_composition_image

        result = parse_body_composition_image(
            image_bytes=b"fake-image",
            media_type="image/jpeg",
            device_profile="tezewa_receipt_v1",
            local_ocr_result=_local_ocr_payload(),
        )

        assert result.values.weight_kg == 84.5
        assert result.values.body_fat_kg == 19.46
        assert result.values.body_fat_percent == 23.0
        assert result.values.waist_hip_ratio == 0.88
        assert result.values.target_weight_kg == 68.3
        assert result.engine in {"hybrid", "ai_assisted"}
        assert result.fallback_used is (result.engine == "hybrid")

    @patch("app.services.body_composition_image_parse_service._image_ai_available", return_value=True)
    def test_removes_stale_local_ai_unavailable_warning_when_ai_succeeds(self, _mock_available):
        stale_local = _local_ocr_payload()
        stale_local.warnings.append(
            BodyCompositionOcrWarning(
                field=None,
                message="Leitura assistida por IA indisponivel; mantivemos a leitura local com revisao manual obrigatoria.",
                severity="warning",
            )
        )

        with patch("app.services.body_composition_image_parse_service.settings.openai_api_key", "test-openai-key"), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            return_value=_ai_parse_result_with_extra_values(),
        ):
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=stale_local,
            )

        assert all("indisponivel" not in warning.message.lower() for warning in result.warnings)
        assert result.confidence > stale_local.confidence

    @patch("app.services.body_composition_image_parse_service._image_ai_available", return_value=True)
    def test_keeps_non_key_local_value_when_only_noisy_local_support_exists(self, _mock_available):
        stale_local = _local_ocr_payload()
        stale_local.values.body_water_kg = 17.7
        stale_local.warnings.append(
            BodyCompositionOcrWarning(
                field="body_water_kg",
                message="body water kg foi inferido pela ordem esperada do recibo. Revisar manualmente.",
                severity="warning",
            )
        )

        with patch("app.services.body_composition_image_parse_service.settings.openai_api_key", "test-openai-key"), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            return_value=_ai_parse_result(),
        ):
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=stale_local,
            )

        assert result.values.body_water_kg == 17.7

    def test_resolve_image_ai_provider_returns_none_without_keys(self):
        with patch("app.services.body_composition_image_parse_service.settings.openai_api_key", ""), patch(
            "app.services.body_composition_image_parse_service.settings.claude_api_key",
            "",
        ):
            from app.services.body_composition_image_parse_service import _resolve_image_ai_provider

            assert _resolve_image_ai_provider() is None

    @patch("app.services.body_composition_image_parse_service._image_ai_available", return_value=False)
    def test_returns_local_with_warning_when_assisted_read_is_disabled(self, _mock_available):
        from app.services.body_composition_image_parse_service import parse_body_composition_image

        result = parse_body_composition_image(
            image_bytes=b"fake-image",
            media_type="image/png",
            device_profile="tezewa_receipt_v1",
            local_ocr_result=_local_ocr_payload(),
        )

        assert result.engine == "local"
        assert result.fallback_used is False
        assert result.needs_review is True
        assert any("Leitura assistida por IA indisponivel" in warning.message for warning in result.warnings)

    @patch("app.services.body_composition_image_parse_service._image_ai_available", return_value=True)
    def test_classifies_exhausted_provider_quota_in_local_fallback(self, _mock_available):
        class QuotaError(RuntimeError):
            code = "insufficient_quota"
            status_code = 429

        with patch("app.services.body_composition_image_parse_service.settings.openai_api_key", "test-openai-key"), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            side_effect=QuotaError("You exceeded your current quota"),
        ):
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=_local_ocr_payload(),
            )

        quota_warning = next(item for item in result.warnings if "cota do provedor" in item.message)
        assert result.engine == "local"
        assert result.needs_review is True
        assert quota_warning.severity == "critical"


class TestImageParseRoute:
    def test_prepares_receipt_without_persisting_or_running_ocr(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner
        prepared = DocumentPreprocessingResult(
            image_bytes=b"corrected-jpeg",
            media_type="image/jpeg",
            applied=True,
            method="receipt_perspective+clahe",
            confidence=np.float32(0.91),
            source_width=1200,
            source_height=2200,
            output_width=1000,
            output_height=2100,
            quality_codes=["document_blurred"],
            quality_metrics={"sharpness_top": 44.2, "sharpness_middle": 52.1, "sharpness_bottom": 40.3},
            document_corners=[
                {"x": 0.1, "y": 0.03},
                {"x": 0.9, "y": 0.04},
                {"x": 0.88, "y": 0.97},
                {"x": 0.12, "y": 0.96},
            ],
        )

        try:
            with patch(
                "app.routers.members.get_member_or_404",
                return_value=SimpleNamespace(id=MEMBER_ID, gym_id=mock_owner.gym_id),
            ), patch(
                "app.routers.members.preprocess_receipt_image",
                return_value=prepared,
            ) as mock_prepare:
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/prepare-image",
                    files={"file": ("receipt.png", b"source-image", "image/png")},
                )

            assert response.status_code == 200
            assert response.content == b"corrected-jpeg"
            assert response.headers["cache-control"] == "no-store"
            metadata = json.loads(response.headers["x-cordex-scan-metadata"])
            assert metadata["method"] == "receipt_perspective+clahe"
            assert abs(metadata["confidence"] - 0.91) < 0.001
            assert metadata["corners"][0] == {"x": 0.1, "y": 0.03}
            assert metadata["quality_metrics"]["sharpness_bottom"] == 40.3
            assert mock_prepare.call_args.kwargs["manual_corners"] is None
        finally:
            app.dependency_overrides.clear()

    def test_prepares_receipt_with_manual_corners(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner
        corners = [
            {"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.1},
            {"x": 0.9, "y": 0.9}, {"x": 0.1, "y": 0.9},
        ]
        prepared = DocumentPreprocessingResult(
            image_bytes=b"manual-jpeg", media_type="image/jpeg", applied=True,
            method="manual_perspective+clahe", confidence=1.0,
            source_width=1000, source_height=2000, output_width=900, output_height=1800,
            document_corners=corners,
        )

        try:
            with patch(
                "app.routers.members.get_member_or_404",
                return_value=SimpleNamespace(id=MEMBER_ID, gym_id=mock_owner.gym_id),
            ), patch(
                "app.routers.members.preprocess_receipt_image",
                return_value=prepared,
            ) as mock_prepare:
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/prepare-image",
                    data={"corners": json.dumps(corners)},
                    files={"file": ("receipt.jpg", b"source-image", "image/jpeg")},
                )

            assert response.status_code == 200
            assert mock_prepare.call_args.kwargs["manual_corners"] == corners
        finally:
            app.dependency_overrides.clear()

    def test_prepare_receipt_rejects_invalid_type_and_missing_document(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner
        try:
            with patch(
                "app.routers.members.get_member_or_404",
                return_value=SimpleNamespace(id=MEMBER_ID, gym_id=mock_owner.gym_id),
            ):
                invalid_type = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/prepare-image",
                    files={"file": ("receipt.txt", b"plain", "text/plain")},
                )
                with patch("app.routers.members.preprocess_receipt_image", return_value=None):
                    missing = client.post(
                        f"/api/v1/members/{MEMBER_ID}/body-composition/prepare-image",
                        files={"file": ("receipt.jpg", b"not-a-document", "image/jpeg")},
                    )

            assert invalid_type.status_code == 415
            assert missing.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_records_capture_event_without_image_or_student_data(self, app, client, mock_owner, caplog):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner
        try:
            with patch(
                "app.routers.members.get_member_or_404",
                return_value=SimpleNamespace(id=MEMBER_ID, gym_id=mock_owner.gym_id),
            ) as member_lookup:
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/capture-event",
                    json={
                        "event": "capture_blocked",
                        "reason": "camera_moving",
                        "confidence": 0.61,
                        "quality_codes": ["bottom_blurred"],
                    },
                )

            assert response.status_code == 204
            assert response.content == b""
            assert member_lookup.call_args.kwargs["gym_id"] == mock_owner.gym_id
            assert "Bioimpedance scanner event" in caplog.text
            assert "image" not in response.headers
        finally:
            app.dependency_overrides.clear()

    def test_accepts_three_segmented_images(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch(
                "app.routers.members.get_member_or_404",
                return_value=SimpleNamespace(id=MEMBER_ID, gym_id=mock_owner.gym_id),
            ), patch(
                "app.routers.members.parse_body_composition_image",
                return_value=_ai_parse_result(),
            ) as mock_parse, patch(
                "app.routers.members.settings.body_composition_multi_image_parse_v1",
                True,
            ):
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
                    files=[
                        ("file", ("top.jpg", b"top-image", "image/jpeg")),
                        ("supplemental_files", ("middle.jpg", b"middle-image", "image/jpeg")),
                        ("supplemental_files", ("bottom.jpg", b"bottom-image", "image/jpeg")),
                    ],
                )

            assert response.status_code == 200
            supplemental = mock_parse.call_args.kwargs["supplemental_images"]
            assert [content for content, _media_type in supplemental] == [b"middle-image", b"bottom-image"]
        finally:
            app.dependency_overrides.clear()

    def test_rejects_more_than_three_images(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch(
                "app.routers.members.get_member_or_404",
                return_value=SimpleNamespace(id=MEMBER_ID, gym_id=mock_owner.gym_id),
            ), patch(
                "app.routers.members.settings.body_composition_multi_image_parse_v1",
                True,
            ):
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
                    files=[
                        ("file", ("top.jpg", b"top-image", "image/jpeg")),
                        ("supplemental_files", ("middle.jpg", b"middle-image", "image/jpeg")),
                        ("supplemental_files", ("bottom.jpg", b"bottom-image", "image/jpeg")),
                        ("supplemental_files", ("extra.jpg", b"extra-image", "image/jpeg")),
                    ],
                )

            assert response.status_code == 422
            assert "maximo tres imagens" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_requires_authentication(self, client):
        response = client.post(
            f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
            files={"file": ("receipt.jpg", b"fake-image", "image/jpeg")},
        )

        assert response.status_code == 401

    def test_respects_current_user_gym_scope(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            def _member_lookup(db, member_id, gym_id):
                assert gym_id == mock_owner.gym_id
                return SimpleNamespace(id=member_id, gym_id=gym_id)

            with patch("app.routers.members.get_member_or_404", side_effect=_member_lookup), patch(
                "app.routers.members.parse_body_composition_image",
                return_value=_ai_parse_result(),
            ):
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
                    data={"device_profile": "tezewa_receipt_v1"},
                    files={"file": ("receipt.jpg", b"fake-image", "image/jpeg")},
                )

            assert response.status_code == 200
            assert response.json()["values"]["weight_kg"] == 84.5
        finally:
            app.dependency_overrides.clear()

    def test_passes_selected_date_and_member_context_to_local_validation(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        previous = SimpleNamespace(weight_kg=78)
        mock_db = make_mock_db(scalar_returns=previous)
        member = SimpleNamespace(
            id=MEMBER_ID,
            gym_id=mock_owner.gym_id,
            birthdate=date(1986, 9, 3),
            sex_for_clinical_calculation="male",
            height_cm=180,
        )
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch("app.routers.members.get_member_or_404", return_value=member), patch(
                "app.routers.members.parse_body_composition_image",
                return_value=_ai_parse_result(),
            ) as mock_parse:
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
                    data={"device_profile": "tezewa_receipt_v1", "evaluation_date": "2026-09-03"},
                    files={"file": ("receipt.jpg", b"fake-image", "image/jpeg")},
                )

            assert response.status_code == 200
            call = mock_parse.call_args.kwargs
            assert call["evaluation_date"] == date(2026, 9, 3)
            assert call["member_birthdate"] == date(1986, 9, 3)
            assert call["member_sex"] == "male"
            assert call["member_height_cm"] == 180
            assert call["previous_weight_kg"] == 78
        finally:
            app.dependency_overrides.clear()

    def test_rejects_invalid_file_type(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch("app.routers.members.get_member_or_404", return_value=SimpleNamespace(id=MEMBER_ID, gym_id=mock_owner.gym_id)):
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
                    data={"device_profile": "tezewa_receipt_v1"},
                    files={"file": ("receipt.txt", b"not-an-image", "text/plain")},
                )

            assert response.status_code == 415
            assert "JPEG, PNG ou WEBP" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_returns_local_engine_when_image_ai_is_disabled(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch("app.routers.members.get_member_or_404", return_value=SimpleNamespace(id=MEMBER_ID, gym_id=mock_owner.gym_id)), patch(
                "app.services.body_composition_image_parse_service.settings.body_composition_image_ai_enabled",
                False,
            ):
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
                    data={
                        "device_profile": "tezewa_receipt_v1",
                        "local_ocr_result": _local_ocr_payload().model_dump_json(),
                    },
                    files={"file": ("receipt.jpg", b"fake-image", "image/jpeg")},
                )

            assert response.status_code == 200
            body = response.json()
            assert body["engine"] == "local"
            assert body["fallback_used"] is False
            assert body["values"]["weight_kg"] == 14.41
            assert any("Leitura assistida por IA indisponivel" in item["message"] for item in body["warnings"])
        finally:
            app.dependency_overrides.clear()

    def test_openai_image_ai_available_does_not_depend_on_claude_breaker(self):
        with patch("app.services.body_composition_image_parse_service.settings.body_composition_image_ai_enabled", True), patch(
            "app.services.body_composition_image_parse_service.settings.openai_api_key",
            "test-openai-key",
        ), patch(
            "app.services.body_composition_image_parse_service.claude_circuit_breaker.is_open",
            return_value=True,
        ):
            from app.services.body_composition_image_parse_service import _image_ai_available

            assert _image_ai_available("openai") is True

    def test_parse_with_openai_vision_uses_json_mode_response(self):
        captured_kwargs = {}

        mock_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"device_model":"Tezewa","values":{"weight_kg":84.5,"body_fat_kg":19.46,"body_fat_percent":23.0,"waist_hip_ratio":0.88},"ranges":{"weight_kg":{"min":61.7,"max":75.5}},"warnings":[],"needs_review":false}'
                    )
                )
            ]
        )
        mock_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: captured_kwargs.update(kwargs) or mock_response,
                )
            )
        )

        with patch("app.services.body_composition_image_parse_service._create_openai_client", return_value=mock_client):
            from app.services.body_composition_image_parse_service import _parse_with_openai_vision

            result = _parse_with_openai_vision(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=_local_ocr_payload(),
            )

        assert result.values.weight_kg == 84.5
        assert result.values.body_fat_kg == 19.46
        assert result.values.body_fat_percent == 23.0
        assert result.engine == "ai_assisted"
        assert result.fallback_used is False
        prompt = captured_kwargs["messages"][1]["content"][0]["text"]
        assert "Template obrigatorio de values" in prompt
        assert "body_water_percent" in prompt
        assert "retorne sempre null" in prompt
        assert "body_water_kg / weight_kg * 100" in prompt
        assert "target_weight_kg" in prompt
        assert "total_energy_kcal" in prompt
        assert "muscle_control_kg" in prompt
        assert "nao pare nos campos principais" in prompt
