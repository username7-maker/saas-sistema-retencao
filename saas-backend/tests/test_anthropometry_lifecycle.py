from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models import TaskStatus
from app.services.assessment_anthropometry_service import (
    delete_anthropometric_assessment,
    preview_anthropometric_assessment,
    update_anthropometric_assessment,
)


def _measurement(value: float, unit: str, side: str = "right") -> dict:
    return {"attempts": [value, value], "unit": unit, "side": side}


def _payload() -> dict:
    return {
        "assessment_date": "2026-09-01T13:00:00Z",
        "sex_for_formula": "male",
        "age_years": 30,
        "measurement_protocol": "jackson_pollock_3_male_18_61",
        "anthropometry_ethnicity": "white",
        "anthropometry_maturity": None,
        "calculate_muscle_mass": False,
        "measurements": {
            "height_cm": _measurement(180, "cm", "not_applicable"),
            "weight_kg": _measurement(82, "kg", "not_applicable"),
            "skinfold_chest_mm": _measurement(10, "mm"),
            "skinfold_abdominal_mm": _measurement(18, "mm"),
            "skinfold_thigh_mm": _measurement(15, "mm"),
            "waist_cm": _measurement(84, "cm"),
            "hip_cm": _measurement(96, "cm"),
        },
        "observations": "Medidas revisadas.",
    }


def test_anthropometry_preview_rejects_future_assessment_date() -> None:
    payload = _payload()
    payload["assessment_date"] = "2999-01-01T12:00:00Z"

    with pytest.raises(HTTPException) as error:
        preview_anthropometric_assessment(payload)

    assert error.value.status_code == 422
    assert error.value.detail["code"] == "assessment_date_future"


def test_weltman_preview_identifies_invalid_circumference_with_unit_and_limits():
    payload = _payload()
    payload["measurement_protocol"] = "weltman_1988_male_obese_20_60"
    payload["measurements"]["waist_cm"] = _measurement(21.5, "cm")
    payload["measurements"]["abdomen_cm"] = _measurement(34.2, "cm")
    with pytest.raises(HTTPException) as error:
        preview_anthropometric_assessment(payload)
    assert error.value.detail == {
        "code": "implausible_measurement", "field": "waist_cm",
        "minimum": "30.0", "maximum": "250.0", "unit": "cm",
    }


def test_anthropometry_naive_date_uses_sao_paulo_and_age_at_assessment() -> None:
    payload = _payload()
    payload["assessment_date"] = "2026-09-23T23:30:00"
    payload["age_years"] = None
    member = SimpleNamespace(birthdate=date(2000, 9, 24), sex_for_clinical_calculation="male", height_cm=180)

    preview = preview_anthropometric_assessment(payload, member=member)

    assert preview["snapshot"]["assessment_date"] == "2026-09-24T02:30:00+00:00"
    assert preview["snapshot"]["inputs"]["age_used_for_formula"] == 25


def _assessment(*, updated_at: datetime) -> SimpleNamespace:
    assessment_id = uuid4()
    return SimpleNamespace(
        id=assessment_id,
        gym_id=uuid4(),
        member_id=uuid4(),
        evaluator_id=uuid4(),
        assessment_number=3,
        assessment_date=datetime(2026, 8, 1, 13, tzinfo=UTC),
        next_assessment_due=None,
        updated_at=updated_at,
        assessment_method="manual_anthropometry",
        measurement_protocol="legacy",
        formula_version="legacy",
        calculation_hash="old-hash",
        observations="Anterior",
        anthropometry_snapshot_json={"inputs": {}, "measurements": {}, "results": {}},
        extra_data={},
        deleted_at=None,
    )


def _member(assessment: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        id=assessment.member_id,
        gym_id=assessment.gym_id,
        full_name="Aluno Teste",
        birthdate=None,
        height_cm=None,
        preferred_shift=None,
        deleted_at=None,
    )


def test_update_recalculates_results_and_creates_manual_actuar_follow_up():
    updated_at = datetime(2026, 9, 1, 12, tzinfo=UTC)
    assessment = _assessment(updated_at=updated_at)
    member = _member(assessment)
    db = MagicMock()
    db.scalar.side_effect = [member, assessment, None, None, None, None, None]

    updated, before = update_anthropometric_assessment(
        db,
        member_id=member.id,
        assessment_id=assessment.id,
        editor_id=assessment.evaluator_id,
        gym_id=member.gym_id,
        payload=_payload(),
        expected_updated_at=updated_at,
        commit=False,
    )

    assert before["calculation_hash"] == "old-hash"
    assert updated.calculation_hash != "old-hash"
    assert updated.weight_kg == 82
    assert updated.basal_metabolic_rate_origin == "mifflin_st_jeor_1990"
    assert updated.extra_data["actuar_sync"]["sync_status"] == "manual_sync_required"
    added_tasks = [call.args[0] for call in db.add.call_args_list]
    assert any(task.extra_data.get("source") == "anthropometry_actuar_update_required" for task in added_tasks)


def test_update_persists_naive_assessment_time_in_utc_with_local_due_date() -> None:
    updated_at = datetime(2026, 9, 1, 12, tzinfo=UTC)
    assessment = _assessment(updated_at=updated_at)
    member = _member(assessment)
    db = MagicMock()
    db.scalar.side_effect = [member, assessment, None, None, None, None, None]
    payload = _payload()
    payload["assessment_date"] = "2026-09-23T23:30:00"

    updated, _ = update_anthropometric_assessment(
        db, member_id=member.id, assessment_id=assessment.id,
        editor_id=assessment.evaluator_id, gym_id=member.gym_id,
        payload=payload, expected_updated_at=updated_at, commit=False,
    )

    assert updated.assessment_date == datetime(2026, 9, 24, 2, 30, tzinfo=UTC)
    assert updated.next_assessment_due == date(2026, 12, 22)


def test_update_rejects_stale_editor_with_conflict():
    assessment = _assessment(updated_at=datetime(2026, 9, 1, 12, tzinfo=UTC))
    member = _member(assessment)
    db = MagicMock()
    db.scalar.side_effect = [member, assessment]

    with pytest.raises(HTTPException) as exc_info:
        update_anthropometric_assessment(
            db,
            member_id=member.id,
            assessment_id=assessment.id,
            editor_id=assessment.evaluator_id,
            gym_id=member.gym_id,
            payload=_payload(),
            expected_updated_at=datetime(2026, 9, 1, 11, tzinfo=UTC),
            commit=False,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "anthropometry_edit_conflict"
    db.add.assert_not_called()


def test_delete_is_recoverable_and_only_cancels_open_generated_tasks():
    assessment = _assessment(updated_at=datetime(2026, 9, 1, 12, tzinfo=UTC))
    member = _member(assessment)
    generated = SimpleNamespace(
        status=TaskStatus.TODO,
        kanban_column="todo",
        completed_at=None,
        extra_data={"source": "anthropometry_feedback_d14"},
    )
    completed = SimpleNamespace(
        status=TaskStatus.DONE,
        kanban_column="done",
        completed_at=datetime(2026, 8, 20, tzinfo=UTC),
        extra_data={"source": "anthropometry_training_delivery_check_d8"},
    )
    unrelated = SimpleNamespace(
        status=TaskStatus.TODO,
        kanban_column="todo",
        completed_at=None,
        extra_data={"source": "manual_customer_task"},
    )
    db = MagicMock()
    db.scalar.side_effect = [member, assessment, None]
    db.scalars.return_value.all.return_value = [generated, completed, unrelated]

    deleted, before = delete_anthropometric_assessment(
        db,
        member_id=member.id,
        assessment_id=assessment.id,
        deleted_by_user_id=assessment.evaluator_id,
        gym_id=member.gym_id,
        commit=False,
    )

    assert before["calculation_hash"] == "old-hash"
    assert deleted.deleted_at is not None
    assert deleted.extra_data["deleted_reason"] == "user_requested_recoverable_delete"
    assert generated.status == TaskStatus.CANCELLED
    assert completed.status == TaskStatus.DONE
    assert unrelated.status == TaskStatus.TODO
    added_tasks = [call.args[0] for call in db.add.call_args_list]
    assert any(task.extra_data.get("source") == "anthropometry_actuar_delete_required" for task in added_tasks)
