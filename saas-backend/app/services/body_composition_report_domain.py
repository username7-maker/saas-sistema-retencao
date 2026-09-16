from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any, Callable, Sequence
from zoneinfo import ZoneInfo

from app.schemas.body_composition import (
    BodyCompositionGoalValueRead,
    BodyCompositionGoalsRead,
    BodyCompositionMetricObservationRead,
    BodyCompositionReportMetricRead,
    BodyCompositionReportPriorityRead,
    BodyCompositionReportScoreRead,
    BodyCompositionScoreBreakdownItemRead,
    BodyCompositionSemanticHistoryPointRead,
    BodyCompositionSemanticHistorySeriesRead,
)


BUSINESS_TIMEZONE = ZoneInfo("America/Sao_Paulo")
INCOMPATIBLE_MESSAGE = "Comparação indisponível — métodos/fontes diferentes"
OLD_REPORT_MESSAGE = "Comparação indisponível neste relatório antigo"
SCORE_DISCLAIMER = "Índice Cordex para acompanhamento individual; não representa diagnóstico clínico."


CORE_METRIC_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {"key": "weight_kg", "label": "Peso", "unit": "kg", "roles": ["headline", "key_indicator", "history"], "reference": "equipment"},
    {"key": "body_fat_used_percent", "label": "Gordura corporal", "unit": "%", "roles": ["headline", "key_indicator", "composition_detail", "history"], "reference": "protocol"},
    {"key": "muscle_mass_kg", "label": "Massa muscular", "unit": "kg", "roles": ["headline", "composition_detail", "history"], "reference": "protocol"},
    {"key": "visceral_fat_level", "label": "Gordura visceral", "unit": None, "roles": ["headline", "key_indicator", "history"], "reference": "equipment"},
    {"key": "waist_hip_ratio", "label": "Relação cintura-quadril", "unit": None, "roles": ["headline", "key_indicator", "history"], "reference": "protocol"},
    {"key": "bmi", "label": "IMC", "unit": None, "roles": ["key_indicator"], "reference": "clinical"},
    {"key": "basal_metabolic_rate_kcal", "label": "Metabolismo basal", "unit": "kcal", "roles": ["composition_detail"], "reference": "none"},
    {"key": "fat_mass_estimated_kg", "label": "Massa de gordura estimada", "unit": "kg", "roles": ["composition_detail"], "reference": "protocol"},
    {"key": "lean_mass_estimated_kg", "label": "Massa livre de gordura estimada", "unit": "kg", "roles": ["composition_detail"], "reference": "protocol"},
    {"key": "body_water_kg", "label": "Água corporal", "unit": "kg", "roles": ["composition_detail"], "reference": "equipment"},
    {"key": "body_water_percent", "label": "Água corporal (%)", "unit": "%", "roles": ["composition_detail"], "reference": "none"},
    {"key": "protein_kg", "label": "Proteína", "unit": "kg", "roles": ["composition_detail"], "reference": "equipment"},
    {"key": "inorganic_salt_kg", "label": "Sal inorgânico", "unit": "kg", "roles": ["composition_detail"], "reference": "equipment"},
    {"key": "fat_free_mass_kg", "label": "Massa livre de gordura", "unit": "kg", "roles": ["composition_detail"], "reference": "protocol"},
    {"key": "skeletal_muscle_kg", "label": "Músculo esquelético", "unit": "kg", "roles": ["composition_detail"], "reference": "equipment"},
    {"key": "skeletal_muscle_percent", "label": "Músculo esquelético", "unit": "%", "roles": ["composition_detail"], "reference": "equipment"},
    {"key": "ffmi", "label": "FFMI", "unit": None, "roles": ["key_indicator"], "reference": "protocol"},
)

_BODY_MEASUREMENT_LABELS = {
    "neck_cm": "Pescoço",
    "shoulders_cm": "Ombros",
    "chest_cm": "Tórax",
    "waist_cm": "Cintura",
    "abdomen_cm": "Abdômen",
    "hip_cm": "Quadril",
    "iliac_cm": "Ilíaca",
    "right_arm_relaxed_cm": "Braço direito relaxado",
    "left_arm_relaxed_cm": "Braço esquerdo relaxado",
    "right_arm_flexed_cm": "Braço direito contraído",
    "left_arm_flexed_cm": "Braço esquerdo contraído",
    "right_thigh_cm": "Coxa direita",
    "left_thigh_cm": "Coxa esquerda",
    "right_calf_cm": "Panturrilha direita",
    "left_calf_cm": "Panturrilha esquerda",
}
_SKINFOLD_LABELS = {
    "skinfold_chest_mm": "Dobra peitoral",
    "skinfold_midaxillary_mm": "Dobra axilar média",
    "skinfold_subscapular_mm": "Dobra subescapular",
    "skinfold_triceps_mm": "Dobra tricipital",
    "skinfold_biceps_mm": "Dobra bicipital",
    "skinfold_abdominal_mm": "Dobra abdominal",
    "skinfold_suprailiac_mm": "Dobra supra-ilíaca",
    "skinfold_thigh_mm": "Dobra da coxa",
    "skinfold_calf_mm": "Dobra da panturrilha",
}
METRIC_DEFINITIONS: tuple[dict[str, Any], ...] = CORE_METRIC_DEFINITIONS + tuple(
    {
        "key": key,
        "label": label,
        "unit": "cm",
        "roles": ["body_measurement"],
        "reference": "none",
    }
    for key, label in _BODY_MEASUREMENT_LABELS.items()
) + tuple(
    {
        "key": key,
        "label": label,
        "unit": "mm",
        "roles": ["skinfold"],
        "reference": "none",
    }
    for key, label in _SKINFOLD_LABELS.items()
)

HISTORY_KEYS = {"weight_kg", "body_fat_used_percent", "muscle_mass_kg", "visceral_fat_level", "waist_hip_ratio"}
STRICT_ORIGIN_KEYS = {"muscle_mass_kg", "basal_metabolic_rate_kcal"}
BODY_FAT_KEYS = {"body_fat_used_percent", "fat_mass_estimated_kg", "lean_mass_estimated_kg", "ffmi"}
UNKNOWN_ORIGINS = {None, "", "legacy_unknown", "unavailable"}


def is_future_evaluation(item: Any, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(tz=UTC)
    measured_at = _measured_at(item)
    if measured_at is not None and measured_at > current:
        return True
    evaluation_date = getattr(item, "evaluation_date", None)
    return bool(evaluation_date and evaluation_date > current.astimezone(BUSINESS_TIMEZONE).date())


def build_semantic_metrics(
    current: Any,
    previous: Any | None,
    *,
    history: Sequence[Any] | None = None,
    now: datetime | None = None,
    reference_resolver: Callable[[Any, str], tuple[float | None, float | None]],
    status_resolver: Callable[[float | None, float | None, float | None], str],
    origin_label_resolver: Callable[..., str | None],
) -> list[BodyCompositionReportMetricRead]:
    invalid_date = is_future_evaluation(current, now=now)
    metrics: list[BodyCompositionReportMetricRead] = []
    for order, definition in enumerate(METRIC_DEFINITIONS):
        key = definition["key"]
        unit = definition["unit"]
        metric_previous = (
            _latest_previous_with_value(current, history or (), key) or previous
            if set(definition["roles"]) & {"body_measurement", "skinfold"}
            else previous
        )
        current_value = _metric_value(current, key)
        previous_value = _metric_value(metric_previous, key) if metric_previous is not None else None
        comparison_status, comparison_message = _comparison_status(
            key,
            current,
            metric_previous,
            current_value=current_value,
            previous_value=previous_value,
            invalid_date=invalid_date,
        )
        delta = round(current_value - previous_value, 2) if comparison_status == "comparable" else None
        delta_percent = (
            round((delta / abs(previous_value)) * 100, 2)
            if delta is not None and previous_value not in (None, 0)
            else None
        )
        reference_min, reference_max = reference_resolver(current, key)
        status = status_resolver(current_value, reference_min, reference_max)
        current_source, current_method = _source_method(current, key)
        previous_source, previous_method = _source_method(metric_previous, key) if metric_previous is not None else (None, None)
        reference_kind, reference_label, reference_source = _reference_metadata(definition["reference"])
        metrics.append(
            BodyCompositionReportMetricRead(
                key=key,
                label=definition["label"],
                display_order=order,
                display_roles=definition["roles"],
                current=_observation(
                    current_value,
                    unit,
                    current_source,
                    current_method,
                    origin_label_resolver,
                    key,
                ),
                previous=(
                    _observation(
                        previous_value,
                        unit,
                        previous_source,
                        previous_method,
                        origin_label_resolver,
                        key,
                    )
                    if metric_previous is not None
                    else None
                ),
                delta=delta,
                delta_percent=delta_percent,
                formatted_delta=_format_delta(delta, unit),
                trend=_trend(delta),
                comparison_status=comparison_status,
                comparison_message=comparison_message,
                reference_kind=reference_kind,
                reference_label=reference_label,
                reference_source=reference_source,
                reference_min=reference_min,
                reference_max=reference_max,
                status=status,
                status_label=_status_label(status),
            )
        )
    return metrics


def _latest_previous_with_value(current: Any, history: Sequence[Any], key: str) -> Any | None:
    current_time = _measured_at(current)
    if current_time is None:
        return None
    candidates = []
    for item in history:
        item_time = _measured_at(item)
        if (
            item_time is not None
            and str(getattr(item, "id", "")) != str(getattr(current, "id", ""))
            and not is_future_evaluation(item)
            and item_time < current_time
            and _metric_value(item, key) is not None
        ):
            candidates.append(item)
    return max(candidates, key=_measured_at, default=None)


def build_semantic_score(
    current_score: int | None,
    previous_score: int | None,
    current_components: Sequence[BodyCompositionScoreBreakdownItemRead],
    previous_components: Sequence[BodyCompositionScoreBreakdownItemRead],
    metrics: Sequence[BodyCompositionReportMetricRead],
    *,
    invalid_date: bool,
) -> BodyCompositionReportScoreRead:
    component_metric_keys = {
        "body_fat": ("body_fat_used_percent",),
        "muscle": ("ffmi",),
        "visceral_fat": ("visceral_fat_level",),
        "waist": ("waist_hip_ratio",),
    }
    metric_by_key = {metric.key: metric for metric in metrics}
    current_keys = {item.key for item in current_components}
    previous_keys = {item.key for item in previous_components}
    if invalid_date:
        comparison_status = "invalid_date"
        message = "Comparação indisponível — data da avaliação inconsistente"
    elif current_score is None or previous_score is None or not previous_components:
        comparison_status = "missing_value"
        message = "Comparação indisponível — avaliação anterior insuficiente"
    elif current_keys != previous_keys:
        comparison_status = "missing_value"
        message = "Comparação indisponível — componentes do score diferentes"
    else:
        component_statuses = {
            metric_by_key[key].comparison_status
            for component in current_keys
            for key in component_metric_keys.get(component, ())
            if key in metric_by_key
        }
        comparison_status = "comparable" if component_statuses == {"comparable"} else (
            "invalid_date" if "invalid_date" in component_statuses else "incompatible_method"
        )
        message = None if comparison_status == "comparable" else INCOMPATIBLE_MESSAGE
    delta = current_score - previous_score if comparison_status == "comparable" and previous_score is not None and current_score is not None else None
    band, band_label = _score_band(current_score)
    return BodyCompositionReportScoreRead(
        value=current_score,
        band=band,
        band_label=band_label,
        delta=delta,
        formatted_delta=f"{delta:+d} pontos" if delta is not None else None,
        comparison_status=comparison_status,
        comparison_message=message,
        components=list(current_components),
        disclaimer=SCORE_DISCLAIMER,
    )


def build_goals(current: Any) -> BodyCompositionGoalsRead:
    definitions = (
        ("target_weight_kg", "Peso de referência", "kg"),
        ("weight_control_kg", "Controle de peso", "kg"),
        ("fat_control_kg", "Gordura a reduzir", "kg"),
        ("muscle_control_kg", "Controle de músculo", "kg"),
    )
    values = [
        BodyCompositionGoalValueRead(key=key, label=label, value=value, formatted_value=_format_value(value, unit), unit=unit)
        for key, label, unit in definitions
        if (value := _number(getattr(current, key, None))) is not None
    ]
    if not values:
        return BodyCompositionGoalsRead(
            status="unavailable",
            requires_review=True,
            professional_message="Meta pendente de definição e validação do professor.",
            member_message="Seu professor definirá a meta do próximo ciclo.",
            values=None,
        )
    muscle_control = _number(getattr(current, "muscle_control_kg", None))
    if muscle_control is not None and muscle_control < 0:
        return BodyCompositionGoalsRead(
            status="unsafe",
            requires_review=True,
            professional_message="A sugestão do equipamento implica redução de massa muscular e deve ser revista pelo professor.",
            member_message="Meta pendente de validação do professor.",
            values=values,
        )
    return BodyCompositionGoalsRead(
        status="available",
        requires_review=True,
        professional_message="Valores sugeridos pelo equipamento; valide antes de usar como meta do ciclo.",
        member_message="Meta sugerida e pendente de validação do professor.",
        values=values,
    )


def build_history(
    current: Any,
    history: Sequence[Any],
    *,
    now: datetime | None = None,
) -> list[BodyCompositionSemanticHistorySeriesRead]:
    current_invalid = is_future_evaluation(current, now=now)
    definitions = [definition for definition in METRIC_DEFINITIONS if definition["key"] in HISTORY_KEYS]
    series_list: list[BodyCompositionSemanticHistorySeriesRead] = []
    for definition in definitions:
        key = definition["key"]
        unit = definition["unit"]
        points: list[BodyCompositionSemanticHistoryPointRead] = []
        excluded = 0
        for item in history:
            value = _metric_value(item, key)
            comparable = not current_invalid and not is_future_evaluation(item, now=now) and value is not None and _history_item_compatible(key, current, item)
            if not comparable:
                if value is not None:
                    excluded += 1
                continue
            source, method = _source_method(item, key)
            measured_at = _measured_at(item)
            if measured_at is None:
                excluded += 1
                continue
            points.append(
                BodyCompositionSemanticHistoryPointRead(
                    evaluation_id=item.id,
                    measured_at=measured_at,
                    evaluation_date=item.evaluation_date,
                    value=value,
                    formatted_value=_format_value(value, unit),
                    source=source,
                    method=method,
                )
            )
        points.sort(key=lambda point: (point.measured_at, str(point.evaluation_id)))
        series_list.append(
            BodyCompositionSemanticHistorySeriesRead(
                key=key,
                label=definition["label"],
                unit=unit,
                method_signature=_method_signature(current, key),
                points=points,
                excluded_points_count=excluded,
                chart_eligible=len(points) >= 3,
                comparison_message=INCOMPATIBLE_MESSAGE if excluded else None,
            )
        )
    return series_list


def build_analysis_and_priorities(
    metrics: Sequence[BodyCompositionReportMetricRead],
    goals: BodyCompositionGoalsRead,
    *,
    invalid_date: bool,
) -> tuple[str | None, list[BodyCompositionReportPriorityRead]]:
    if invalid_date:
        return None, [
            BodyCompositionReportPriorityRead(
                key="fix_date",
                title="Corrigir a data da avaliação",
                detail="A evolução permanecerá suspensa até a data ser corrigida.",
                tone="warning",
                display_order=1,
            )
        ]
    by_key = {metric.key: metric for metric in metrics}
    comparable = [metric for metric in metrics if metric.comparison_status == "comparable" and metric.delta not in (None, 0)]
    if comparable:
        first = next((metric for metric in comparable if metric.key == "weight_kg"), comparable[0])
        direction = "reduziu" if (first.delta or 0) < 0 else "aumentou"
        analysis = f"{first.label} {direction} {first.formatted_delta.lstrip('+-') if first.formatted_delta else ''} desde a avaliação anterior."
    else:
        analysis = "A avaliação atual estabelece um retrato corporal para acompanhamento nas próximas medições."
    priorities: list[BodyCompositionReportPriorityRead] = []
    visceral = by_key.get("visceral_fat_level")
    if visceral and visceral.status in {"monitor", "high"}:
        priorities.append(BodyCompositionReportPriorityRead(
            key="monitor_visceral",
            title="Acompanhar gordura visceral",
            detail="Repita a medição em condições semelhantes na próxima avaliação.",
            tone="warning",
            display_order=len(priorities) + 1,
        ))
    if goals.requires_review:
        priorities.append(BodyCompositionReportPriorityRead(
            key="review_goal",
            title="Validar a meta do ciclo",
            detail=goals.professional_message,
            tone="warning" if goals.status == "unsafe" else "neutral",
            display_order=len(priorities) + 1,
        ))
    priorities.append(BodyCompositionReportPriorityRead(
        key="repeat_protocol",
        title="Padronizar a próxima avaliação",
        detail="Repita horário, hidratação e condições do protocolo para melhorar a comparação.",
        tone="neutral",
        display_order=len(priorities) + 1,
    ))
    return analysis, priorities[:3]


def _comparison_status(
    key: str,
    current: Any,
    previous: Any | None,
    *,
    current_value: float | None,
    previous_value: float | None,
    invalid_date: bool,
) -> tuple[str, str | None]:
    if invalid_date or (previous is not None and is_future_evaluation(previous)):
        return "invalid_date", "Comparação indisponível — data da avaliação inconsistente"
    if current_value is None or previous is None or previous_value is None:
        return "missing_value", "Comparação indisponível — valor anterior ausente"
    if not _history_item_compatible(key, current, previous):
        return "incompatible_method", INCOMPATIBLE_MESSAGE
    return "comparable", None


def _history_item_compatible(key: str, current: Any, item: Any) -> bool:
    if key in STRICT_ORIGIN_KEYS:
        current_origin = _origin(current, key)
        item_origin = _origin(item, key)
        return current_origin not in UNKNOWN_ORIGINS and current_origin == item_origin
    if key in BODY_FAT_KEYS:
        source_current, method_current = _source_method(current, key)
        source_item, method_item = _source_method(item, key)
        return bool(source_current and method_current and source_current == source_item and method_current == method_item)
    return True


def _metric_value(item: Any, key: str) -> float | None:
    if item is None:
        return None
    value = getattr(item, key, None)
    if value is None and key == "body_fat_used_percent":
        value = getattr(item, "body_fat_percent", None)
    if value is None and key == "lean_mass_estimated_kg":
        value = getattr(item, "fat_free_mass_kg", None) or getattr(item, "lean_mass_kg", None)
    return _number(value)


def _source_method(item: Any, key: str) -> tuple[str | None, str | None]:
    if item is None:
        return None, None
    if key in STRICT_ORIGIN_KEYS:
        origin = _origin(item, key)
        return origin, origin
    if key in BODY_FAT_KEYS:
        return getattr(item, "body_fat_used_source", None), getattr(item, "body_fat_method", None)
    source = getattr(item, "measurement_source", None) or getattr(item, "source", None) or "reported"
    return str(source), key


def _method_signature(item: Any, key: str) -> str | None:
    source, method = _source_method(item, key)
    parts = [str(value) for value in (source, method) if value]
    return "::".join(parts) or None


def _origin(item: Any, key: str) -> str | None:
    field = "muscle_mass_origin" if key == "muscle_mass_kg" else "basal_metabolic_rate_origin"
    return str(getattr(item, field, None) or "") or None


def _observation(
    value: float | None,
    unit: str | None,
    source: str | None,
    method: str | None,
    origin_label_resolver: Callable[..., str | None],
    key: str,
) -> BodyCompositionMetricObservationRead:
    source_label = origin_label_resolver(source, metric_key=key) if key in STRICT_ORIGIN_KEYS else _metric_source_label(key, source)
    method_label = origin_label_resolver(method, metric_key=key) if key in STRICT_ORIGIN_KEYS else _metric_method_label(key, method)
    return BodyCompositionMetricObservationRead(
        value=value,
        formatted_value=_format_value(value, unit),
        unit=unit,
        source=source,
        source_label=source_label,
        method=method,
        method_label=method_label,
    )


def _reference_metadata(kind: str) -> tuple[str, str | None, str | None]:
    if kind == "clinical":
        return "clinical", "Referência clínica", "OMS — classificação de IMC para adultos"
    if kind == "equipment":
        return "equipment", "Faixa técnica do equipamento", "Escala informada pelo equipamento"
    if kind == "protocol":
        return "protocol", "Referência do protocolo", "Cordex — protocolo operacional"
    return "none", None, None


def _score_band(value: int | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if value <= 39:
        return "attention", "Atenção"
    if value <= 69:
        return "intermediate", "Intermediária"
    if value <= 84:
        return "good", "Boa"
    return "excellent", "Excelente"


def _measured_at(item: Any) -> datetime | None:
    value = getattr(item, "measured_at", None)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    evaluation_date = getattr(item, "evaluation_date", None)
    if isinstance(evaluation_date, date):
        return datetime.combine(evaluation_date, time(hour=12), tzinfo=UTC)
    return None


def _number(value: Any) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_value(value: float | int | None, unit: str | None) -> str:
    if value is None:
        return "-"
    number = float(value)
    text = str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{text} {unit}" if unit else text


def _format_delta(value: float | None, unit: str | None) -> str | None:
    if value is None:
        return None
    prefix = "+" if value > 0 else ""
    return f"{prefix}{_format_value(value, unit)}"


def _trend(value: float | None) -> str | None:
    if value is None:
        return None
    if abs(value) < 0.01:
        return "stable"
    return "up" if value > 0 else "down"


def _status_label(status: str) -> str:
    return {"low": "Abaixo", "adequate": "Normal", "monitor": "Monitorar", "high": "Acima"}.get(status, "Sem faixa")


def _generic_source_label(source: str | None) -> str | None:
    return {
        "bioimpedance": "Bioimpedância",
        "anthropometry": "Dobras e medidas",
        "manual_anthropometry": "Dobras e medidas",
        "manual_override": "Informado pelo profissional",
        "reported": "Medido/informado",
    }.get(source, source)


def _generic_method_label(method: str | None) -> str | None:
    return {
        "legacy_bioimpedance": "Leitura da bioimpedância",
        "skinfold_protocol": "Protocolo de dobras",
        "navy_circumference": "Circunferências",
        "geneos_composite": "Método composto GeneOS",
        "manual_override": "Informado pelo profissional",
    }.get(method, method)


def _metric_source_label(key: str, source: str | None) -> str | None:
    labels = {
        "bmi": "Calculado por peso e altura",
        "waist_hip_ratio": "Medidas corporais",
        "weight_kg": "Medido/informado",
        "visceral_fat_level": "Bioimpedância",
        "body_water_kg": "Bioimpedância",
        "body_water_percent": "Bioimpedância",
        "protein_kg": "Bioimpedância",
        "inorganic_salt_kg": "Bioimpedância",
        "skeletal_muscle_kg": "Bioimpedância",
        "skeletal_muscle_percent": "Bioimpedância",
    }
    if key in _BODY_MEASUREMENT_LABELS:
        return "Medidas corporais"
    return labels.get(key) or _generic_source_label(source)


def _metric_method_label(key: str, method: str | None) -> str | None:
    labels = {
        "bmi": "Peso dividido pela altura ao quadrado",
        "waist_hip_ratio": "Relação entre cintura e quadril",
        "weight_kg": "Pesagem",
    }
    if key in _BODY_MEASUREMENT_LABELS:
        return "Perimetria"
    return labels.get(key) or _generic_method_label(method)
