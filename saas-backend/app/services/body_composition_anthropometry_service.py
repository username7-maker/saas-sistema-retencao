from __future__ import annotations

import math
from typing import Any


ANTHROPOMETRY_CALCULATION_FIELDS = (
    "neck_cm",
    "waist_cm",
    "abdomen_cm",
    "hip_cm",
)

ANTHROPOMETRY_EVOLUTION_FIELDS = (
    "shoulders_cm",
    "chest_cm",
    "right_arm_relaxed_cm",
    "left_arm_relaxed_cm",
    "right_arm_flexed_cm",
    "left_arm_flexed_cm",
    "right_thigh_cm",
    "left_thigh_cm",
    "right_calf_cm",
    "left_calf_cm",
)

ANTHROPOMETRY_FIELDS = ANTHROPOMETRY_CALCULATION_FIELDS + ANTHROPOMETRY_EVOLUTION_FIELDS

QUALITY_FLAGS = {
    "anthropometry_incomplete",
    "body_fat_source_divergence",
    "anthropometry_needs_review",
    "anthropometry_inconsistent",
    "impossible_measurement_value",
    "abnormal_measurement_variation",
}

_CM_TO_INCHES = 1 / 2.54

_MEASUREMENT_RANGES = {
    "height_cm": (90.0, 250.0),
    "weight_kg": (20.0, 250.0),
    "neck_cm": (15.0, 80.0),
    "waist_cm": (30.0, 250.0),
    "abdomen_cm": (30.0, 250.0),
    "hip_cm": (35.0, 260.0),
    "shoulders_cm": (40.0, 260.0),
    "chest_cm": (35.0, 250.0),
    "right_arm_relaxed_cm": (10.0, 90.0),
    "left_arm_relaxed_cm": (10.0, 90.0),
    "right_arm_flexed_cm": (10.0, 95.0),
    "left_arm_flexed_cm": (10.0, 95.0),
    "right_thigh_cm": (20.0, 130.0),
    "left_thigh_cm": (20.0, 130.0),
    "right_calf_cm": (15.0, 90.0),
    "left_calf_cm": (15.0, 90.0),
}


def resolve_body_fat_fields(values: dict[str, Any], previous_values: Any | None = None) -> dict[str, Any]:
    data = dict(values)
    flags: list[str] = list(data.get("data_quality_flags_json") or [])

    bioimpedance_percent = _first_float(data.get("body_fat_bioimpedance_percent"), data.get("body_fat_percent"))
    if bioimpedance_percent is not None:
        data["body_fat_bioimpedance_percent"] = _round_percent(bioimpedance_percent)

    anthropometry = calculate_anthropometric_body_fat(data, previous_values=previous_values)
    flags.extend(anthropometry["flags"])

    anthropometric_percent = anthropometry["body_fat_percent"]
    if anthropometric_percent is not None:
        data["body_fat_anthropometric_percent"] = anthropometric_percent

    if (
        bioimpedance_percent is not None
        and anthropometric_percent is not None
        and abs(bioimpedance_percent - anthropometric_percent) > 6
    ):
        flags.append("body_fat_source_divergence")

    preferred = data.get("preferred_body_fat_source")
    if preferred not in {"bioimpedance", "anthropometry", "geneos_composite", "manual_override"}:
        preferred = "geneos_composite" if anthropometry["has_minimum_measurements"] else "bioimpedance"
    data["preferred_body_fat_source"] = preferred

    manual_override = _to_float(data.get("body_fat_manual_override_percent"))
    review_completed = bool(data.get("body_fat_manual_review_completed") or data.get("anthropometry_review_completed"))
    used_percent: float | None = None
    used_source: str | None = None
    method: str | None = None
    confidence: str | None = anthropometry["confidence"]
    range_min: float | None = anthropometry["range_min"]
    range_max: float | None = anthropometry["range_max"]

    if preferred == "manual_override" and manual_override is not None:
        used_percent = _round_percent(manual_override)
        used_source = "manual_override"
        method = "manual_override"
        confidence = "medium"
        range_min = None
        range_max = None
    elif preferred in {"anthropometry", "geneos_composite"}:
        if anthropometric_percent is None:
            flags.append("anthropometry_incomplete")
        elif confidence == "inconsistent" and not review_completed:
            flags.append("anthropometry_inconsistent")
            flags.append("anthropometry_needs_review")
        else:
            used_percent = anthropometric_percent
            used_source = "anthropometry"
            method = "geneos_composite" if preferred == "geneos_composite" and anthropometry["navy_percent"] is not None and anthropometry["rfm_percent"] is not None else anthropometry["method"]

    if used_percent is None and bioimpedance_percent is not None:
        used_percent = _round_percent(bioimpedance_percent)
        used_source = "bioimpedance"
        method = "legacy_bioimpedance"
        if preferred == "bioimpedance":
            confidence = None
            range_min = None
            range_max = None

    if used_percent is None and anthropometric_percent is not None and confidence != "inconsistent":
        used_percent = anthropometric_percent
        used_source = "anthropometry"
        method = anthropometry["method"]

    data["body_fat_used_percent"] = used_percent
    data["body_fat_used_source"] = used_source
    data["body_fat_method"] = method
    data["body_fat_confidence"] = confidence if used_source == "anthropometry" else None
    data["body_fat_range_min"] = range_min if used_source == "anthropometry" else None
    data["body_fat_range_max"] = range_max if used_source == "anthropometry" else None

    weight_kg = _to_float(data.get("weight_kg"))
    if weight_kg is not None and weight_kg > 0 and used_percent is not None:
        fat_mass = round(weight_kg * used_percent / 100, 2)
        data["fat_mass_estimated_kg"] = fat_mass
        data["lean_mass_estimated_kg"] = round(weight_kg - fat_mass, 2)

    if preferred == "manual_override" and manual_override is not None:
        data["measurement_source"] = "manual_override"
        data.setdefault("measurement_protocol", "manual_override")
    elif _has_any_anthropometry(data):
        data["measurement_source"] = "composite_geneos" if preferred == "geneos_composite" else "manual_anthropometry"
        data.setdefault("measurement_protocol", "geneos_composite")
    elif bioimpedance_percent is not None:
        data["measurement_source"] = "bioimpedance"

    review_required = any(
        flag in set(flags)
        for flag in (
            "anthropometry_needs_review",
            "anthropometry_inconsistent",
            "impossible_measurement_value",
            "abnormal_measurement_variation",
        )
    )
    if review_required:
        data["body_fat_manual_review_required"] = True
        data["needs_review"] = True
    else:
        data["body_fat_manual_review_required"] = bool(data.get("body_fat_manual_review_required", False))

    data["data_quality_flags_json"] = list(dict.fromkeys(flags))
    return data


def calculate_anthropometric_body_fat(values: Any, previous_values: Any | None = None) -> dict[str, Any]:
    flags: list[str] = []
    sex = _read(values, "sex")
    height_cm = _read_float(values, "height_cm")
    weight_kg = _read_float(values, "weight_kg")
    neck_cm = _read_float(values, "neck_cm")
    waist_cm = _read_float(values, "waist_cm")
    abdomen_cm = _read_float(values, "abdomen_cm")
    hip_cm = _read_float(values, "hip_cm")

    flags.extend(_validate_measurement_ranges(values))
    if _has_any_anthropometry(values) and sex not in {"male", "female"}:
        flags.append("anthropometry_incomplete")

    navy_percent = _calculate_navy(
        sex=sex,
        height_cm=height_cm,
        neck_cm=neck_cm,
        waist_cm=waist_cm,
        abdomen_cm=abdomen_cm,
        hip_cm=hip_cm,
        flags=flags,
    )
    rfm_percent = _calculate_rfm(
        sex=sex,
        height_cm=height_cm,
        waist_cm=waist_cm,
        abdomen_cm=abdomen_cm,
        flags=flags,
    )

    method = None
    selected_percent = None
    confidence = None
    if navy_percent is not None and rfm_percent is not None:
        diff = abs(navy_percent - rfm_percent)
        method = "geneos_composite"
        selected_percent = navy_percent
        if diff <= 2:
            confidence = "high"
        elif diff <= 3:
            confidence = "medium_high"
        elif diff <= 6:
            confidence = "medium"
        else:
            confidence = "inconsistent"
            flags.append("anthropometry_inconsistent")
            flags.append("anthropometry_needs_review")
    elif navy_percent is not None:
        method = "navy_circumference"
        selected_percent = navy_percent
        confidence = "medium"
    elif rfm_percent is not None:
        method = "rfm"
        selected_percent = rfm_percent
        confidence = "low"
    elif _has_any_anthropometry(values):
        flags.append("anthropometry_incomplete")

    if selected_percent is not None and not 2 <= selected_percent <= 75:
        flags.append("impossible_measurement_value")
        selected_percent = None
        confidence = None

    flags.extend(_detect_abnormal_variation(values, previous_values))
    range_min, range_max = _estimated_range(selected_percent, confidence)
    has_minimum = navy_percent is not None or rfm_percent is not None
    fat_mass = None
    lean_mass = None
    if weight_kg is not None and selected_percent is not None:
        fat_mass = round(weight_kg * selected_percent / 100, 2)
        lean_mass = round(weight_kg - fat_mass, 2)

    return {
        "body_fat_percent": _round_percent(selected_percent),
        "navy_percent": _round_percent(navy_percent),
        "rfm_percent": _round_percent(rfm_percent),
        "method": method,
        "confidence": confidence,
        "range_min": range_min,
        "range_max": range_max,
        "fat_mass_kg": fat_mass,
        "lean_mass_kg": lean_mass,
        "flags": list(dict.fromkeys(flags)),
        "has_minimum_measurements": has_minimum,
    }


def _calculate_navy(
    *,
    sex: Any,
    height_cm: float | None,
    neck_cm: float | None,
    waist_cm: float | None,
    abdomen_cm: float | None,
    hip_cm: float | None,
    flags: list[str],
) -> float | None:
    if sex not in {"male", "female"} or height_cm is None or neck_cm is None:
        return None
    height_in = height_cm * _CM_TO_INCHES
    neck_in = neck_cm * _CM_TO_INCHES
    if height_in <= 0 or neck_in <= 0:
        flags.append("impossible_measurement_value")
        return None

    if sex == "male":
        torso_cm = abdomen_cm if abdomen_cm is not None else waist_cm
        if torso_cm is None:
            return None
        torso_in = torso_cm * _CM_TO_INCHES
        if torso_in <= neck_in:
            flags.append("impossible_measurement_value")
            return None
        return 86.010 * math.log10(torso_in - neck_in) - 70.041 * math.log10(height_in) + 36.76

    if waist_cm is None or hip_cm is None:
        if waist_cm is None and abdomen_cm is not None:
            flags.append("anthropometry_incomplete")
        return None
    waist_in = waist_cm * _CM_TO_INCHES
    hip_in = hip_cm * _CM_TO_INCHES
    sum_in = waist_in + hip_in - neck_in
    if sum_in <= 0:
        flags.append("impossible_measurement_value")
        return None
    return 163.205 * math.log10(sum_in) - 97.684 * math.log10(height_in) - 78.387


def _calculate_rfm(
    *,
    sex: Any,
    height_cm: float | None,
    waist_cm: float | None,
    abdomen_cm: float | None,
    flags: list[str],
) -> float | None:
    if sex not in {"male", "female"} or height_cm is None:
        return None
    circumference = waist_cm
    if circumference is None and sex == "male":
        circumference = abdomen_cm
    if circumference is None:
        return None
    if circumference <= 0 or height_cm <= 0:
        flags.append("impossible_measurement_value")
        return None
    base = 64 if sex == "male" else 76
    return base - 20 * (height_cm / circumference)


def _validate_measurement_ranges(values: Any) -> list[str]:
    for key, (minimum, maximum) in _MEASUREMENT_RANGES.items():
        value = _read_float(values, key)
        if value is not None and not minimum <= value <= maximum:
            return ["impossible_measurement_value"]
    return []


def _detect_abnormal_variation(values: Any, previous_values: Any | None) -> list[str]:
    if previous_values is None:
        return []
    checks = (
        ("waist_cm", 8.0),
        ("abdomen_cm", 8.0),
        ("neck_cm", 4.0),
        ("body_fat_used_percent", 6.0),
    )
    for key, threshold in checks:
        current = _read_float(values, key)
        previous = _read_float(previous_values, key)
        if current is not None and previous is not None and abs(current - previous) > threshold:
            return ["abnormal_measurement_variation"]
    return []


def _estimated_range(value: float | None, confidence: str | None) -> tuple[float | None, float | None]:
    if value is None or confidence is None or confidence == "inconsistent":
        return None, None
    margin = {
        "high": 1.5,
        "medium_high": 2.0,
        "medium": 3.0,
        "low": 4.0,
    }.get(confidence, 4.0)
    return _round_percent(max(0, value - margin)), _round_percent(min(75, value + margin))


def _has_any_anthropometry(values: Any) -> bool:
    return any(_read_float(values, field) is not None for field in ANTHROPOMETRY_FIELDS)


def _read(values: Any, key: str) -> Any:
    if values is None:
        return None
    if isinstance(values, dict):
        return values.get(key)
    return getattr(values, key, None)


def _read_float(values: Any, key: str) -> float | None:
    return _to_float(_read(values, key))


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_float(*values: Any) -> float | None:
    for value in values:
        number = _to_float(value)
        if number is not None:
            return number
    return None


def _round_percent(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None
