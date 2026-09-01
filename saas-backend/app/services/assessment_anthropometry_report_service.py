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
    CALCULATION_ORIGIN_LABELS,
    body_composition_origin_label,
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
    has_muscle_mass = getattr(assessment, "muscle_mass_kg", None) is not None
    if not has_muscle_mass:
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
    _omit_unavailable_report_metrics(report, has_muscle_mass=has_muscle_mass)
    muscle_origin = _assessment_metric_origin(
        assessment,
        origin_field="muscle_mass_origin",
        value_field="muscle_mass_kg",
    )
    bmr_origin = _assessment_metric_origin(
        assessment,
        origin_field="basal_metabolic_rate_origin",
        value_field="basal_metabolic_rate",
    )
    extrapolation_flags = _lee_extrapolation_flags(assessment) if muscle_origin == "lee_2000" else []
    muscle_note = _muscle_methodological_note(muscle_origin, has_value=has_muscle_mass)
    bmr_note = _bmr_methodological_note(bmr_origin)
    extrapolation_note = (
        " O resultado de Lee e uma extrapolacao fora da populacao adulta nao obesa da validacao original."
        if extrapolation_flags
        else ""
    )
    report.methodological_note = (
        "Avaliacao antropometrica sem bioimpedancia. Os resultados sao estimativas por protocolo manual."
        f"{muscle_note}{bmr_note}{extrapolation_note} Massa muscular esqueletica, massa livre de gordura e massa magra sao conceitos distintos."
        " Agua corporal, gordura visceral, massa ossea e idade metabolica nao foram inferidas."
    )

    payload = build_body_composition_premium_pdf_payload(report, technical=False)
    parameters = dict(payload.parameters)
    parameters.update(
        {
            "protocol": protocol_key,
            "formula_version": formula_version,
            "assessment_method": getattr(assessment, "assessment_method", "manual_anthropometry"),
            "record_origin": getattr(assessment, "record_origin", "cordex"),
            "muscle_mass_origin": muscle_origin,
            "muscle_mass_origin_label": body_composition_origin_label(
                muscle_origin,
                metric_key="muscle_mass_kg",
            ),
            "muscle_mass_formula": _origin_formula_name(muscle_origin),
            "muscle_mass_extrapolation_flags": extrapolation_flags,
            "basal_metabolic_rate_origin": bmr_origin,
            "basal_metabolic_rate_origin_label": body_composition_origin_label(
                bmr_origin,
                metric_key="basal_metabolic_rate_kcal",
            ),
            "basal_metabolic_rate_formula": _origin_formula_name(bmr_origin),
            "methodological_note": report.methodological_note,
            "client_footer_note": (
                "Relatorio antropometrico informativo. A origem de TMB e massa muscular aparece junto de cada indicador; "
                "massa livre de gordura continua sendo um indicador diferente."
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
    payload.version = "anthropometry-premium-v2"
    payload.parameters = parameters
    payload.cover_summary = (
        "Relatorio gerado a partir de medidas manuais e protocolo antropometrico. "
        + (_muscle_cover_summary(muscle_origin) if has_muscle_mass else "Massa muscular requer medicao valida. ")
        + "Campos exclusivos da bioimpedancia permanecem indisponiveis."
    )
    payload.footer_note = (
        "Massa muscular esqueletica, massa livre de gordura e massa magra sao indicadores distintos. "
        "Nenhuma metrica exclusiva da bioimpedancia foi inferida."
    )
    _apply_anthropometry_metric_source_labels(payload)
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
        "muscle_mass_kg": getattr(assessment, "muscle_mass_kg", None),
        "muscle_mass_origin": _assessment_metric_origin(
            assessment,
            origin_field="muscle_mass_origin",
            value_field="muscle_mass_kg",
        ),
        "skeletal_muscle_kg": None,
        "visceral_fat_level": None,
        "body_water_kg": None,
        "body_water_percent": None,
        "protein_kg": None,
        "inorganic_salt_kg": None,
        "waist_hip_ratio": getattr(assessment, "waist_hip_ratio", None),
        "basal_metabolic_rate_kcal": getattr(assessment, "basal_metabolic_rate", None),
        "basal_metabolic_rate_origin": _assessment_metric_origin(
            assessment,
            origin_field="basal_metabolic_rate_origin",
            value_field="basal_metabolic_rate",
        ),
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


def _omit_unavailable_report_metrics(report: Any, *, has_muscle_mass: bool) -> None:
    unavailable_keys = {
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
    if not has_muscle_mass:
        unavailable_keys.add("muscle_mass_kg")

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


def _apply_anthropometry_metric_source_labels(payload: PremiumReportPayload) -> None:
    report = payload.parameters.get("report")
    if not isinstance(report, dict):
        return
    source_by_key = {
        "weight_kg": ("measurements", "Informado/manual"),
        "height_cm": ("measurements", "Informado/manual"),
        "body_fat_used_percent": ("measurements", "Medidas/protocolo"),
        "fat_mass_estimated_kg": ("measurements", "Medidas/protocolo"),
        "lean_mass_estimated_kg": ("measurements", "Calculo"),
        "fat_free_mass_kg": ("measurements", "Calculo"),
        "waist_hip_ratio": ("measurements", "Medidas corporais"),
        "waist_height_ratio": ("measurements", "Calculo"),
        "ffmi": ("measurements", "Calculo"),
        "bmi": ("measurements", "Calculo"),
    }
    metric_sections = (
        "primary_cards",
        "composition_metrics",
        "muscle_fat_metrics",
        "risk_metrics",
        "goal_metrics",
    )
    for section in metric_sections:
        metrics = report.get(section)
        if not isinstance(metrics, list):
            continue
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            key = str(metric.get("key") or "")
            origin = str(metric.get("origin") or "")
            origin_label = metric.get("origin_label") or body_composition_origin_label(origin, metric_key=key)
            source = source_by_key.get(key)
            if key in {"muscle_mass_kg", "basal_metabolic_rate_kcal"} and origin_label:
                source = (
                    "measurements" if origin in {"reported", "legacy_unknown"} else "calculation",
                    str(origin_label),
                )
            if not source:
                continue
            metric["source_group"] = source[0]
            metric["source_label"] = source[1]
            if key == "muscle_mass_kg":
                metric["label"] = "Massa muscular"
            elif key == "basal_metabolic_rate_kcal":
                metric["label"] = "TMB"
                metric["unit"] = "kcal/dia"
                formatted = metric.get("formatted_value")
                if isinstance(formatted, str):
                    metric["formatted_value"] = formatted.replace(" kcal", " kcal/dia")


def _assessment_metric_origin(
    assessment: Any,
    *,
    origin_field: str,
    value_field: str,
) -> str:
    origin = str(getattr(assessment, origin_field, None) or "").strip()
    if origin in CALCULATION_ORIGIN_LABELS:
        return origin
    return "unavailable" if getattr(assessment, value_field, None) is None else "legacy_unknown"


def _origin_formula_name(origin: str) -> str | None:
    return {
        "schofield_hw_1985": "Schofield-HW (1985)",
        "mifflin_st_jeor_1990": "Mifflin-St Jeor (1990)",
        "lee_2000": "Lee et al. (2000)",
        "poortmans_2005": "Poortmans et al. (2005)",
    }.get(origin)


def _muscle_methodological_note(origin: str, *, has_value: bool) -> str:
    if not has_value or origin == "unavailable":
        return " Massa muscular indisponivel: e necessaria uma medicao valida."
    if origin == "reported":
        return " A massa muscular foi medida ou informada no exame e o valor foi preservado."
    if origin == "lee_2000":
        return " A massa muscular esqueletica foi estimada pela equacao antropometrica de Lee et al. (2000)."
    if origin == "poortmans_2005":
        return " A massa muscular esqueletica foi estimada pela equacao pediatrica de Poortmans et al. (2005)."
    return " A massa muscular e um valor historico cuja origem nao pode ser identificada com seguranca."


def _bmr_methodological_note(origin: str) -> str:
    if origin == "reported":
        return " A TMB foi informada no exame e o valor foi preservado."
    if origin == "schofield_hw_1985":
        return " A TMB pediatrica foi estimada por Schofield-HW (1985), conforme sexo e idade."
    if origin == "mifflin_st_jeor_1990":
        return " A TMB adulta foi estimada por Mifflin-St Jeor (1990)."
    if origin == "legacy_unknown":
        return " A TMB e um valor historico cuja origem nao pode ser identificada com seguranca."
    return " A TMB permanece indisponivel por falta de dados suficientes."


def _muscle_cover_summary(origin: str) -> str:
    if origin == "reported":
        return "Inclui massa muscular medida ou informada no exame. "
    if origin == "lee_2000":
        return "Inclui massa muscular esqueletica estimada por Lee (2000). "
    if origin == "poortmans_2005":
        return "Inclui massa muscular esqueletica estimada por Poortmans (2005). "
    return "Inclui massa muscular historica com origem nao identificada. "


def _lee_extrapolation_flags(assessment: Any) -> list[str]:
    snapshot = getattr(assessment, "anthropometry_snapshot_json", None) or {}
    flags = snapshot.get("flags", []) if isinstance(snapshot, dict) else []
    if not isinstance(flags, list):
        return []
    return [str(flag) for flag in flags if str(flag).startswith("lee_")]


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
