from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any, Sequence

from app.models import Member
from app.models.body_composition import BodyCompositionEvaluation
from app.schemas.body_composition import (
    BodyCompositionBodyFatContextRead,
    BodyCompositionComparisonRowRead,
    BodyCompositionDataQualityFlag,
    BodyCompositionHistoryPointRead,
    BodyCompositionHistorySeriesRead,
    BodyCompositionInsightRead,
    BodyCompositionMeasurementRowRead,
    BodyCompositionMetricCardRead,
    BodyCompositionNextAssessmentRead,
    BodyCompositionRecommendationRead,
    BodyCompositionRangeStatus,
    BodyCompositionReferenceMetricRead,
    BodyCompositionReportHeaderRead,
    BodyCompositionReportRead,
    BodyCompositionScoreBreakdownItemRead,
)
from app.services.body_composition_anthropometry_service import (
    ANTHROPOMETRY_CALCULATION_FIELDS,
    ANTHROPOMETRY_EVOLUTION_FIELDS,
    resolve_body_fat_fields,
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
    "semelhantes de hidratacao, alimentacao, exercicio e horario. O percentual de gordura oficial usa "
    "dobras e medidas quando houver protocolo valido; quando a avaliacao tiver apenas bioimpedancia, usa "
    "o valor informado pelo exame. Ele nao substitui avaliacao clinica."
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
    "body_fat_used_percent": (10.0, 25.0),
    "fat_mass_estimated_kg": (5.0, 30.0),
    "lean_mass_estimated_kg": (35.0, 90.0),
    "visceral_fat_level": (1.0, 12.0),
    "waist_hip_ratio": (0.7, 0.95),
    "waist_height_ratio": (0.3, 0.5),
    "ffmi": (16.0, 25.0),
    "health_score": (70.0, 100.0),
}

_CARD_DEFS = (
    ("weight_kg", "Peso", "kg"),
    ("body_fat_used_percent", "Gordura corporal estimada", "%"),
    ("visceral_fat_level", "Gordura visceral", None),
    ("muscle_mass_kg", "Massa muscular", "kg"),
    ("bmi", "IMC", None),
    ("basal_metabolic_rate_kcal", "Metabolismo basal", "kcal"),
)

_COMPOSITION_DEFS = (
    ("body_fat_used_percent", "Gordura corporal estimada", "%"),
    ("fat_mass_estimated_kg", "Massa de gordura estimada", "kg"),
    ("lean_mass_estimated_kg", "Massa livre de gordura estimada", "kg"),
    ("body_water_kg", "Agua corporal", "kg"),
    ("body_water_percent", "Agua corporal (%)", "%"),
    ("protein_kg", "Proteina", "kg"),
    ("inorganic_salt_kg", "Minerais", "kg"),
    ("fat_free_mass_kg", "Massa livre de gordura", "kg"),
    ("muscle_mass_kg", "Massa muscular", "kg"),
    ("skeletal_muscle_kg", "Musculo esqueletico", "kg"),
)

_MUSCLE_FAT_DEFS = (
    ("weight_kg", "Peso total", "kg"),
    ("skeletal_muscle_kg", "Musculo esqueletico", "kg"),
    ("fat_mass_estimated_kg", "Massa de gordura estimada", "kg"),
)

_RISK_DEFS = (
    ("bmi", "IMC", None),
    ("body_fat_used_percent", "Gordura corporal estimada", "%"),
    ("visceral_fat_level", "Gordura visceral", None),
    ("waist_hip_ratio", "Relacao cintura-quadril", None),
    ("waist_height_ratio", "Razao cintura-altura", None),
    ("ffmi", "FFMI", None),
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
    ("body_fat_used_percent", "Gordura estimada", "%"),
    ("muscle_mass_kg", "Massa muscular", "kg"),
    ("visceral_fat_level", "Gordura visceral", None),
    ("bmi", "IMC", None),
    ("basal_metabolic_rate_kcal", "Metabolismo basal", "kcal"),
)

_HISTORY_DEFS = (
    ("weight_kg", "Peso", "kg"),
    ("body_fat_used_percent", "Gordura estimada", "%"),
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
    body_fat_percent = _read_metric_float(values, "body_fat_used_percent")
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
    previous_evaluation: Any | None = None,
) -> dict[str, Any]:
    data = dict(values)
    calculated_body_water_percent = calculate_body_water_percent(
        weight_kg=data.get("weight_kg"),
        body_water_kg=data.get("body_water_kg"),
    )
    if calculated_body_water_percent is not None:
        data["body_water_percent"] = calculated_body_water_percent
    elif data.get("source") == "ocr_receipt" and data.get("device_profile") == "tezewa_receipt_v1":
        data["body_water_percent"] = None

    fat_free_mass = _maybe_float(data.get("fat_free_mass_kg"))
    lean_mass = _maybe_float(data.get("lean_mass_kg"))
    if fat_free_mass is None and lean_mass is not None:
        data["fat_free_mass_kg"] = lean_mass
        fat_free_mass = lean_mass
    if lean_mass is None and fat_free_mass is not None:
        data["lean_mass_kg"] = fat_free_mass

    data = resolve_body_fat_fields(data, previous_values=previous_evaluation)

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
        data.setdefault("evaluated_by_user_id", reviewer_user_id)
    elif not reviewed_manually:
        data["reviewer_user_id"] = None

    anthropometry_flags = list(data.get("data_quality_flags_json") or [])
    data["data_quality_flags_json"] = list(dict.fromkeys(anthropometry_flags + build_body_composition_quality_flags(
        data,
        parsing_confidence=parsing_confidence,
        needs_review=needs_review or not reviewed_manually,
    )))
    return data


def calculate_body_water_percent(*, weight_kg: Any, body_water_kg: Any) -> float | None:
    weight = _maybe_float(weight_kg)
    body_water = _maybe_float(body_water_kg)
    if weight is None or body_water is None or weight <= 0 or body_water < 0:
        return None
    return round((body_water / weight) * 100, 1)


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
    risk_metrics = [_build_reference_metric(evaluation, key, label, unit) for key, label, unit in _RISK_DEFS]
    score_breakdown = _build_score_breakdown(evaluation)
    score_total = sum(item.score for item in score_breakdown) if score_breakdown else None
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
        data_quality_flags=_public_body_composition_flags(getattr(evaluation, "data_quality_flags_json", None) or []),
        body_fat_context=_build_body_fat_context(evaluation),
        score_total=score_total,
        score_breakdown=score_breakdown,
        recommendations=_build_body_composition_recommendations(evaluation, risk_metrics),
        next_assessment=_build_next_assessment(evaluation),
        measurement_rows=_build_measurement_rows(evaluation, previous),
        primary_cards=[_build_metric_card(evaluation, previous, key, label, unit) for key, label, unit in _CARD_DEFS],
        composition_metrics=[_build_reference_metric(evaluation, key, label, unit) for key, label, unit in _COMPOSITION_DEFS],
        muscle_fat_metrics=[_build_reference_metric(evaluation, key, label, unit) for key, label, unit in _MUSCLE_FAT_DEFS],
        risk_metrics=risk_metrics,
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
    measurement_rows = [
        [row.label, row.formatted_current, row.formatted_previous, row.formatted_delta]
        for row in report.measurement_rows
        if row.current_value is not None or row.previous_value is not None
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
                subtitle="Leitura estruturada dos compartimentos corporais, fonte oficial da gordura e indicadores de risco.",
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
                    PremiumReportTable(
                        title="Medidas corporais",
                        columns=["Medida", "Atual", "Anterior", "Variacao"],
                        rows=measurement_rows or [["Sem medidas manuais", "-", "-", "-"]],
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

    body_fat_delta = _delta(_read_metric_float(current, "body_fat_used_percent"), _read_metric_float(previous, "body_fat_used_percent"))
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
                    f"gordura estimada variou {body_fat_delta:+.2f} p.p.",
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

    last_three = [item for item in ordered if _read_metric_float(item, "body_fat_used_percent") is not None][-3:]
    if len(last_three) >= 3:
        values = [_read_metric_float(item, "body_fat_used_percent") for item in last_three]
        if values[0] is not None and values[1] is not None and values[2] is not None and values[0] >= values[1] >= values[2]:
            insights.append(
                BodyCompositionInsightRead(
                    key="trend_positive",
                    title="Tendencia positiva nas ultimas avaliacoes",
                    message="As ultimas tres avaliacoes sugerem direcao positiva na reducao de gordura corporal.",
                    tone="positive",
                    reasons=[f"serie de gordura estimada: {values[0]:.1f} -> {values[1]:.1f} -> {values[2]:.1f}."],
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


def _build_body_fat_context(evaluation: BodyCompositionEvaluation) -> BodyCompositionBodyFatContextRead:
    anthropometric = _read_float(evaluation, "body_fat_anthropometric_percent")
    used = _read_metric_float(evaluation, "body_fat_used_percent")
    return BodyCompositionBodyFatContextRead(
        bioimpedance_raw_percent=None,
        anthropometric_percent=anthropometric,
        used_percent=used,
        used_source=getattr(evaluation, "body_fat_used_source", None),
        preferred_source=getattr(evaluation, "preferred_body_fat_source", None),
        method=getattr(evaluation, "body_fat_method", None),
        confidence=getattr(evaluation, "body_fat_confidence", None),
        range_min=_read_float(evaluation, "body_fat_range_min"),
        range_max=_read_float(evaluation, "body_fat_range_max"),
        difference_between_sources=None,
        manual_review_required=bool(getattr(evaluation, "body_fat_manual_review_required", False)),
        manual_review_completed=bool(getattr(evaluation, "body_fat_manual_review_completed", False)),
        quality_flags=_public_body_composition_flags(getattr(evaluation, "data_quality_flags_json", None) or []),
    )


def _build_score_breakdown(evaluation: BodyCompositionEvaluation) -> list[BodyCompositionScoreBreakdownItemRead]:
    body_fat = _read_metric_float(evaluation, "body_fat_used_percent")
    body_fat_min, body_fat_max = _resolve_reference_range(evaluation, "body_fat_used_percent")
    ffmi = _read_metric_float(evaluation, "ffmi")
    visceral = _read_metric_float(evaluation, "visceral_fat_level")
    waist_hip = _read_metric_float(evaluation, "waist_hip_ratio")
    waist_height = _read_metric_float(evaluation, "waist_height_ratio")

    body_fat_score = _centered_range_score(body_fat, body_fat_min, body_fat_max)
    muscle_score = _progressive_range_score(ffmi, *_REFERENCE_RANGES["ffmi"])
    visceral_score = _inverse_range_score(visceral, *_REFERENCE_RANGES["visceral_fat_level"])
    waist_score = _average_scores(
        [
            _inverse_range_score(waist_hip, *_REFERENCE_RANGES["waist_hip_ratio"]),
            _inverse_range_score(waist_height, *_REFERENCE_RANGES["waist_height_ratio"]),
        ]
    )

    return [
        BodyCompositionScoreBreakdownItemRead(
            key="body_fat",
            label="Gordura corporal",
            score=body_fat_score,
            description="Pontua o percentual oficial usado no relatorio contra a faixa de referencia.",
        ),
        BodyCompositionScoreBreakdownItemRead(
            key="muscle",
            label="Massa muscular",
            score=muscle_score,
            description="Usa FFMI quando existe massa livre de gordura e altura suficientes.",
        ),
        BodyCompositionScoreBreakdownItemRead(
            key="visceral_fat",
            label="Gordura visceral",
            score=visceral_score,
            description="Quanto menor o indice visceral dentro da faixa, maior a pontuacao.",
        ),
        BodyCompositionScoreBreakdownItemRead(
            key="waist",
            label="Cintura / RCQ",
            score=waist_score,
            description="Combina relacao cintura-quadril e razao cintura-altura quando disponiveis.",
        ),
    ]


def _build_body_composition_recommendations(
    evaluation: BodyCompositionEvaluation,
    risk_metrics: Sequence[BodyCompositionReferenceMetricRead],
) -> list[BodyCompositionRecommendationRead]:
    recommendations: list[BodyCompositionRecommendationRead] = []
    metrics_by_key = {metric.key: metric for metric in risk_metrics}
    visceral_metric = metrics_by_key.get("visceral_fat_level")
    waist_hip_metric = metrics_by_key.get("waist_hip_ratio")
    waist_height_metric = metrics_by_key.get("waist_height_ratio")

    if any(
        metric and metric.status in {"monitor", "high"}
        for metric in (visceral_metric, waist_hip_metric, waist_height_metric)
    ):
        recommendations.append(
            BodyCompositionRecommendationRead(
                key="monitor_waist_visceral",
                title="Monitorar cintura e gordura visceral",
                detail=(
                    "Os indicadores de cintura ou gordura visceral pedem acompanhamento. "
                    "Repita as medidas nas proximas avaliacoes e priorize consistencia do protocolo."
                ),
                tone="warning",
            )
        )

    thigh_delta = _paired_measure_delta(
        _read_float(evaluation, "right_thigh_cm"),
        _read_float(evaluation, "left_thigh_cm"),
    )
    if thigh_delta is not None and thigh_delta >= 4:
        recommendations.append(
            BodyCompositionRecommendationRead(
                key="repeat_thigh_measurement",
                title="Repetir a medicao da coxa",
                detail=(
                    f"A diferenca registrada entre as coxas foi de {thigh_delta:.1f} cm. "
                    "Esse desvio e atipico e deve ser conferido antes de orientar decisoes pelo valor."
                ),
                tone="warning",
            )
        )

    muscle_control = _read_float(evaluation, "muscle_control_kg")
    if muscle_control is not None and muscle_control < 0:
        recommendations.append(
            BodyCompositionRecommendationRead(
                key="review_target_weight",
                title="Definir o objetivo do ciclo antes do peso-alvo",
                detail=(
                    "A meta automatica indica reducao de massa muscular. "
                    "Revise o objetivo com o professor antes de usar esse peso-alvo como referencia."
                ),
                tone="warning",
            )
        )

    if not recommendations:
        recommendations.append(
            BodyCompositionRecommendationRead(
                key="repeat_protocol",
                title="Manter o mesmo protocolo na proxima avaliacao",
                detail="Repita as medidas em condicoes semelhantes para tornar a evolucao comparavel.",
                tone="neutral",
            )
        )
    return recommendations[:3]


def _build_next_assessment(evaluation: BodyCompositionEvaluation) -> BodyCompositionNextAssessmentRead:
    measured_date = _measured_at(evaluation).date()
    due_date = measured_date + timedelta(days=90)
    contact_date = measured_date + timedelta(days=75)
    return BodyCompositionNextAssessmentRead(
        due_date=due_date,
        formatted_due_date=due_date.strftime("%d/%m/%Y"),
        contact_date=contact_date,
        formatted_contact_date=contact_date.strftime("%d/%m/%Y"),
        cycle_days=90,
        contact_offset_days=75,
        conditions=[
            "mesmo horario sempre que possivel",
            "hidratacao semelhante",
            "evitar treino intenso imediatamente antes",
            "manter padrao de alimentacao previo",
        ],
    )


def _paired_measure_delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(abs(left - right), 1)


def _public_body_composition_flags(flags: Sequence[Any]) -> list[BodyCompositionDataQualityFlag]:
    hidden = {"body_fat_source_divergence"}
    return [flag for flag in flags if str(flag) not in hidden]


_MEASUREMENT_LABELS = {
    "neck_cm": "Pescoco",
    "waist_cm": "Cintura",
    "abdomen_cm": "Abdomen",
    "hip_cm": "Quadril",
    "shoulders_cm": "Ombros",
    "chest_cm": "Torax",
    "right_arm_relaxed_cm": "Braco direito relaxado",
    "left_arm_relaxed_cm": "Braco esquerdo relaxado",
    "right_arm_flexed_cm": "Braco direito contraido",
    "left_arm_flexed_cm": "Braco esquerdo contraido",
    "right_thigh_cm": "Coxa direita",
    "left_thigh_cm": "Coxa esquerda",
    "right_calf_cm": "Panturrilha direita",
    "left_calf_cm": "Panturrilha esquerda",
}


def _build_measurement_rows(
    current: BodyCompositionEvaluation,
    previous: BodyCompositionEvaluation | None,
) -> list[BodyCompositionMeasurementRowRead]:
    rows: list[BodyCompositionMeasurementRowRead] = []
    for key in ANTHROPOMETRY_CALCULATION_FIELDS + ANTHROPOMETRY_EVOLUTION_FIELDS:
        current_value = _read_float(current, key)
        previous_value = _read_float(previous, key) if previous else None
        delta = _delta(current_value, previous_value)
        rows.append(
            BodyCompositionMeasurementRowRead(
                key=key,
                label=_MEASUREMENT_LABELS.get(key, key),
                current_value=current_value,
                previous_value=previous_value,
                delta=delta,
                used_for_body_fat_calculation=key in ANTHROPOMETRY_CALCULATION_FIELDS,
                formatted_current=_format_value(current_value, "cm"),
                formatted_previous=_format_value(previous_value, "cm"),
                formatted_delta=_format_delta(delta, None, "cm") if delta is not None else "-",
            )
        )
    return rows


def _build_metric_card(
    current: BodyCompositionEvaluation,
    previous: BodyCompositionEvaluation | None,
    key: str,
    label: str,
    unit: str | None,
) -> BodyCompositionMetricCardRead:
    current_value = _read_metric_float(current, key)
    previous_value = _read_metric_float(previous, key) if previous else None
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
    value = _read_metric_float(evaluation, key)
    reference_min, reference_max = _resolve_reference_range(evaluation, key)
    status = _resolve_range_status(value, reference_min, reference_max)
    position_label = _range_position_label(value, reference_min, reference_max)
    if status == "adequate" and _is_upper_third_risk_indicator(key, value, reference_min, reference_max):
        status = "monitor"
    hint = _format_reference_hint(reference_min, reference_max, unit)
    if key == "bmi":
        hint = "Interpretar junto com o FFMI; IMC isolado pode superestimar excesso de peso em perfis musculosos."
    elif key == "waist_height_ratio" and reference_max is not None:
        hint = f"Meta < {_format_value(reference_max, None)}"
        if value is not None and value <= reference_max:
            position_label = "dentro da meta"
    return BodyCompositionReferenceMetricRead(
        key=key,
        label=label,
        value=value,
        unit=unit,
        formatted_value=_format_value(value, unit),
        reference_min=reference_min,
        reference_max=reference_max,
        status=status,
        hint=hint,
        position_label=position_label,
    )


def _build_comparison_row(
    current: BodyCompositionEvaluation,
    previous: BodyCompositionEvaluation | None,
    key: str,
    label: str,
    unit: str | None,
) -> BodyCompositionComparisonRowRead:
    current_value = _read_metric_float(current, key)
    previous_value = _read_metric_float(previous, key) if previous else None
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
                value=_read_metric_float(item, key),
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
    if card.label in {"Gordura corporal estimada", "Gordura visceral", "IMC"} and card.trend == "down":
        tone = "positive"
    elif card.label in {"Gordura corporal estimada", "Gordura visceral", "IMC"} and card.trend == "up":
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
    body_fat = next((card.formatted_value for card in report.primary_cards if card.key == "body_fat_used_percent"), "-")
    muscle = next((card.formatted_value for card in report.primary_cards if card.key == "muscle_mass_kg"), "-")
    if technical:
        return (
            f"Avaliacao de {report.header.member_name} com peso {weight}, gordura corporal estimada {body_fat} "
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


def _read_metric_float(item: Any, key: str) -> float | None:
    if key == "body_fat_used_percent":
        return _read_float(item, "body_fat_used_percent")
    if key == "waist_height_ratio":
        waist = _read_float(item, "waist_cm")
        height = _read_float(item, "height_cm")
        if waist is None or height in (None, 0):
            return None
        return round(waist / height, 2)
    if key == "ffmi":
        fat_free_mass = (
            _read_float(item, "fat_free_mass_kg")
            or _read_float(item, "lean_mass_estimated_kg")
            or _read_float(item, "lean_mass_kg")
        )
        height = _read_float(item, "height_cm")
        if fat_free_mass is None or height in (None, 0):
            return None
        height_m = height / 100
        if height_m <= 0:
            return None
        return round(fat_free_mass / (height_m * height_m), 1)
    value = _read_float(item, key)
    if value is not None or key != "body_water_percent":
        return value
    return calculate_body_water_percent(
        weight_kg=_read_float(item, "weight_kg"),
        body_water_kg=_read_float(item, "body_water_kg"),
    )


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
    if key == "body_fat_used_percent":
        body_fat_min = _read_float(evaluation, "body_fat_range_min")
        body_fat_max = _read_float(evaluation, "body_fat_range_max")
        if body_fat_min is not None or body_fat_max is not None:
            return body_fat_min, body_fat_max
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


def _is_upper_third_risk_indicator(
    key: str,
    value: float | None,
    minimum: float | None,
    maximum: float | None,
) -> bool:
    if key not in {"visceral_fat_level", "waist_hip_ratio"}:
        return False
    if value is None or minimum is None or maximum is None or maximum <= minimum:
        return False
    upper_third_start = minimum + ((maximum - minimum) * 2 / 3)
    return value >= upper_third_start


def _range_position_label(value: float | None, minimum: float | None, maximum: float | None) -> str | None:
    if value is None or minimum is None or maximum is None or maximum <= minimum:
        return None
    if value < minimum:
        return "abaixo da faixa"
    if value > maximum:
        return "acima da faixa"
    third = (maximum - minimum) / 3
    if value < minimum + third:
        return "terco inferior da faixa"
    if value < minimum + 2 * third:
        return "terco medio da faixa"
    return "terco superior da faixa"


def _centered_range_score(value: float | None, minimum: float | None, maximum: float | None, max_score: int = 25) -> int:
    if value is None or minimum is None or maximum is None or maximum <= minimum:
        return 0
    midpoint = (minimum + maximum) / 2
    half_span = (maximum - minimum) / 2
    distance = abs(value - midpoint)
    if distance <= half_span:
        return max(0, min(max_score, round(max_score - (distance / max(half_span, 0.01)) * 8)))
    overflow = distance - half_span
    return max(0, round(17 - (overflow / max(half_span, 0.01)) * 17))


def _progressive_range_score(value: float | None, minimum: float | None, maximum: float | None, max_score: int = 25) -> int:
    if value is None or minimum is None or maximum is None or maximum <= minimum:
        return 0
    if value < minimum:
        return max(0, round((value / max(minimum, 0.01)) * 14))
    if value > maximum:
        return max(15, round(max_score - min(10, value - maximum)))
    ratio = (value - minimum) / (maximum - minimum)
    return max(0, min(max_score, round(15 + ratio * 10)))


def _inverse_range_score(value: float | None, minimum: float | None, maximum: float | None, max_score: int = 25) -> int:
    if value is None or minimum is None or maximum is None or maximum <= minimum:
        return 0
    if value <= minimum:
        return max_score
    if value >= maximum:
        overflow_ratio = (value - maximum) / max(maximum - minimum, 0.01)
        return max(0, round(10 - overflow_ratio * 10))
    ratio = (value - minimum) / (maximum - minimum)
    return max(0, min(max_score, round(max_score - ratio * 15)))


def _average_scores(scores: Sequence[int]) -> int:
    valid = [score for score in scores if score > 0]
    if not valid:
        return 0
    return round(sum(valid) / len(valid))


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
        "monitor": "Monitorar",
        "high": "Alto",
        "unknown": "Sem referencia",
    }[status]


def _maybe_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
