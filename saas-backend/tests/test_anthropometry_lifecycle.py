from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models import TaskStatus
from app.services.assessment_anthropometry_service import (
    delete_anthropometric_assessment,
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
