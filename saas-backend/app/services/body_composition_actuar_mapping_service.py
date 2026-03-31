from __future__ import annotations

from typing import Any

from app.models import BodyCompositionEvaluation, Member


def build_body_composition_canonical_payload(member: Member, evaluation: BodyCompositionEvaluation) -> dict[str, Any]:
    measured_at = evaluation.evaluation_date.isoformat()
    weight_kg = _to_float(getattr(evaluation, "weight_kg", None))
    bmi = _to_float(getattr(evaluation, "bmi", None))
    return {
        "evaluation_id": str(evaluation.id),
        "member_id": str(member.id),
        "measured_at": measured_at,
        "weight_kg": weight_kg,
        "height_cm": _derive_height_cm(weight_kg, bmi),
        "body_fat_pct": _to_float(getattr(evaluation, "body_fat_percent", None)),
        "muscle_mass_kg": _to_float(getattr(evaluation, "skeletal_muscle_kg", None)) or _to_float(getattr(evaluation, "muscle_mass_kg", None)),
        "lean_mass_kg": _to_float(getattr(evaluation, "fat_free_mass_kg", None)) or _to_float(getattr(evaluation, "lean_mass_kg", None)),
        "body_water_pct": _to_float(getattr(evaluation, "body_water_percent", None)),
        "bmi": bmi,
        "bmr_kcal": _to_float(getattr(evaluation, "basal_metabolic_rate_kcal", None)),
        "visceral_fat": _to_float(getattr(evaluation, "visceral_fat_level", None)),
        "circumference_fields": _build_circumference_fields(evaluation),
        "notes": getattr(evaluation, "notes", None),
        "source_device": getattr(evaluation, "device_model", None) or getattr(evaluation, "device_profile", None),
        "operator_name": None,
    }


def build_actuar_field_mapping(
    member: Member,
    evaluation: BodyCompositionEvaluation,
) -> dict[str, Any]:
    payload = build_body_composition_canonical_payload(member, evaluation)
    mappings = [
        _mapping("weight_kg", "weight", payload["weight_kg"], "critical_direct", required=True),
        _mapping("height_cm", "height_cm", payload["height_cm"], "critical_derived", required=True),
        _mapping("body_fat_pct", "body_fat_percent", payload["body_fat_pct"], "critical_direct", required=True),
        _mapping("muscle_mass_kg", "muscle_mass_kg", payload["muscle_mass_kg"], "critical_direct", required=True),
        _mapping("lean_mass_kg", "lean_mass_kg", payload["lean_mass_kg"], "non_critical_direct"),
        _mapping("bmi", "bmi", payload["bmi"], "non_critical_direct"),
        _mapping("evaluation_date", None, payload["measured_at"], "text_note_only"),
        _mapping("body_water_pct", "body_water_percent", payload["body_water_pct"], "non_critical_direct"),
        _mapping("bmr_kcal", None, payload["bmr_kcal"], "unsupported", supported=False),
        _mapping("visceral_fat", None, payload["visceral_fat"], "unsupported", supported=False),
        _mapping("notes", "notes", payload["notes"], "text_note_only", supported=True),
    ]
    critical_fields = [item for item in mappings if item["classification"].startswith("critical")]
    non_critical_fields = [item for item in mappings if not item["classification"].startswith("critical")]
    missing_critical_fields = [item["field"] for item in critical_fields if item["required"] and _is_missing(item["value"])]
    return {
        "payload": payload,
        "mapped_fields": mappings,
        "critical_fields": critical_fields,
        "non_critical_fields": non_critical_fields,
        "missing_critical_fields": missing_critical_fields,
    }


def build_manual_sync_summary(member: Member, evaluation: BodyCompositionEvaluation) -> dict[str, Any]:
    mapping = build_actuar_field_mapping(member, evaluation)
    summary_lines = [
        f"Aluno: {member.full_name}",
        f"Data da avaliacao: {evaluation.evaluation_date.isoformat()}",
    ]
    for item in mapping["critical_fields"]:
        label = item["actuar_field"] or item["field"]
        value = "-" if _is_missing(item["value"]) else item["value"]
        summary_lines.append(f"{label}: {value}")
    return {
        "critical_fields": mapping["critical_fields"],
        "summary_text": "\n".join(summary_lines),
    }


def _build_circumference_fields(evaluation: BodyCompositionEvaluation) -> dict[str, Any] | None:
    measured_ranges_json = getattr(evaluation, "measured_ranges_json", None)
    if not measured_ranges_json:
        return None
    return {
        key: value
        for key, value in measured_ranges_json.items()
        if isinstance(value, dict)
    } or None


def _mapping(
    field: str,
    actuar_field: str | None,
    value: Any,
    classification: str,
    *,
    required: bool = False,
    supported: bool = True,
) -> dict[str, Any]:
    return {
        "field": field,
        "actuar_field": actuar_field,
        "value": value,
        "classification": classification,
        "required": required,
        "supported": supported,
    }


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _derive_height_cm(weight_kg: float | None, bmi: float | None) -> int | None:
    if weight_kg is None or bmi is None or weight_kg <= 0 or bmi <= 0:
        return None
    height_m = (weight_kg / bmi) ** 0.5
    if height_m <= 0:
        return None
    return round(height_m * 100)
