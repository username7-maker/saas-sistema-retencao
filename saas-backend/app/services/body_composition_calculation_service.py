from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

ORIGIN_REPORTED = "reported"
ORIGIN_SCHOFIELD = "schofield_hw_1985"
ORIGIN_MIFFLIN = "mifflin_st_jeor_1990"
ORIGIN_LEE = "lee_2000"
ORIGIN_POORTMANS = "poortmans_2005"
ORIGIN_LEGACY_UNKNOWN = "legacy_unknown"
ORIGIN_UNAVAILABLE = "unavailable"

CALCULATION_ORIGINS = frozenset(
    {
        ORIGIN_REPORTED,
        ORIGIN_SCHOFIELD,
        ORIGIN_MIFFLIN,
        ORIGIN_LEE,
        ORIGIN_POORTMANS,
        ORIGIN_LEGACY_UNKNOWN,
        ORIGIN_UNAVAILABLE,
    }
)

MUSCLE_REQUIRED_FIELDS = (
    "right_arm_relaxed_cm",
    "right_thigh_cm",
    "right_calf_cm",
    "skinfold_triceps_mm",
    "skinfold_thigh_mm",
    "skinfold_calf_mm",
)

_Q2 = Decimal("0.01")
_PI = Decimal(str(math.pi))


@dataclass(frozen=True, slots=True)
class CalculationResult:
    value: Decimal | None
    origin: str
    formula: str | None
    formula_version: str | None
    age_range: str | None
    alerts: tuple[str, ...] = ()
    corrected_circumferences_cm: Mapping[str, Decimal] | None = None


def calculate_basal_metabolic_rate(
    *,
    sex: Any,
    age_years: Any,
    height_cm: Any,
    weight_kg: Any,
) -> CalculationResult:
    normalized_sex = _normalize_sex(sex)
    age = _decimal(age_years)
    height = _decimal(height_cm)
    weight = _decimal(weight_kg)
    if normalized_sex is None or age is None or height is None or weight is None:
        return _unavailable(alert="bmr_inputs_incomplete")
    if age <= 0 or height <= 0 or weight <= 0:
        return _unavailable(alert="bmr_inputs_invalid")

    height_m = height / Decimal("100")
    if Decimal("3") <= age < Decimal("10"):
        if normalized_sex == "male":
            value = Decimal("19.59") * weight + Decimal("130.3") * height_m + Decimal("414.9")
            formula = "19.59*weight_kg+130.3*height_m+414.9"
        else:
            value = Decimal("16.969") * weight + Decimal("161.8") * height_m + Decimal("371.2")
            formula = "16.969*weight_kg+161.8*height_m+371.2"
        return CalculationResult(
            value=_round2(value),
            origin=ORIGIN_SCHOFIELD,
            formula=formula,
            formula_version="schofield-hw-1985-3-9-v1",
            age_range="3-<10",
        )

    if Decimal("10") <= age <= Decimal("18"):
        if normalized_sex == "male":
            value = Decimal("16.25") * weight + Decimal("137.2") * height_m + Decimal("515.5")
            formula = "16.25*weight_kg+137.2*height_m+515.5"
        else:
            value = Decimal("8.365") * weight + Decimal("465") * height_m + Decimal("200")
            formula = "8.365*weight_kg+465*height_m+200"
        return CalculationResult(
            value=_round2(value),
            origin=ORIGIN_SCHOFIELD,
            formula=formula,
            formula_version="schofield-hw-1985-10-18-v1",
            age_range="10-18",
        )

    if age >= Decimal("19"):
        sex_constant = Decimal("5") if normalized_sex == "male" else Decimal("-161")
        value = Decimal("10") * weight + Decimal("6.25") * height - Decimal("5") * age + sex_constant
        return CalculationResult(
            value=_round2(value),
            origin=ORIGIN_MIFFLIN,
            formula="10*weight_kg+6.25*height_cm-5*age_years+sex_constant",
            formula_version="mifflin-st-jeor-1990-v1",
            age_range="19+",
        )

    return _unavailable(alert="bmr_age_outside_supported_range")


def calculate_muscle_mass(
    *,
    sex: Any,
    age_years: Any,
    height_cm: Any,
    ethnicity: Any,
    measurements: Mapping[str, Any] | None,
    weight_kg: Any = None,
) -> CalculationResult:
    normalized_sex = _normalize_sex(sex)
    normalized_ethnicity = str(ethnicity or "").strip().lower() or None
    age = _decimal(age_years)
    height = _decimal(height_cm)
    if normalized_sex is None or age is None or height is None or age <= 0 or height <= 0:
        return _unavailable(alert="muscle_inputs_incomplete")

    if Decimal("7") <= age <= Decimal("16"):
        if normalized_ethnicity != "white":
            return _unavailable(
                alert="muscle_measurement_required",
                extra_alert="poortmans_population_not_validated",
                age_range="7-16-white",
            )
        corrected, error = _corrected_circumferences(measurements)
        if corrected is None:
            return _unavailable(
                alert="muscle_measurement_required",
                extra_alert=error or "muscle_measurements_incomplete",
                age_range="7-16-white",
            )
        sex_coefficient = Decimal("1") if normalized_sex == "male" else Decimal("0")
        height_m = height / Decimal("100")
        value = height_m * (
            Decimal("0.0064") * corrected["arm"] ** 2
            + Decimal("0.0032") * corrected["thigh"] ** 2
            + Decimal("0.0015") * corrected["calf"] ** 2
        ) + Decimal("2.56") * sex_coefficient + Decimal("0.136") * age
        if value <= 0:
            return _unavailable(alert="muscle_calculation_invalid", age_range="7-16-white")
        return CalculationResult(
            value=_round2(value),
            origin=ORIGIN_POORTMANS,
            formula="height_m*(0.0064*CAG^2+0.0032*CTG^2+0.0015*CCG^2)+2.56*sex+0.136*age",
            formula_version="poortmans-2005-v1",
            age_range="7-16-white",
            corrected_circumferences_cm=corrected,
        )

    if age >= Decimal("18"):
        if normalized_ethnicity not in {"white", "black", "asian"}:
            return _unavailable(
                alert="muscle_measurement_required",
                extra_alert="lee_ethnicity_required",
                age_range="18+",
            )
        corrected, error = _corrected_circumferences(measurements)
        if corrected is None:
            return _unavailable(
                alert="muscle_measurement_required",
                extra_alert=error or "muscle_measurements_incomplete",
                age_range="18+",
            )
        sex_coefficient = Decimal("1") if normalized_sex == "male" else Decimal("0")
        ethnicity_coefficient = {
            "asian": Decimal("-2.0"),
            "black": Decimal("1.1"),
            "white": Decimal("0"),
        }[normalized_ethnicity]
        height_m = height / Decimal("100")
        value = (
            height_m
            * (
                Decimal("0.00744") * corrected["arm"] ** 2
                + Decimal("0.00088") * corrected["thigh"] ** 2
                + Decimal("0.00441") * corrected["calf"] ** 2
            )
            + Decimal("2.4") * sex_coefficient
            - Decimal("0.048") * age
            + ethnicity_coefficient
            + Decimal("7.8")
        )
        if value <= 0:
            return _unavailable(alert="muscle_calculation_invalid", age_range="18+")
        alerts: list[str] = []
        bmi = _bmi(height_cm=height, weight_kg=weight_kg)
        if bmi is not None and bmi >= Decimal("30"):
            alerts.append("lee_bmi_extrapolation")
        return CalculationResult(
            value=_round2(value),
            origin=ORIGIN_LEE,
            formula=(
                "height_m*(0.00744*CAG^2+0.00088*CTG^2+0.00441*CCG^2)"
                "+2.4*sex-0.048*age+ethnicity+7.8"
            ),
            formula_version="lee-2000-complete-v1",
            age_range="18+",
            alerts=tuple(alerts),
            corrected_circumferences_cm=corrected,
        )

    return _unavailable(
        alert="muscle_measurement_required",
        extra_alert="muscle_age_outside_validated_range",
        age_range="7-16-white-or-18+",
    )


def calculation_metadata(result: CalculationResult) -> dict[str, Any]:
    return {
        "origin": result.origin,
        "formula": result.formula,
        "formula_version": result.formula_version,
        "age_range": result.age_range,
        "alerts": list(result.alerts),
        "result": str(result.value) if result.value is not None else None,
        "corrected_circumferences_cm": (
            {key: str(value) for key, value in result.corrected_circumferences_cm.items()}
            if result.corrected_circumferences_cm
            else None
        ),
    }


def _corrected_circumferences(
    measurements: Mapping[str, Any] | None,
) -> tuple[dict[str, Decimal] | None, str | None]:
    values = measurements or {}
    parsed: dict[str, Decimal] = {}
    for field in MUSCLE_REQUIRED_FIELDS:
        value = _measurement_decimal(values.get(field))
        if value is None or value <= 0:
            return None, "muscle_measurements_incomplete"
        parsed[field] = value
    corrected = {
        "arm": parsed["right_arm_relaxed_cm"] - _PI * parsed["skinfold_triceps_mm"] / Decimal("10"),
        "thigh": parsed["right_thigh_cm"] - _PI * parsed["skinfold_thigh_mm"] / Decimal("10"),
        "calf": parsed["right_calf_cm"] - _PI * parsed["skinfold_calf_mm"] / Decimal("10"),
    }
    if min(corrected.values()) <= 0:
        return None, "corrected_circumference_invalid"
    return corrected, None


def _measurement_decimal(value: Any) -> Decimal | None:
    if isinstance(value, Mapping):
        for key in ("decimal_value", "consolidated_value", "value"):
            if value.get(key) is not None:
                return _decimal(value.get(key))
        return None
    return _decimal(value)


def _bmi(*, height_cm: Any, weight_kg: Any) -> Decimal | None:
    height = _decimal(height_cm)
    weight = _decimal(weight_kg)
    if height is None or weight is None or height <= 0 or weight <= 0:
        return None
    height_m = height / Decimal("100")
    return weight / (height_m * height_m)


def _normalize_sex(value: Any) -> str | None:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in {"male", "female"} else None


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _round2(value: Decimal) -> Decimal:
    return value.quantize(_Q2, rounding=ROUND_HALF_UP)


def _unavailable(
    *,
    alert: str,
    extra_alert: str | None = None,
    age_range: str | None = None,
) -> CalculationResult:
    alerts = tuple(item for item in (alert, extra_alert) if item)
    return CalculationResult(
        value=None,
        origin=ORIGIN_UNAVAILABLE,
        formula=None,
        formula_version=None,
        age_range=age_range,
        alerts=alerts,
    )
