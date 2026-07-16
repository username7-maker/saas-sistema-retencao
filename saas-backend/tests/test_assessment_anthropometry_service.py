import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services import assessment_anthropometry_service as service


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _measure(values, unit, *, side="right", reason=None):
    return {
        "attempts": values,
        "unit": unit,
        "side": side,
        "side_exception_reason": reason,
    }


def _petroski_payload(**overrides):
    payload = {
        "assessment_date": datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc),
        "sex_for_formula": "male",
        "age_years": 22,
        "measurement_protocol": "petroski_1995_male_18_66",
        "measurements": {
            "height_cm": _measure([177.0, 177.0], "cm", side="not_applicable"),
            "weight_kg": _measure([73.6, 73.6], "kg", side="not_applicable"),
            "skinfold_triceps_mm": _measure([9.0, 9.0], "mm"),
            "skinfold_subscapular_mm": _measure([12.0, 12.0], "mm"),
            "skinfold_suprailiac_mm": _measure([7.0, 7.0], "mm"),
            "skinfold_calf_mm": _measure([10.0, 10.0], "mm"),
            "waist_cm": _measure([80.0, 80.0], "cm"),
            "hip_cm": _measure([96.0, 96.0], "cm"),
        },
        "observations": "Avaliacao manual sem balanca de bioimpedancia.",
    }
    payload.update(overrides)
    return payload


def test_preview_computes_supported_protocol_without_bioimpedance() -> None:
    preview = service.preview_anthropometric_assessment(_petroski_payload())

    assert preview["assessment_method"] == "manual_anthropometry"
    assert preview["record_origin"] == "cordex"
    assert preview["measurement_policy_version"] == "anthropometry-v1"
    assert preview["protocol"]["key"] == "petroski_1995_male_18_66"
    assert preview["results"]["body_fat_pct"] == Decimal("12.49")
    assert preview["results"]["fat_mass_kg"] == Decimal("9.19")
    assert preview["results"]["lean_mass_kg"] == Decimal("64.41")
    assert preview["results"]["bmi"] == Decimal("23.49")
    assert preview["results"]["waist_hip_ratio"] == Decimal("0.83")
    assert preview["results"]["basal_metabolic_rate"] == Decimal("1737.25")
    assert preview["results"]["muscle_mass_kg"] is None
    assert preview["indicator_origins"]["muscle_mass_kg"] == "unavailable"
    assert preview["indicator_origins"]["body_fat_pct"] == "anthropometry_calculated"
    assert len(preview["calculation_hash"]) == 64


def test_measurement_policy_requires_third_attempt_when_tolerance_is_exceeded() -> None:
    payload = _petroski_payload()
    payload["measurements"]["skinfold_triceps_mm"] = _measure([9.0, 11.0], "mm")

    with pytest.raises(HTTPException) as exc:
        service.preview_anthropometric_assessment(payload)

    assert exc.value.status_code == 422
    assert "third_attempt_required" in str(exc.value.detail)


def test_measurement_policy_uses_median_when_third_attempt_is_present() -> None:
    payload = _petroski_payload()
    payload["measurements"]["skinfold_triceps_mm"] = _measure([8.0, 14.0, 9.0], "mm")

    preview = service.preview_anthropometric_assessment(payload)

    consolidated = preview["snapshot"]["measurements"]["skinfold_triceps_mm"]["consolidated_value"]
    assert consolidated == "9.0"
    assert preview["snapshot"]["measurements"]["skinfold_triceps_mm"]["consolidation"] == "median"


def test_measurement_policy_requires_reason_for_left_side_exception() -> None:
    payload = _petroski_payload()
    payload["measurements"]["skinfold_calf_mm"] = _measure([10.0, 10.0], "mm", side="left")

    with pytest.raises(HTTPException) as exc:
        service.preview_anthropometric_assessment(payload)

    assert exc.value.status_code == 422
    assert "side_exception_reason_required" in str(exc.value.detail)


def test_manual_only_protocol_blocks_confirmation() -> None:
    payload = _petroski_payload(measurement_protocol="weltman_1988_male_obese_20_60")
    payload["measurements"]["waist_cm"] = _measure([98.0, 98.0], "cm")

    with pytest.raises(HTTPException) as exc:
        service.preview_anthropometric_assessment(payload)

    assert exc.value.status_code == 422
    assert "anthropometry_protocol_manual_only" in str(exc.value.detail)


def test_anthropometry_ladder_creates_d8_d14_d75_d90_without_superseding() -> None:
    db = MagicMock()
    db.scalar.return_value = None
    member = SimpleNamespace(id=MEMBER_ID, gym_id=GYM_ID, full_name="Aluno Teste", preferred_shift="morning")
    assessment = SimpleNamespace(
        id=uuid.uuid4(),
        gym_id=GYM_ID,
        assessment_number=4,
        assessment_date=datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc),
        next_assessment_due=date(2026, 10, 14),
    )

    tasks = service.ensure_anthropometry_ladder_tasks(
        db,
        member=member,
        assessment=assessment,
        evaluator_id=USER_ID,
        commit=False,
    )

    assert [task.extra_data["day_offset"] for task in tasks] == [8, 14, 75, 90]
    assert tasks[2].due_date == assessment.assessment_date + timedelta(days=75)
    assert tasks[3].due_date.date() == assessment.next_assessment_due
    assert tasks[2].extra_data["technical_ladder_step"] == "anthropometry_rebooking_contact_d75"
    assert all(task.extra_data["assessment_source_type"] == "manual_anthropometry" for task in tasks)
    assert db.add.call_count == 4
    db.flush.assert_called_once()


def test_create_manual_anthropometry_is_idempotent_by_gym_and_key(monkeypatch) -> None:
    idempotency_key = uuid.uuid4()
    created_tasks = []
    member = SimpleNamespace(
        id=MEMBER_ID,
        gym_id=GYM_ID,
        full_name="Aluno Teste",
        birthdate=date(2004, 7, 16),
        sex_for_clinical_calculation="male",
        height_cm=Decimal("177.0"),
        extra_data={},
        deleted_at=None,
    )
    db = MagicMock()
    db.scalar.side_effect = [None, member, 3]
    monkeypatch.setattr(
        service,
        "ensure_anthropometry_ladder_tasks",
        lambda *args, **kwargs: created_tasks.append(kwargs["assessment"]) or [],
    )

    assessment = service.create_anthropometric_assessment(
        db,
        member_id=MEMBER_ID,
        evaluator_id=USER_ID,
        gym_id=GYM_ID,
        payload=_petroski_payload(age_years=None),
        idempotency_key=idempotency_key,
        commit=False,
    )

    assert assessment.assessment_method == "manual_anthropometry"
    assert assessment.record_origin == "cordex"
    assert assessment.assessment_number == 4
    assert assessment.idempotency_key == idempotency_key
    assert assessment.calculation_hash == assessment.anthropometry_snapshot_json["calculation_hash"]
    assert assessment.sex_used_for_formula == "male"
    assert assessment.age_used_for_formula == 22
    assert assessment.height_used_for_formula == Decimal("177.00")
    assert assessment.weight_used_for_formula == Decimal("73.60")
    assert len(created_tasks) == 1
    db.flush.assert_called()


def test_repeated_idempotency_key_returns_existing_assessment(monkeypatch) -> None:
    existing = SimpleNamespace(
        id=uuid.uuid4(),
        calculation_hash=service.preview_anthropometric_assessment(_petroski_payload())["calculation_hash"],
        anthropometry_snapshot_json={},
    )
    db = MagicMock()
    db.scalar.return_value = existing
    monkeypatch.setattr(service, "ensure_anthropometry_ladder_tasks", MagicMock())

    result = service.create_anthropometric_assessment(
        db,
        member_id=MEMBER_ID,
        evaluator_id=USER_ID,
        gym_id=GYM_ID,
        payload=_petroski_payload(),
        idempotency_key=uuid.uuid4(),
        commit=False,
    )

    assert result is existing
    service.ensure_anthropometry_ladder_tasks.assert_not_called()
    db.add.assert_not_called()
