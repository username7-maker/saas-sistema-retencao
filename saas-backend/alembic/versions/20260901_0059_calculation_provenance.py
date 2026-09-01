"""add calculation provenance and safely backfill historical assessments

Revision ID: 20260901_0059
Revises: 20260827_0058
Create Date: 2026-09-01
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "20260901_0059"
down_revision: str | None = "20260827_0058"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ORIGINS = (
    "reported",
    "schofield_hw_1985",
    "mifflin_st_jeor_1990",
    "lee_2000",
    "poortmans_2005",
    "legacy_unknown",
    "unavailable",
)
_ORIGIN_SQL = ", ".join(f"'{item}'" for item in _ORIGINS)
_MUSCLE_FIELDS = (
    "right_arm_relaxed_cm",
    "right_thigh_cm",
    "right_calf_cm",
    "skinfold_triceps_mm",
    "skinfold_thigh_mm",
    "skinfold_calf_mm",
)
_Q2 = Decimal("0.01")
_PI = Decimal(str(math.pi))


def upgrade() -> None:
    op.add_column("assessments", sa.Column("muscle_mass_origin", sa.String(length=32), nullable=True))
    op.add_column("assessments", sa.Column("basal_metabolic_rate_origin", sa.String(length=32), nullable=True))
    op.add_column("body_composition_evaluations", sa.Column("muscle_mass_origin", sa.String(length=32), nullable=True))
    op.add_column(
        "body_composition_evaluations",
        sa.Column("basal_metabolic_rate_origin", sa.String(length=32), nullable=True),
    )
    op.create_check_constraint(
        "assessment_bmr_origin_valid",
        "assessments",
        f"basal_metabolic_rate_origin IS NULL OR basal_metabolic_rate_origin IN ({_ORIGIN_SQL})",
    )
    op.create_check_constraint(
        "assessment_muscle_origin_valid",
        "assessments",
        f"muscle_mass_origin IS NULL OR muscle_mass_origin IN ({_ORIGIN_SQL})",
    )
    op.create_check_constraint(
        "bce_bmr_origin_valid",
        "body_composition_evaluations",
        f"basal_metabolic_rate_origin IS NULL OR basal_metabolic_rate_origin IN ({_ORIGIN_SQL})",
    )
    op.create_check_constraint(
        "bce_muscle_origin_valid",
        "body_composition_evaluations",
        f"muscle_mass_origin IS NULL OR muscle_mass_origin IN ({_ORIGIN_SQL})",
    )
    _backfill_assessments()
    _backfill_body_composition()
    op.alter_column("assessments", "muscle_mass_origin", nullable=False, server_default="unavailable")
    op.alter_column("assessments", "basal_metabolic_rate_origin", nullable=False, server_default="unavailable")
    op.alter_column("body_composition_evaluations", "muscle_mass_origin", nullable=False, server_default="unavailable")
    op.alter_column(
        "body_composition_evaluations",
        "basal_metabolic_rate_origin",
        nullable=False,
        server_default="unavailable",
    )


def downgrade() -> None:
    op.drop_constraint("bce_muscle_origin_valid", "body_composition_evaluations", type_="check")
    op.drop_constraint("bce_bmr_origin_valid", "body_composition_evaluations", type_="check")
    op.drop_constraint("assessment_muscle_origin_valid", "assessments", type_="check")
    op.drop_constraint("assessment_bmr_origin_valid", "assessments", type_="check")
    op.drop_column("body_composition_evaluations", "basal_metabolic_rate_origin")
    op.drop_column("body_composition_evaluations", "muscle_mass_origin")
    op.drop_column("assessments", "basal_metabolic_rate_origin")
    op.drop_column("assessments", "muscle_mass_origin")


def _backfill_assessments() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    assessments = sa.Table("assessments", metadata, autoload_with=bind)
    audit_logs = sa.Table("audit_logs", metadata, autoload_with=bind)
    rows = bind.execute(sa.select(assessments)).mappings()
    for row in rows:
        snapshot = dict(row.get("anthropometry_snapshot_json") or {})
        inputs = dict(snapshot.get("inputs") or {})
        age = _integer(row.get("age_used_for_formula") or inputs.get("age_used_for_formula"))
        sex = row.get("sex_used_for_formula") or inputs.get("sex_used_for_formula")
        height = row.get("height_used_for_formula") or row.get("height_cm") or inputs.get("height_used_for_formula")
        weight = row.get("weight_used_for_formula") or row.get("weight_kg") or inputs.get("weight_used_for_formula")
        generated = (
            row.get("assessment_method") == "manual_anthropometry"
            and row.get("record_origin") == "cordex"
            and str(row.get("formula_version") or "").startswith("anthropometry-v")
        )
        updates: dict[str, Any] = {}
        changes: dict[str, dict[str, Any]] = {}

        old_bmr = row.get("basal_metabolic_rate")
        if generated:
            bmr, bmr_origin = _bmr(sex=sex, age=age, height_cm=height, weight_kg=weight)
            if bmr is not None:
                updates["basal_metabolic_rate"] = bmr
                updates["basal_metabolic_rate_origin"] = bmr_origin
                if not _same(old_bmr, bmr):
                    changes["basal_metabolic_rate"] = _change(old_bmr, bmr)
            elif old_bmr is not None and age is not None and age < 3:
                updates["basal_metabolic_rate"] = None
                updates["basal_metabolic_rate_origin"] = "unavailable"
                changes["basal_metabolic_rate"] = _change(old_bmr, None)
            else:
                updates["basal_metabolic_rate_origin"] = "legacy_unknown" if old_bmr is not None else "unavailable"
        else:
            updates["basal_metabolic_rate_origin"] = "legacy_unknown" if old_bmr is not None else "unavailable"

        old_muscle = row.get("muscle_mass_kg")
        known_lee = "lee-2000" in str(row.get("formula_version") or "")
        muscle_requested = bool(inputs.get("calculate_muscle_mass")) or known_lee
        ethnicity = inputs.get("anthropometry_ethnicity")
        measurements = snapshot.get("measurements") if isinstance(snapshot.get("measurements"), Mapping) else {}
        muscle, muscle_origin, alerts = _muscle(
            sex=sex,
            age=age,
            height_cm=height,
            weight_kg=weight,
            ethnicity=ethnicity,
            values=measurements,
        )
        if generated and muscle_requested and muscle is not None:
            updates["muscle_mass_kg"] = muscle
            updates["muscle_mass_origin"] = muscle_origin
            if not _same(old_muscle, muscle):
                changes["muscle_mass_kg"] = _change(old_muscle, muscle)
        elif generated and known_lee and age is not None and age < 18:
            updates["muscle_mass_kg"] = None
            updates["muscle_mass_origin"] = "unavailable"
            if old_muscle is not None:
                changes["muscle_mass_kg"] = _change(old_muscle, None)
        elif old_muscle is not None:
            updates["muscle_mass_origin"] = "lee_2000" if generated and known_lee and age is not None and age >= 18 else "legacy_unknown"
        else:
            updates["muscle_mass_origin"] = "unavailable"

        if generated:
            snapshot = _updated_snapshot(
                snapshot,
                bmr=updates.get("basal_metabolic_rate", old_bmr),
                bmr_origin=updates["basal_metabolic_rate_origin"],
                muscle=updates.get("muscle_mass_kg", old_muscle),
                muscle_origin=updates["muscle_mass_origin"],
                alerts=alerts,
                changes=changes,
            )
            updates["anthropometry_snapshot_json"] = snapshot
            updates["calculation_hash"] = snapshot["calculation_hash"]

        bind.execute(sa.update(assessments).where(assessments.c.id == row["id"]).values(**updates))
        if changes:
            _insert_audit(bind, audit_logs, row, entity="assessment", changes=changes)


def _backfill_body_composition() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    evaluations = sa.Table("body_composition_evaluations", metadata, autoload_with=bind)
    audit_logs = sa.Table("audit_logs", metadata, autoload_with=bind)
    rows = bind.execute(sa.select(evaluations)).mappings()
    for row in rows:
        updates: dict[str, Any] = {}
        changes: dict[str, dict[str, Any]] = {}
        alerts = list(row.get("data_quality_flags_json") or [])
        old_bmr = row.get("basal_metabolic_rate_kcal")
        if old_bmr is not None:
            updates["basal_metabolic_rate_origin"] = "legacy_unknown"
        else:
            bmr, bmr_origin = _bmr(
                sex=row.get("sex"),
                age=_integer(row.get("age_years")),
                height_cm=row.get("height_cm"),
                weight_kg=row.get("weight_kg"),
            )
            updates["basal_metabolic_rate_kcal"] = bmr
            updates["basal_metabolic_rate_origin"] = bmr_origin
            if bmr is not None:
                changes["basal_metabolic_rate_kcal"] = _change(None, bmr)

        old_muscle = row.get("muscle_mass_kg")
        if old_muscle is not None:
            updates["muscle_mass_origin"] = "legacy_unknown"
        else:
            muscle, muscle_origin, muscle_alerts = _muscle(
                sex=row.get("sex"),
                age=_integer(row.get("age_years")),
                height_cm=row.get("height_cm"),
                weight_kg=row.get("weight_kg"),
                ethnicity=row.get("anthropometry_ethnicity"),
                values=row,
            )
            updates["muscle_mass_kg"] = muscle
            updates["muscle_mass_origin"] = muscle_origin
            alerts.extend(muscle_alerts)
            if muscle is not None:
                changes["muscle_mass_kg"] = _change(None, muscle)
        updates["data_quality_flags_json"] = list(dict.fromkeys(alerts))
        bind.execute(sa.update(evaluations).where(evaluations.c.id == row["id"]).values(**updates))
        if changes:
            _insert_audit(bind, audit_logs, row, entity="body_composition_evaluation", changes=changes)


def _bmr(*, sex: Any, age: int | None, height_cm: Any, weight_kg: Any) -> tuple[Decimal | None, str]:
    height = _decimal(height_cm)
    weight = _decimal(weight_kg)
    if sex not in {"male", "female"} or age is None or height is None or weight is None or height <= 0 or weight <= 0:
        return None, "unavailable"
    height_m = height / Decimal("100")
    if 3 <= age < 10:
        value = (
            Decimal("19.59") * weight + Decimal("130.3") * height_m + Decimal("414.9")
            if sex == "male"
            else Decimal("16.969") * weight + Decimal("161.8") * height_m + Decimal("371.2")
        )
        return _round2(value), "schofield_hw_1985"
    if 10 <= age <= 18:
        value = (
            Decimal("16.25") * weight + Decimal("137.2") * height_m + Decimal("515.5")
            if sex == "male"
            else Decimal("8.365") * weight + Decimal("465") * height_m + Decimal("200")
        )
        return _round2(value), "schofield_hw_1985"
    if age >= 19:
        offset = Decimal("5") if sex == "male" else Decimal("-161")
        return _round2(Decimal("10") * weight + Decimal("6.25") * height - Decimal("5") * age + offset), "mifflin_st_jeor_1990"
    return None, "unavailable"


def _muscle(
    *,
    sex: Any,
    age: int | None,
    height_cm: Any,
    weight_kg: Any,
    ethnicity: Any,
    values: Mapping[str, Any],
) -> tuple[Decimal | None, str, list[str]]:
    height = _decimal(height_cm)
    ethnicity = str(ethnicity or "").strip().lower()
    if sex not in {"male", "female"} or age is None or height is None or height <= 0:
        return None, "unavailable", ["muscle_inputs_incomplete"]
    if 7 <= age <= 16 and ethnicity != "white":
        return None, "unavailable", ["muscle_measurement_required", "poortmans_population_not_validated"]
    if age < 18 and not 7 <= age <= 16:
        return None, "unavailable", ["muscle_measurement_required", "muscle_age_outside_validated_range"]
    if age >= 18 and ethnicity not in {"white", "black", "asian"}:
        return None, "unavailable", ["muscle_measurement_required", "lee_ethnicity_required"]
    corrected = _corrected(values)
    if corrected is None:
        return None, "unavailable", ["muscle_measurement_required", "muscle_measurements_incomplete"]
    height_m = height / Decimal("100")
    sex_value = Decimal("1") if sex == "male" else Decimal("0")
    if 7 <= age <= 16:
        value = height_m * (
            Decimal("0.0064") * corrected["arm"] ** 2
            + Decimal("0.0032") * corrected["thigh"] ** 2
            + Decimal("0.0015") * corrected["calf"] ** 2
        ) + Decimal("2.56") * sex_value + Decimal("0.136") * age
        return _round2(value), "poortmans_2005", []
    ethnicity_value = {"asian": Decimal("-2.0"), "black": Decimal("1.1"), "white": Decimal("0")}[ethnicity]
    value = (
        height_m
        * (
            Decimal("0.00744") * corrected["arm"] ** 2
            + Decimal("0.00088") * corrected["thigh"] ** 2
            + Decimal("0.00441") * corrected["calf"] ** 2
        )
        + Decimal("2.4") * sex_value
        - Decimal("0.048") * age
        + ethnicity_value
        + Decimal("7.8")
    )
    alerts: list[str] = []
    height_m_value = height / Decimal("100")
    weight = _decimal(weight_kg)
    if weight is not None and weight / (height_m_value * height_m_value) >= Decimal("30"):
        alerts.append("lee_bmi_extrapolation")
    return _round2(value), "lee_2000", alerts


def _corrected(values: Mapping[str, Any]) -> dict[str, Decimal] | None:
    parsed = {field: _measurement(values.get(field)) for field in _MUSCLE_FIELDS}
    if any(value is None or value <= 0 for value in parsed.values()):
        return None
    corrected = {
        "arm": parsed["right_arm_relaxed_cm"] - _PI * parsed["skinfold_triceps_mm"] / Decimal("10"),
        "thigh": parsed["right_thigh_cm"] - _PI * parsed["skinfold_thigh_mm"] / Decimal("10"),
        "calf": parsed["right_calf_cm"] - _PI * parsed["skinfold_calf_mm"] / Decimal("10"),
    }
    return corrected if min(corrected.values()) > 0 else None


def _measurement(value: Any) -> Decimal | None:
    if isinstance(value, Mapping):
        for key in ("decimal_value", "consolidated_value", "value"):
            if value.get(key) is not None:
                return _decimal(value.get(key))
        return None
    return _decimal(value)


def _updated_snapshot(
    snapshot: dict[str, Any],
    *,
    bmr: Any,
    bmr_origin: str,
    muscle: Any,
    muscle_origin: str,
    alerts: list[str],
    changes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    updated = dict(snapshot)
    updated["schema_version"] = "anthropometry_snapshot_v3"
    origins = dict(updated.get("indicator_origins") or {})
    origins["basal_metabolic_rate"] = bmr_origin
    origins["muscle_mass_kg"] = muscle_origin
    updated["indicator_origins"] = origins
    results = dict(updated.get("results") or {})
    results["basal_metabolic_rate"] = str(bmr) if bmr is not None else None
    results["muscle_mass_kg"] = str(muscle) if muscle is not None else None
    updated["results"] = results
    updated["flags"] = list(dict.fromkeys([flag for flag in updated.get("flags") or [] if flag != "lee_age_extrapolation"] + alerts))
    updated["historical_recalculation"] = {
        "revision": revision,
        "applied_at": datetime.now(tz=UTC).isoformat(),
        "changes": changes,
    }
    updated.pop("calculation_hash", None)
    digest = hashlib.sha256(
        json.dumps(updated, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()
    updated["calculation_hash"] = digest
    return updated


def _insert_audit(bind: Any, audit_logs: sa.Table, row: Mapping[str, Any], *, entity: str, changes: dict[str, Any]) -> None:
    bind.execute(
        sa.insert(audit_logs).values(
            id=uuid.uuid4(),
            gym_id=row["gym_id"],
            user_id=None,
            member_id=row.get("member_id"),
            action="calculation_origin_historical_backfill",
            entity=entity,
            entity_id=row["id"],
            details={"revision": revision, "changes": changes},
            ip_address=None,
            user_agent=None,
        )
    )


def _change(before: Any, after: Any) -> dict[str, Any]:
    return {
        "before": str(before) if before is not None else None,
        "after": str(after) if after is not None else None,
    }


def _same(left: Any, right: Any) -> bool:
    left_decimal = _decimal(left)
    right_decimal = _decimal(right)
    if left_decimal is None or right_decimal is None:
        return left is None and right is None
    return abs(left_decimal - right_decimal) < Decimal("0.005")


def _integer(value: Any) -> int | None:
    number = _decimal(value)
    return int(number) if number is not None else None


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _round2(value: Decimal) -> Decimal:
    return value.quantize(_Q2, rounding=ROUND_HALF_UP)
