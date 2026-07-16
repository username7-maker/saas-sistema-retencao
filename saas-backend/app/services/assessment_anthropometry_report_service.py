from __future__ import annotations

from datetime import UTC, date, datetime, time, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Sequence

from app.services.body_composition_anthropometry_service import (
    ANTHROPOMETRY_CALCULATION_FIELDS,
    ANTHROPOMETRY_EVOLUTION_FIELDS,
)
from app.services.body_composition_report_service import (
    build_body_composition_premium_pdf_payload,
    build_body_composition_report_read,
)
from app.services.premium_report_service import PremiumReportPayload, render_premium_report_pdf


def build_anthropometric_report_payload(
    member: Any,
    assessment: Any,
    *,
    history: Sequence[Any] | None = None,
    generated_by: str | None = None,
) -> PremiumReportPayload:
    protocol_key = getattr(assessment, "measurement_protocol", None)
    formula_version = getattr(assessment, "formula_version", None)
    current = _assessment_to_report_evaluation(assessment)
    raw_history = list(history or [])
    if not any(str(getattr(item, "id", "")) == str(getattr(assessment, "id", "")) for item in raw_history):
        raw_history.append(assessment)
    report_history = [_assessment_to_report_evaluation(item) for item in raw_history]
    report = build_body_composition_report_read(member, current, history=report_history)
    report.score_breakdown = [
        item.model_copy(
            update={
                "label": "Massa livre / FFMI",
                "description": "Usa massa livre de gordura e altura. Nao representa massa muscular medida.",
            }
        )
        if item.key == "muscle"
        else item
        for item in report.score_breakdown
    ]
    _omit_unavailable_report_metrics(report)
    report.methodological_note = (
        "Avaliacao antropometrica sem bioimpedancia. Os resultados sao estimativas por protocolo manual; "
        "massa muscular, agua corporal, gordura visceral, massa ossea e idade metabolica nao foram inferidas."
    )

    payload = build_body_composition_premium_pdf_payload(report, technical=False)
    parameters = dict(payload.parameters)
    parameters.update(
        {
            "protocol": protocol_key,
            "formula_version": formula_version,
            "assessment_method": getattr(assessment, "assessment_method", "manual_anthropometry"),
            "record_origin": getattr(assessment, "record_origin", "cordex"),
            "client_footer_note": (
                "Relatorio antropometrico informativo. Valores exclusivos da bioimpedancia permanecem indisponiveis; "
                "massa livre de gordura nao e massa muscular."
            ),
            "composition_detail_subtitle": (
                "Valores separados por origem: medidas manuais, protocolo antropometrico e calculos derivados."
            ),
        }
    )
    assessed_at = _assessment_datetime(assessment)
    payload.title = "Relatorio premium de avaliacao antropometrica"
    payload.subtitle = f"{getattr(member, 'full_name', 'Aluno')} - {assessed_at.strftime('%d/%m/%Y %H:%M')}"
    payload.generated_by = generated_by or payload.generated_by
    payload.version = "anthropometry-premium-v1"
    payload.parameters = parameters
    payload.cover_summary = (
        "Relatorio gerado a partir de medidas manuais e protocolo antropometrico. "
        "Campos exclusivos da bioimpedancia permanecem indisponiveis."
    )
    payload.footer_note = (
        "Massa livre de gordura nao e massa muscular. Nenhuma metrica exclusiva da bioimpedancia foi inferida."
    )
    return payload


def generate_anthropometric_assessment_pdf(
    member: Any,
    assessment: Any,
    *,
    history: Sequence[Any] | None = None,
    generated_by: str | None = None,
) -> tuple[bytes, str]:
    payload = build_anthropometric_report_payload(member, assessment, history=history, generated_by=generated_by)
    pdf = render_premium_report_pdf(payload)
    assessed_at = getattr(assessment, "assessment_date", None)
    if isinstance(assessed_at, datetime):
        date_slug = assessed_at.date().isoformat()
    else:
        date_slug = datetime.now(tz=timezone.utc).date().isoformat()
    member_slug = _slug(getattr(member, "full_name", "aluno"))
    filename = f"avaliacao_antropometrica_{member_slug}_{date_slug}_{getattr(assessment, 'id')}.pdf"
    return pdf, filename


def _assessment_to_report_evaluation(assessment: Any) -> SimpleNamespace:
    measured_at = _assessment_datetime(assessment)
    values = _snapshot_measurement_values(assessment)
    attributes: dict[str, Any] = {
        "id": getattr(assessment, "id", None),
        "measured_at": measured_at,
        "evaluation_date": measured_at.date(),
        "reviewed_manually": True,
        "parsing_confidence": None,
        "ocr_confidence": None,
        "data_quality_flags_json": [],
        "sex": getattr(assessment, "sex_used_for_formula", None),
        "age_years": getattr(assessment, "age_used_for_formula", None),
        "height_cm": getattr(assessment, "height_cm", None),
        "weight_kg": getattr(assessment, "weight_kg", None),
        "bmi": getattr(assessment, "bmi", None),
        "body_fat_used_percent": getattr(assessment, "body_fat_pct", None),
        "body_fat_anthropometric_percent": getattr(assessment, "body_fat_pct", None),
        "body_fat_used_source": "anthropometry",
        "preferred_body_fat_source": "anthropometry",
        "body_fat_method": "skinfold_protocol",
        "body_fat_confidence": "high",
        "body_fat_range_min": None,
        "body_fat_range_max": None,
        "body_fat_manual_review_required": False,
        "body_fat_manual_review_completed": True,
        "fat_mass_estimated_kg": getattr(assessment, "fat_mass_kg", None),
        "lean_mass_estimated_kg": getattr(assessment, "lean_mass_kg", None),
        "lean_mass_kg": getattr(assessment, "lean_mass_kg", None),
        "fat_free_mass_kg": getattr(assessment, "lean_mass_kg", None),
        "muscle_mass_kg": None,
        "skeletal_muscle_kg": None,
        "visceral_fat_level": None,
        "body_water_kg": None,
        "body_water_percent": None,
        "protein_kg": None,
        "inorganic_salt_kg": None,
        "waist_hip_ratio": getattr(assessment, "waist_hip_ratio", None),
        "basal_metabolic_rate_kcal": getattr(assessment, "basal_metabolic_rate", None),
        "physical_age": None,
        "health_score": None,
        "target_weight_kg": None,
        "weight_control_kg": None,
        "fat_control_kg": None,
        "muscle_control_kg": None,
        "notes": getattr(assessment, "observations", None),
        "measured_ranges_json": {},
    }
    for field in ANTHROPOMETRY_CALCULATION_FIELDS + ANTHROPOMETRY_EVOLUTION_FIELDS:
        value = values.get(field)
        if value is not None:
            attributes[field] = value
    return SimpleNamespace(**attributes)


def _omit_unavailable_report_metrics(report: Any) -> None:
    unavailable_keys = {
        "muscle_mass_kg",
        "skeletal_muscle_kg",
        "visceral_fat_level",
        "body_water_kg",
        "body_water_percent",
        "protein_kg",
        "inorganic_salt_kg",
        "physical_age",
        "health_score",
        "target_weight_kg",
        "weight_control_kg",
        "fat_control_kg",
        "muscle_control_kg",
    }

    def keep_metric(metric: Any) -> bool:
        return getattr(metric, "key", None) not in unavailable_keys and getattr(metric, "value", None) is not None

    report.primary_cards = [metric for metric in report.primary_cards if keep_metric(metric)]
    report.composition_metrics = [metric for metric in report.composition_metrics if keep_metric(metric)]
    report.muscle_fat_metrics = [metric for metric in report.muscle_fat_metrics if keep_metric(metric)]
    report.risk_metrics = [metric for metric in report.risk_metrics if keep_metric(metric)]
    report.goal_metrics = [metric for metric in report.goal_metrics if keep_metric(metric)]
    report.comparison_rows = [
        row
        for row in report.comparison_rows
        if getattr(row, "key", None) not in unavailable_keys
        and (getattr(row, "current_value", None) is not None or getattr(row, "previous_value", None) is not None)
    ]
    report.score_breakdown = [item for item in report.score_breakdown if getattr(item, "key", None) != "visceral_fat"]
    report.history_series = [
        series
        for series in report.history_series
        if getattr(series, "key", None) not in unavailable_keys and any(point.value is not None for point in series.points)
    ]


def _assessment_datetime(assessment: Any) -> datetime:
    assessed_at = getattr(assessment, "assessment_date", None)
    if isinstance(assessed_at, datetime):
        return assessed_at if assessed_at.tzinfo else assessed_at.replace(tzinfo=UTC)
    if isinstance(assessed_at, date):
        return datetime.combine(assessed_at, time(hour=12), tzinfo=UTC)
    return datetime.now(tz=timezone.utc)


def _snapshot_measurement_values(assessment: Any) -> dict[str, float]:
    values: dict[str, float] = {}
    snapshot = getattr(assessment, "anthropometry_snapshot_json", None) or {}
    measurements = snapshot.get("measurements", {}) if isinstance(snapshot, dict) else {}
    if isinstance(measurements, dict):
        for field, item in measurements.items():
            if not isinstance(item, dict):
                continue
            value = _to_float(item.get("consolidated_value"))
            if value is not None:
                values[str(field)] = value
    extra_data = getattr(assessment, "extra_data", None) or {}
    perimetry = extra_data.get("perimetry_evolution", {}) if isinstance(extra_data, dict) else {}
    if isinstance(perimetry, dict):
        for field, value in perimetry.items():
            parsed = _to_float(value)
            if parsed is not None:
                values[str(field)] = parsed

    column_fallbacks = {
        "waist_cm": getattr(assessment, "waist_cm", None),
        "hip_cm": getattr(assessment, "hip_cm", None),
        "chest_cm": getattr(assessment, "chest_cm", None),
        "right_arm_relaxed_cm": getattr(assessment, "arm_cm", None),
        "right_thigh_cm": getattr(assessment, "thigh_cm", None),
    }
    for field, value in column_fallbacks.items():
        parsed = _to_float(value)
        if parsed is not None and field not in values:
            values[field] = parsed
    return values


def _format_metric(value: Any, unit: str) -> str:
    number = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"{number}{f' {unit}' if unit else ''}"


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _field_label(field: str) -> str:
    labels = {
        "height_cm": "Altura",
        "weight_kg": "Peso",
        "waist_cm": "Cintura",
        "hip_cm": "Quadril",
        "abdomen_cm": "Abdomen",
        "skinfold_triceps_mm": "Dobra tricipital",
        "skinfold_subscapular_mm": "Dobra subescapular",
        "skinfold_suprailiac_mm": "Dobra suprailiaca",
        "skinfold_calf_mm": "Dobra panturrilha",
    }
    return labels.get(field, field.replace("_", " ").title())


def _metric_label(key: str) -> str:
    labels = {
        "muscle_mass_kg": "Massa muscular",
        "body_water_percent": "Agua corporal",
        "visceral_fat_level": "Gordura visceral",
        "bone_mass_kg": "Massa ossea",
        "metabolic_age": "Idade metabolica/fisica",
        "total_energy_expenditure": "Gasto energetico total",
        "target_weight_kg": "Peso-alvo",
        "body_fat_pct": "Gordura corporal",
        "lean_mass_kg": "Massa livre de gordura",
    }
    return labels.get(key, key.replace("_", " ").title())


def _origin_label(value: Any) -> str:
    return {
        "manual_measured": "Dado informado/medido manualmente",
        "anthropometry_calculated": "Calculado por antropometria",
        "bioimpedance_measured": "Medido por bioimpedancia",
        "manual_override": "Alterado manualmente",
        "unavailable": "Indisponivel nesta modalidade",
    }.get(str(value), str(value))


def _slug(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    compact = "-".join(part for part in normalized.split("-") if part)
    return compact[:80] or "aluno"
