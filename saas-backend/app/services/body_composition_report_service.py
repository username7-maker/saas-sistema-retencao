from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Any, Sequence

from app.models import Member
from app.models.body_composition import BodyCompositionEvaluation
from app.schemas.body_composition import (
    BodyCompositionComparisonRowRead,
    BodyCompositionDataQualityFlag,
    BodyCompositionHistoryPointRead,
    BodyCompositionHistorySeriesRead,
    BodyCompositionInsightRead,
    BodyCompositionMetricCardRead,
    BodyCompositionRangeStatus,
    BodyCompositionReferenceMetricRead,
    BodyCompositionReportHeaderRead,
    BodyCompositionReportRead,
)
from app.services.premium_report_service import (
    PremiumReportAction,
    PremiumReportBranding,
    PremiumReportChart,
    PremiumReportChartPoint,
    PremiumReportMetric,
    PremiumReportNarrative,
    PremiumReportPayload,
    PremiumReportSection,
    PremiumReportTable,
)


METHODOLOGICAL_NOTE = (
    "Comparacoes historicas sao mais confiaveis quando as medicoes sao feitas em condicoes "
    "semelhantes de hidratacao, alimentacao, exercicio e horario."
)

_REFERENCE_RANGES: dict[str, tuple[float | None, float | None]] = {
    "body_water_kg": (20.0, 70.0),
    "protein_kg": (5.0, 25.0),
    "inorganic_salt_kg": (2.0, 6.0),
    "body_fat_kg": (5.0, 30.0),
    "fat_free_mass_kg": (35.0, 90.0),
    "muscle_mass_kg": (20.0, 60.0),
    "weight_kg": (20.0, 220.0),
    "skeletal_muscle_kg": (15.0, 45.0),
    "body_fat_percent": (10.0, 25.0),
    "visceral_fat_level": (1.0, 12.0),
    "waist_hip_ratio": (0.7, 0.95),
    "health_score": (70.0, 100.0),
}

_CARD_DEFS = (
    ("weight_kg", "Peso", "kg"),
    ("body_fat_percent", "% gordura corporal", "%"),
    ("visceral_fat_level", "Gordura visceral", None),
    ("muscle_mass_kg", "Massa muscular", "kg"),
    ("bmi", "IMC", None),
    ("basal_metabolic_rate_kcal", "Metabolismo basal", "kcal"),
)

_COMPOSITION_DEFS = (
    ("body_water_kg", "Agua corporal", "kg"),
    ("protein_kg", "Proteina", "kg"),
    ("inorganic_salt_kg", "Minerais", "kg"),
    ("body_fat_kg", "Massa de gordura", "kg"),
    ("fat_free_mass_kg", "Massa livre de gordura", "kg"),
    ("muscle_mass_kg", "Massa muscular", "kg"),
)

_MUSCLE_FAT_DEFS = (
    ("weight_kg", "Peso total", "kg"),
    ("skeletal_muscle_kg", "Musculo esqueletico", "kg"),
    ("body_fat_kg", "Gordura corporal", "kg"),
)

_RISK_DEFS = (
    ("bmi", "IMC", None),
    ("body_fat_percent", "% gordura", "%"),
    ("visceral_fat_level", "Gordura visceral", None),
    ("waist_hip_ratio", "Relacao cintura-quadril", None),
    ("health_score", "Health score", None),
    ("physical_age", "Idade fisica", "anos"),
)

_GOAL_DEFS = (
    ("target_weight_kg", "Peso-alvo", "kg"),
    ("weight_control_kg", "Controle de peso", "kg"),
    ("fat_control_kg", "Controle de gordura", "kg"),
    ("muscle_control_kg", "Controle de musculo", "kg"),
)

_COMPARISON_DEFS = (
    ("weight_kg", "Peso", "kg"),
    ("body_fat_percent", "% gordura", "%"),
    ("muscle_mass_kg", "Massa muscular", "kg"),
    ("visceral_fat_level", "Gordura visceral", None),
    ("bmi", "IMC", None),
    ("basal_metabolic_rate_kcal", "Metabolismo basal", "kcal"),
)

_HISTORY_DEFS = (
    ("weight_kg", "Peso", "kg"),
    ("body_fat_percent", "% gordura", "%"),
    ("muscle_mass_kg", "Massa muscular", "kg"),
    ("visceral_fat_level", "Gordura visceral", None),
)


def build_body_composition_quality_flags(
    values: Any,
    *,
    parsing_confidence: float | None = None,
    needs_review: bool = False,
) -> list[BodyCompositionDataQualityFlag]:
    flags: list[BodyCompositionDataQualityFlag] = []
    body_fat_percent = _read_float(values, "body_fat_percent")
    muscle_mass = _read_float(values, "muscle_mass_kg")
    bmi = _read_float(values, "bmi")

    if body_fat_percent is None:
        flags.append("missing_body_fat_percent")
    if muscle_mass is None and _read_float(values, "skeletal_muscle_kg") is None:
        flags.append("missing_muscle_mass")
    if bmi is not None and not 5 <= bmi <= 80:
        flags.append("suspect_bmi")
    if parsing_confidence is not None and parsing_confidence < 0.85:
        flags.append("ocr_low_confidence")
    if needs_review:
        flags.append("manually_review_required")
    return list(dict.fromkeys(flags))


def resolve_body_composition_persistence_fields(
    values: dict[str, Any],
    *,
    reviewer_user_id: Any = None,
) -> dict[str, Any]:
    data = dict(values)
    fat_free_mass = _maybe_float(data.get("fat_free_mass_kg"))
    lean_mass = _maybe_float(data.get("lean_mass_kg"))
    if fat_free_mass is None and lean_mass is not None:
        data["fat_free_mass_kg"] = lean_mass
        fat_free_mass = lean_mass
    if lean_mass is None and fat_free_mass is not None:
        data["lean_mass_kg"] = fat_free_mass

    measured_at = data.get("measured_at")
    evaluation_date = data.get("evaluation_date")
    if measured_at is None and evaluation_date is not None:
        data["measured_at"] = datetime.combine(evaluation_date, time(hour=12), tzinfo=UTC)
    elif measured_at is not None and evaluation_date is None:
        data["evaluation_date"] = measured_at.date() if isinstance(measured_at, datetime) else evaluation_date

    parsing_confidence = data.get("parsing_confidence")
    if parsing_confidence is None:
        parsing_confidence = data.get("ocr_confidence")
        data["parsing_confidence"] = parsing_confidence
    if data.get("ocr_confidence") is None:
        data["ocr_confidence"] = parsing_confidence

    needs_review = bool(data.get("needs_review", False))
    reviewed_manually = bool(data.get("reviewed_manually", False))
    if reviewed_manually and reviewer_user_id:
        data["reviewer_user_id"] = reviewer_user_id
    elif not reviewed_manually:
        data["reviewer_user_id"] = None

    data["data_quality_flags_json"] = build_body_composition_quality_flags(
        data,
        parsing_confidence=parsing_confidence,
        needs_review=needs_review or not reviewed_manually,
    )
    return data


def build_body_composition_report_read(
    member: Member,
    evaluation: BodyCompositionEvaluation,
    *,
    history: Sequence[BodyCompositionEvaluation],
) -> BodyCompositionReportRead:
    ordered_history = sorted(
        history,
        key=lambda item: (
            _measured_at(item),
            getattr(item, "created_at", None) or datetime.min.replace(tzinfo=UTC),
        ),
    )
    previous = _resolve_previous_evaluation(evaluation, ordered_history)
    header = BodyCompositionReportHeaderRead(
        member_name=member.full_name,
        gym_name=getattr(getattr(member, "gym", None), "name", None),
        trainer_name=getattr(getattr(member, "assigned_user", None), "full_name", None),
        measured_at=_measured_at(evaluation),
        age_years=getattr(evaluation, "age_years", None) or _resolve_member_age(member, evaluation),
        sex=getattr(evaluation, "sex", None),
        height_cm=_read_float(evaluation, "height_cm"),
        weight_kg=_read_float(evaluation, "weight_kg"),
    )
    insights = generate_body_composition_insights(evaluation, ordered_history)
    return BodyCompositionReportRead(
        header=header,
        current_evaluation_id=evaluation.id,
        previous_evaluation_id=previous.id if previous else None,
        reviewed_manually=bool(getattr(evaluation, "reviewed_manually", False)),
        parsing_confidence=_read_float(evaluation, "parsing_confidence") or _read_float(evaluation, "ocr_confidence"),
        data_quality_flags=list(getattr(evaluation, "data_quality_flags_json", None) or []),
        primary_cards=[_build_metric_card(evaluation, previous, key, label, unit) for key, label, unit in _CARD_DEFS],
        composition_metrics=[_build_reference_metric(evaluation, key, label, unit) for key, label, unit in _COMPOSITION_DEFS],
        muscle_fat_metrics=[_build_reference_metric(evaluation, key, label, unit) for key, label, unit in _MUSCLE_FAT_DEFS],
        risk_metrics=[_build_reference_metric(evaluation, key, label, unit) for key, label, unit in _RISK_DEFS],
        goal_metrics=[_build_reference_metric(evaluation, key, label, unit) for key, label, unit in _GOAL_DEFS],
        comparison_rows=[_build_comparison_row(evaluation, previous, key, label, unit) for key, label, unit in _COMPARISON_DEFS],
        history_series=[_build_history_series(ordered_history, key, label, unit) for key, label, unit in _HISTORY_DEFS],
        insights=insights,
        teacher_notes=getattr(evaluation, "notes", None),
        methodological_note=METHODOLOGICAL_NOTE,
        segmental_analysis_available=False,
    )


def build_body_composition_premium_pdf_payload(
    report: BodyCompositionReportRead,
    *,
    technical: bool,
) -> PremiumReportPayload:
    comparison_rows = [
        [
            row.label,
            row.previous_formatted,
            row.current_formatted,
            _format_delta(row.difference_absolute, row.difference_percent, row.unit),
        ]
        for row in report.comparison_rows
    ]
    insight_rows = [PremiumReportNarrative(item.title, item.message, tone=_map_tone(item.tone)) for item in report.insights]
    charts = [
        PremiumReportChart(
            title=series.label,
            points=[
                PremiumReportChartPoint(label=point.evaluation_date.strftime("%d/%m"), value=float(point.value))
                for point in series.points
                if point.value is not None
            ],
            unit=series.unit,
            insight="Serie historica da metrica ao longo das avaliacoes.",
        )
        for series in report.history_series
        if any(point.value is not None for point in series.points)
    ]
    return PremiumReportPayload(
        report_kind="body_composition",
        report_scope="technical" if technical else "member_summary",
        title="Relatorio tecnico de composicao corporal" if technical else "Relatorio premium de bioimpedancia",
        subtitle=f"{report.header.member_name} · {report.header.measured_at.strftime('%d/%m/%Y %H:%M')}",
        generated_at=datetime.now(tz=UTC),
        generated_by="Sistema",
        version="premium-v3",
        branding=PremiumReportBranding(gym_name=report.header.gym_name),
        parameters={
            "evaluation_id": str(report.current_evaluation_id),
            "previous_evaluation_id": str(report.previous_evaluation_id) if report.previous_evaluation_id else None,
            "technical": technical,
            "layout_style": "clinical_sheet_v1",
            "report": report.model_dump(mode="json"),
        },
        entity_id=str(report.current_evaluation_id),
        evaluation_id=str(report.current_evaluation_id),
        subject_name=report.header.member_name,
        cover_summary=_build_cover_summary(report, technical=technical),
        sections=[
            PremiumReportSection(
                title="Resumo do exame",
                subtitle="Painel principal da avaliacao atual.",
                metrics=[_metric_card_to_premium(card) for card in report.primary_cards],
                narratives=insight_rows[:2],
            ),
            PremiumReportSection(
                title="Composicao corporal",
                subtitle="Leitura estruturada dos compartimentos corporais e indicadores de risco.",
                tables=[
                    PremiumReportTable(
                        title="Composicao corporal",
                        columns=["Metrica", "Valor", "Faixa", "Status"],
                        rows=[_reference_metric_row(metric) for metric in report.composition_metrics],
                    ),
                    PremiumReportTable(
                        title="Peso × musculo × gordura",
                        columns=["Metrica", "Valor", "Faixa", "Status"],
                        rows=[_reference_metric_row(metric) for metric in report.muscle_fat_metrics],
                    ),
                    PremiumReportTable(
                        title="Indicadores de risco e acompanhamento",
                        columns=["Metrica", "Valor", "Faixa", "Status"],
                        rows=[_reference_metric_row(metric) for metric in report.risk_metrics],
                    ),
                    PremiumReportTable(
                        title="Objetivo e controle corporal",
                        columns=["Metrica", "Valor", "Faixa", "Status"],
                        rows=[_reference_metric_row(metric) for metric in report.goal_metrics],
                    ),
                ],
                narratives=insight_rows[2:4] if technical else [],
            ),
            PremiumReportSection(
                title="Evolucao",
                subtitle="Comparativo com a avaliacao anterior e serie historica.",
                tables=[
                    PremiumReportTable(
                        title="Anterior vs atual",
                        columns=["Metrica", "Anterior", "Atual", "Delta"],
                        rows=comparison_rows or [["Linha de base", "-", "-", "-"]],
                    )
                ],
                charts=charts,
                narratives=insight_rows[4:] if technical else insight_rows[2:],
                actions=_build_recommended_actions(report),
            ),
        ],
        footer_note=METHODOLOGICAL_NOTE,
    )


def generate_body_composition_insights(
    current: BodyCompositionEvaluation,
    history: Sequence[BodyCompositionEvaluation],
) -> list[BodyCompositionInsightRead]:
    ordered = sorted(
        history,
        key=lambda item: (
            _measured_at(item),
            getattr(item, "created_at", None) or datetime.min.replace(tzinfo=UTC),
        ),
    )
    previous = _resolve_previous_evaluation(current, ordered)
    insights: list[BodyCompositionInsightRead] = []

    if previous is None:
        return [
            BodyCompositionInsightRead(
                key="baseline",
                title="Linha de base inicial",
                message="Esta e a primeira linha de base confiavel para acompanhar evolucao corporal nas proximas avaliacoes.",
                tone="neutral",
                reasons=["Historico insuficiente para comparacoes consistentes."],
            )
        ]

    body_fat_delta = _delta(_read_float(current, "body_fat_percent"), _read_float(previous, "body_fat_percent"))
    muscle_delta = _delta(_read_float(current, "muscle_mass_kg"), _read_float(previous, "muscle_mass_kg"))
    weight_delta = _delta(_read_float(current, "weight_kg"), _read_float(previous, "weight_kg"))
    visceral_current = _read_float(current, "visceral_fat_level")
    visceral_prev = _read_float(previous, "visceral_fat_level")

    if body_fat_delta is not None and body_fat_delta < -0.3 and (muscle_delta is None or muscle_delta >= -0.3):
        insights.append(
            BodyCompositionInsightRead(
                key="fat_down_muscle_stable",
                title="Reducao de gordura com preservacao muscular",
                message="Houve reducao de gordura corporal sem perda relevante de massa muscular.",
                tone="positive",
                reasons=[
                    f"% gordura variou {body_fat_delta:+.2f} p.p.",
                    f"massa muscular variou {muscle_delta:+.2f} kg." if muscle_delta is not None else "massa muscular sem leitura comparavel.",
                ],
            )
        )

    if weight_delta is not None and weight_delta < -0.5 and muscle_delta is not None and muscle_delta < -0.8:
        insights.append(
            BodyCompositionInsightRead(
                key="lean_loss_alert",
                title="Atencao para perda de massa magra",
                message="O peso caiu, mas parte relevante da reducao veio de massa muscular. Vale revisar treino e ingestao proteica.",
                tone="warning",
                reasons=[
                    f"peso variou {weight_delta:+.2f} kg",
                    f"massa muscular variou {muscle_delta:+.2f} kg",
                ],
            )
        )

    if visceral_current is not None and visceral_current > 12 and (visceral_prev is None or visceral_current <= visceral_prev + 0.3):
        insights.append(
            BodyCompositionInsightRead(
                key="visceral_persistent",
                title="Gordura visceral ainda elevada",
                message="A gordura visceral segue acima da faixa operacional desejada e merece acompanhamento continuo.",
                tone="warning",
                reasons=[f"gordura visceral atual em {visceral_current:.1f}."],
            )
        )

    last_three = [item for item in ordered if _read_float(item, "body_fat_percent") is not None][-3:]
    if len(last_three) >= 3:
        values = [_read_float(item, "body_fat_percent") for item in last_three]
        if values[0] is not None and values[1] is not None and values[2] is not None and values[0] >= values[1] >= values[2]:
            insights.append(
                BodyCompositionInsightRead(
                    key="trend_positive",
                    title="Tendencia positiva nas ultimas avaliacoes",
                    message="As ultimas tres avaliacoes sugerem direcao positiva na reducao de gordura corporal.",
                    tone="positive",
                    reasons=[f"serie de % gordura: {values[0]:.1f} → {values[1]:.1f} → {values[2]:.1f}."],
                )
            )

    if not insights:
        insights.append(
            BodyCompositionInsightRead(
                key="neutral_follow_up",
                title="Acompanhamento em andamento",
                message="Ja existe historico suficiente para acompanhamento, mas sem um sinal dominante nesta comparacao isolada.",
                tone="neutral",
                reasons=["Os principais indicadores ficaram estaveis ou com variacao pequena."],
            )
        )
    return insights


def _resolve_member_age(member: Member, evaluation: BodyCompositionEvaluation) -> int | None:
    birthdate = getattr(member, "birthdate", None)
    if birthdate is None:
        return None
    measured_date = _measured_at(evaluation).date()
    years = measured_date.year - birthdate.year
    if (measured_date.month, measured_date.day) < (birthdate.month, birthdate.day):
        years -= 1
    return max(years, 0)


def _resolve_previous_evaluation(
    evaluation: BodyCompositionEvaluation,
    history: Sequence[BodyCompositionEvaluation],
) -> BodyCompositionEvaluation | None:
    previous_items = [item for item in history if item.id != evaluation.id and _measured_at(item) <= _measured_at(evaluation)]
    return previous_items[-1] if previous_items else None


def _build_metric_card(
    current: BodyCompositionEvaluation,
    previous: BodyCompositionEvaluation | None,
    key: str,
    label: str,
    unit: str | None,
) -> BodyCompositionMetricCardRead:
    current_value = _read_float(current, key)
    previous_value = _read_float(previous, key) if previous else None
    absolute = _delta(current_value, previous_value)
    percent = _delta_percent(current_value, previous_value)
    return BodyCompositionMetricCardRead(
        key=key,
        label=label,
        value=current_value,
        unit=unit,
        formatted_value=_format_value(current_value, unit),
        delta_absolute=absolute,
        delta_percent=percent,
        trend=_trend(absolute),
    )


def _build_reference_metric(
    evaluation: BodyCompositionEvaluation,
    key: str,
    label: str,
    unit: str | None,
) -> BodyCompositionReferenceMetricRead:
    value = _read_float(evaluation, key)
    reference_min, reference_max = _resolve_reference_range(evaluation, key)
    status = _resolve_range_status(value, reference_min, reference_max)
    return BodyCompositionReferenceMetricRead(
        key=key,
        label=label,
        value=value,
        unit=unit,
        formatted_value=_format_value(value, unit),
        reference_min=reference_min,
        reference_max=reference_max,
        status=status,
        hint=_format_reference_hint(reference_min, reference_max, unit),
    )


def _build_comparison_row(
    current: BodyCompositionEvaluation,
    previous: BodyCompositionEvaluation | None,
    key: str,
    label: str,
    unit: str | None,
) -> BodyCompositionComparisonRowRead:
    current_value = _read_float(current, key)
    previous_value = _read_float(previous, key) if previous else None
    absolute = _delta(current_value, previous_value)
    percent = _delta_percent(current_value, previous_value)
    return BodyCompositionComparisonRowRead(
        key=key,
        label=label,
        unit=unit,
        previous_value=previous_value,
        current_value=current_value,
        previous_formatted=_format_value(previous_value, unit),
        current_formatted=_format_value(current_value, unit),
        difference_absolute=absolute,
        difference_percent=percent,
        trend=_trend(absolute),
    )


def _build_history_series(
    history: Sequence[BodyCompositionEvaluation],
    key: str,
    label: str,
    unit: str | None,
) -> BodyCompositionHistorySeriesRead:
    return BodyCompositionHistorySeriesRead(
        key=key,
        label=label,
        unit=unit,
        points=[
            BodyCompositionHistoryPointRead(
                evaluation_id=item.id,
                measured_at=_measured_at(item),
                evaluation_date=item.evaluation_date,
                value=_read_float(item, key),
            )
            for item in history
        ],
    )


def _metric_card_to_premium(card: BodyCompositionMetricCardRead) -> PremiumReportMetric:
    delta_hint = None
    if card.delta_absolute is not None:
        delta_hint = _format_delta(card.delta_absolute, card.delta_percent, card.unit)
    tone = "neutral"
    if card.label in {"Massa muscular", "Metabolismo basal"} and card.trend == "up":
        tone = "positive"
    if card.label in {"% gordura corporal", "Gordura visceral", "IMC"} and card.trend == "down":
        tone = "positive"
    elif card.label in {"% gordura corporal", "Gordura visceral", "IMC"} and card.trend == "up":
        tone = "warning"
    return PremiumReportMetric(card.label, card.formatted_value, hint=delta_hint, tone=tone)


def _reference_metric_row(metric: BodyCompositionReferenceMetricRead) -> list[str]:
    return [
        metric.label,
        metric.formatted_value,
        metric.hint or "-",
        _status_label(metric.status),
    ]


def _build_recommended_actions(report: BodyCompositionReportRead) -> list[PremiumReportAction]:
    actions: list[PremiumReportAction] = []
    for metric in report.goal_metrics:
        if metric.value is None:
            continue
        actions.append(PremiumReportAction(metric.label, f"Meta operacional atual: {metric.formatted_value}."))
    if report.teacher_notes:
        actions.append(PremiumReportAction("Observacao do professor", report.teacher_notes))
    if not actions:
        actions.append(PremiumReportAction("Proxima reavaliacao", "Manter acompanhamento com protocolo repetivel e comparar com esta linha de base."))
    return actions[:5]


def _build_cover_summary(report: BodyCompositionReportRead, *, technical: bool) -> str:
    weight = _format_value(report.header.weight_kg, "kg")
    body_fat = next((card.formatted_value for card in report.primary_cards if card.key == "body_fat_percent"), "-")
    muscle = next((card.formatted_value for card in report.primary_cards if card.key == "muscle_mass_kg"), "-")
    if technical:
        return (
            f"Avaliacao de {report.header.member_name} com peso {weight}, gordura corporal {body_fat} "
            f"e massa muscular {muscle}, organizada para acompanhamento tecnico."
        )
    return (
        f"Resumo premium da bioimpedancia de {report.header.member_name} com foco em composicao corporal, "
        f"evolucao e proximos passos de acompanhamento."
    )


def _map_tone(tone: str) -> str:
    return {"positive": "positive", "warning": "warning"}.get(tone, "neutral")


def _read_float(item: Any, key: str) -> float | None:
    if item is None:
        value = None
    elif isinstance(item, dict):
        value = item.get(key)
    else:
        value = getattr(item, key, None)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _measured_at(evaluation: BodyCompositionEvaluation) -> datetime:
    measured_at = getattr(evaluation, "measured_at", None)
    if isinstance(measured_at, datetime):
        return measured_at if measured_at.tzinfo else measured_at.replace(tzinfo=UTC)
    return datetime.combine(evaluation.evaluation_date, time(hour=12), tzinfo=UTC)


def _delta(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 2)


def _delta_percent(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return round(((current - previous) / previous) * 100, 2)


def _trend(delta_value: float | None) -> str:
    if delta_value is None:
        return "insufficient"
    if abs(delta_value) < 0.15:
        return "stable"
    return "up" if delta_value > 0 else "down"


def _format_value(value: float | int | None, unit: str | None = None) -> str:
    if value is None:
        return "-"
    if isinstance(value, int) or float(value).is_integer():
        text = f"{int(value)}"
    else:
        text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    if unit == "%":
        return f"{text}%"
    return f"{text} {unit}".strip() if unit else text


def _format_delta(delta_absolute: float | None, delta_percent: float | None, unit: str | None) -> str:
    if delta_absolute is None:
        return "-"
    abs_text = _format_value(delta_absolute, unit)
    if delta_percent is None:
        return abs_text
    pct_text = f"{delta_percent:+.1f}%"
    return f"{abs_text} ({pct_text})"


def _resolve_reference_range(
    evaluation: BodyCompositionEvaluation,
    key: str,
) -> tuple[float | None, float | None]:
    stored_ranges = getattr(evaluation, "measured_ranges_json", None) or {}
    if isinstance(stored_ranges, dict) and isinstance(stored_ranges.get(key), dict):
        raw = stored_ranges[key]
        return _maybe_float(raw.get("min")), _maybe_float(raw.get("max"))
    return _REFERENCE_RANGES.get(key, (None, None))


def _resolve_range_status(
    value: float | None,
    minimum: float | None,
    maximum: float | None,
) -> BodyCompositionRangeStatus:
    if value is None or (minimum is None and maximum is None):
        return "unknown"
    if minimum is not None and value < minimum:
        return "low"
    if maximum is not None and value > maximum:
        return "high"
    return "adequate"


def _format_reference_hint(minimum: float | None, maximum: float | None, unit: str | None) -> str | None:
    if minimum is None and maximum is None:
        return None
    low = _format_value(minimum, unit) if minimum is not None else "-"
    high = _format_value(maximum, unit) if maximum is not None else "-"
    return f"{low} a {high}"


def _status_label(status: BodyCompositionRangeStatus) -> str:
    return {
        "low": "Baixo",
        "adequate": "Adequado",
        "high": "Alto",
        "unknown": "Sem referencia",
    }[status]


def _maybe_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
