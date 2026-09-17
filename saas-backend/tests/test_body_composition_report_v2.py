from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from app.schemas.body_composition import BodyCompositionEvaluationCreate
from app.services.assessment_anthropometry_report_service import build_anthropometric_report_read
from app.services.body_composition_report_service import (
    build_body_composition_report_read,
    resolve_body_composition_persistence_fields,
)
from app.services.body_composition_service import _validate_body_composition_payload
from app.services.body_composition_report_service import build_body_composition_premium_pdf_payload
from app.services.premium_report_service import render_premium_report_html


SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def _member() -> SimpleNamespace:
    return SimpleNamespace(
        full_name="Erick Bedin",
        birthdate=date(1979, 1, 1),
        gym=SimpleNamespace(name="ProGym"),
        assigned_user=SimpleNamespace(full_name="Professor Teste"),
    )


def _evaluation(
    measured_at: datetime,
    *,
    weight: float = 82,
    muscle: float = 40,
    muscle_origin: str = "reported",
    bmr: float = 1880,
    bmr_origin: str = "reported",
    body_fat: float = 15.2,
    body_fat_source: str = "bioimpedance",
    body_fat_method: str = "legacy_bioimpedance",
    muscle_control: float | None = 0.5,
    notes: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        evaluation_date=measured_at.astimezone(SAO_PAULO).date(),
        measured_at=measured_at,
        created_at=measured_at,
        age_years=47,
        sex="male",
        height_cm=180,
        weight_kg=weight,
        body_fat_percent=body_fat,
        body_fat_used_percent=body_fat,
        body_fat_bioimpedance_percent=body_fat if body_fat_source == "bioimpedance" else None,
        body_fat_anthropometric_percent=body_fat if body_fat_source == "anthropometry" else None,
        body_fat_manual_override_percent=None,
        body_fat_range_min=None,
        body_fat_range_max=None,
        body_fat_used_source=body_fat_source,
        preferred_body_fat_source=body_fat_source,
        body_fat_method=body_fat_method,
        body_fat_confidence="high",
        body_fat_manual_review_required=False,
        body_fat_manual_review_completed=True,
        fat_mass_estimated_kg=round(weight * body_fat / 100, 2),
        lean_mass_estimated_kg=round(weight * (1 - body_fat / 100), 2),
        fat_free_mass_kg=round(weight * (1 - body_fat / 100), 2),
        muscle_mass_kg=muscle,
        muscle_mass_origin=muscle_origin,
        skeletal_muscle_kg=None,
        skeletal_muscle_percent=38,
        body_water_kg=49.8,
        body_water_percent=60.6,
        protein_kg=16.1,
        inorganic_salt_kg=4,
        visceral_fat_level=12,
        waist_hip_ratio=0.9,
        waist_height_ratio=None,
        ffmi=21.5,
        bmi=25.4,
        basal_metabolic_rate_kcal=bmr,
        basal_metabolic_rate_origin=bmr_origin,
        target_weight_kg=70,
        weight_control_kg=-12,
        fat_control_kg=-5.7,
        muscle_control_kg=muscle_control,
        physical_age=28,
        health_score=67,
        notes=notes,
        reviewed_manually=True,
        parsing_confidence=1,
        data_quality_flags_json=[],
        measured_ranges_json={},
    )


def _metric(report, key: str):
    return next(metric for metric in report.metrics if metric.key == key)


def test_v2_contract_blocks_deltas_for_incompatible_metric_origins() -> None:
    previous = _evaluation(
        datetime(2026, 8, 1, 12, tzinfo=UTC),
        weight=99,
        muscle=62.4,
        muscle_origin="reported",
        bmr=1350,
        bmr_origin="reported",
    )
    current = _evaluation(
        datetime(2026, 9, 1, 12, tzinfo=UTC),
        weight=82.2,
        muscle=40,
        muscle_origin="legacy_unknown",
        bmr=1880,
        bmr_origin="legacy_unknown",
    )

    report = build_body_composition_report_read(_member(), current, history=[previous, current])

    assert report.contract_version == "body-composition-report-v2"
    assert report.evaluation_number == 2
    assert report.is_baseline is False
    assert _metric(report, "weight_kg").comparison_status == "comparable"
    assert _metric(report, "weight_kg").delta == pytest.approx(-16.8)
    for key in ("muscle_mass_kg", "basal_metabolic_rate_kcal"):
        metric = _metric(report, key)
        assert metric.comparison_status == "incompatible_method"
        assert metric.delta is None
        assert metric.trend is None
        assert metric.comparison_message == "Comparação indisponível — métodos/fontes diferentes"
    assert "massa muscular" not in (report.analysis_cordex or "").lower()


def test_score_comparison_requires_all_score_components_to_be_comparable() -> None:
    previous = _evaluation(
        datetime(2026, 8, 1, 12, tzinfo=UTC),
        body_fat_source="bioimpedance",
        body_fat_method="bioimpedance_v1",
    )
    current = _evaluation(
        datetime(2026, 9, 1, 12, tzinfo=UTC),
        body_fat_source="bioimpedance",
        body_fat_method="legacy_bioimpedance",
    )

    report = build_body_composition_report_read(_member(), current, history=[previous, current])

    assert report.score.value == 67
    assert report.score.band == "intermediate"
    assert report.score.delta is None
    assert report.score.comparison_status == "incompatible_method"
    assert report.score.disclaimer == "Índice Cordex para acompanhamento individual; não representa diagnóstico clínico."


def test_v2_perimetry_keeps_current_and_previous_states_unambiguous() -> None:
    previous = _evaluation(datetime(2026, 8, 1, 12, tzinfo=UTC))
    previous.shoulders_cm = None
    previous.neck_cm = 39
    current = _evaluation(datetime(2026, 9, 1, 12, tzinfo=UTC))
    current.shoulders_cm = 100
    current.neck_cm = None

    report = build_body_composition_report_read(_member(), current, history=[previous, current])

    shoulders = _metric(report, "shoulders_cm")
    neck = _metric(report, "neck_cm")
    assert "body_measurement" in shoulders.display_roles
    assert shoulders.current.formatted_value == "100 cm"
    assert shoulders.previous is not None and shoulders.previous.value is None
    assert neck.current.value is None
    assert neck.previous is not None and neck.previous.formatted_value == "39 cm"

    html = render_premium_report_html(build_body_composition_premium_pdf_payload(report, technical=True))
    assert "Ombros" in html and "100 cm" in html
    assert "Primeira avaliação" in html
    assert "Pescoço" in html and "Não aferido nesta avaliação" in html


def test_implausible_perimetry_change_is_not_used_in_narrative() -> None:
    previous = _evaluation(datetime(2026, 8, 1, 12, tzinfo=UTC))
    previous.shoulders_cm = 112
    current = _evaluation(datetime(2026, 9, 1, 12, tzinfo=UTC))
    current.shoulders_cm = 12

    report = build_body_composition_report_read(_member(), current, history=[previous, current])
    shoulders = _metric(report, "shoulders_cm")

    assert shoulders.comparison_status == "incompatible_method"
    assert shoulders.delta is None
    assert shoulders.comparison_message == "Comparação suspensa — variação corporal improvável; revise as medidas registradas"
    assert "Ombros reduziu" not in (report.analysis_cordex or "")


def test_pdf_compares_perimetry_and_skinfolds_with_latest_available_measurement() -> None:
    measured = _evaluation(datetime(2026, 7, 1, 12, tzinfo=UTC))
    measured.measured_at = None
    measured.waist_cm = 94
    measured.skinfold_triceps_mm = 18
    intermediate = _evaluation(datetime(2026, 8, 1, 12, tzinfo=UTC))
    intermediate.waist_cm = None
    intermediate.skinfold_triceps_mm = None
    current = _evaluation(datetime(2026, 9, 1, 12, tzinfo=UTC))
    current.waist_cm = 90
    current.skinfold_triceps_mm = 15

    report = build_body_composition_report_read(
        _member(),
        current,
        history=[measured, intermediate, current],
    )

    waist = _metric(report, "waist_cm")
    triceps = _metric(report, "skinfold_triceps_mm")
    assert waist.previous is not None and waist.previous.value == 94
    assert waist.delta == -4
    assert "skinfold" in triceps.display_roles
    assert triceps.previous is not None and triceps.previous.value == 18
    assert triceps.delta == -3

    html = render_premium_report_html(build_body_composition_premium_pdf_payload(report, technical=True))
    assert "Dobras cutâneas" in html
    assert "Dobra tricipital" in html
    assert "Anterior: 18 mm · -3 mm" in html
    assert "Anterior: 94 cm &middot; -4 cm" in html


def test_anthropometric_pdf_contract_includes_skinfolds_from_snapshot() -> None:
    def assessment(measured_at: datetime, *, waist: float, triceps: float) -> SimpleNamespace:
        return SimpleNamespace(
            id=uuid4(),
            assessment_date=measured_at,
            created_at=measured_at,
            height_cm=180,
            weight_kg=85,
            bmi=26.2,
            body_fat_pct=15,
            fat_mass_kg=12.75,
            lean_mass_kg=72.25,
            waist_hip_ratio=0.9,
            sex_used_for_formula="male",
            age_used_for_formula=47,
            observations=None,
            waist_cm=waist,
            anthropometry_snapshot_json={
                "flags": [],
                "measurements": {
                    "waist_cm": {"consolidated_value": waist},
                    "skinfold_triceps_mm": {"consolidated_value": triceps},
                },
            },
            extra_data={},
        )

    previous = assessment(datetime(2026, 7, 1, 12, tzinfo=UTC), waist=94, triceps=18)
    current = assessment(datetime(2026, 8, 1, 12, tzinfo=UTC), waist=90, triceps=15)
    report = build_anthropometric_report_read(_member(), current, history=[previous, current])

    triceps = _metric(report, "skinfold_triceps_mm")
    assert triceps.current.value == 15
    assert triceps.previous is not None and triceps.previous.value == 18
    assert triceps.delta == -3


def test_history_eligibility_is_decided_per_series() -> None:
    first = _evaluation(datetime(2026, 6, 1, 12, tzinfo=UTC), weight=100, muscle_origin="reported")
    second = _evaluation(datetime(2026, 7, 1, 12, tzinfo=UTC), weight=95, muscle_origin="lee_2000")
    third = _evaluation(datetime(2026, 8, 1, 12, tzinfo=UTC), weight=90, muscle_origin="legacy_unknown")
    current = _evaluation(datetime(2026, 9, 1, 12, tzinfo=UTC), weight=85, muscle_origin="legacy_unknown")

    report = build_body_composition_report_read(_member(), current, history=[first, second, third, current])
    weight = next(series for series in report.history if series.key == "weight_kg")
    muscle = next(series for series in report.history if series.key == "muscle_mass_kg")

    assert weight.chart_eligible is True
    assert len(weight.points) == 4
    assert muscle.chart_eligible is False
    assert len(muscle.points) == 0
    assert muscle.excluded_points_count == 4


def test_future_legacy_report_keeps_values_but_disables_evolution() -> None:
    now = datetime.now(tz=UTC)
    previous = _evaluation(now - timedelta(days=30), weight=90)
    current = _evaluation(now + timedelta(days=10), weight=85)

    report = build_body_composition_report_read(_member(), current, history=[previous, current])

    assert report.date_consistency == "future_legacy"
    assert report.analysis_cordex is None
    assert report.score.delta is None
    assert report.score.comparison_status == "invalid_date"
    assert all(metric.delta is None for metric in report.metrics)
    assert all(metric.comparison_status == "invalid_date" for metric in report.metrics)
    assert all(not series.points for series in report.history)


def test_goals_can_be_unsafe_and_require_review_at_the_same_time() -> None:
    current = _evaluation(datetime.now(tz=UTC) - timedelta(days=1), muscle_control=-6.3)

    report = build_body_composition_report_read(_member(), current, history=[current])

    assert report.goals.status == "unsafe"
    assert report.goals.requires_review is True
    assert report.goals.values is not None
    assert "massa muscular" in report.goals.professional_message.lower()


def test_reference_metadata_distinguishes_equipment_protocol_and_clinical() -> None:
    current = _evaluation(datetime.now(tz=UTC) - timedelta(days=1))

    report = build_body_composition_report_read(_member(), current, history=[current])

    weight = _metric(report, "weight_kg")
    bmi = _metric(report, "bmi")
    body_fat = _metric(report, "body_fat_used_percent")
    assert (weight.reference_kind, weight.reference_label) == ("equipment", "Faixa técnica do equipamento")
    assert bmi.reference_kind == "clinical"
    assert bmi.reference_source == "OMS — classificação de IMC para adultos"
    assert body_fat.reference_kind == "protocol"
    assert body_fat.reference_source == "Cordex — protocolo operacional"


def test_new_payload_rejects_future_dates_in_sao_paulo() -> None:
    tomorrow = datetime.now(tz=SAO_PAULO).date() + timedelta(days=1)
    payload = BodyCompositionEvaluationCreate(
        evaluation_date=tomorrow,
        measured_at=datetime.combine(tomorrow, datetime.min.time(), tzinfo=SAO_PAULO),
        source="manual",
        weight_kg=82,
    )

    with pytest.raises(HTTPException) as exc_info:
        _validate_body_composition_payload(payload)

    assert exc_info.value.status_code == 422
    assert "futuro" in str(exc_info.value.detail).lower()


def test_naive_measured_at_is_interpreted_in_sao_paulo_and_stored_in_utc() -> None:
    payload = resolve_body_composition_persistence_fields({
        "evaluation_date": date(2026, 9, 15),
        "measured_at": datetime(2026, 9, 15, 9, 30),
        "weight_kg": 82,
    })

    assert payload["measured_at"] == datetime(2026, 9, 15, 12, 30, tzinfo=UTC)


def test_evaluation_date_without_time_does_not_invent_a_measured_hour() -> None:
    payload = resolve_body_composition_persistence_fields({
        "evaluation_date": date(2026, 9, 15),
        "weight_kg": 82,
    })

    assert "measured_at" not in payload


def test_report_with_date_only_does_not_present_an_invented_hour() -> None:
    current = _evaluation(datetime(2026, 9, 15, 12, tzinfo=UTC))
    current.measured_at = None
    current.evaluation_date = date(2026, 9, 15)

    report = build_body_composition_report_read(_member(), current, history=[current])
    html = render_premium_report_html(build_body_composition_premium_pdf_payload(report, technical=True))

    assert report.header.measured_at is None
    assert report.header.evaluation_date == date(2026, 9, 15)
    assert "15/09/2026" in html
    assert "15/09/2026 12:00" not in html


def test_payload_rejects_divergence_between_local_date_and_measured_at() -> None:
    payload = BodyCompositionEvaluationCreate(
        evaluation_date=date(2026, 9, 14),
        measured_at=datetime(2026, 9, 15, 1, 0, tzinfo=SAO_PAULO),
        source="manual",
        weight_kg=82,
    )

    with pytest.raises(HTTPException) as exc_info:
        _validate_body_composition_payload(payload)

    assert exc_info.value.status_code == 422
    assert "coincidir" in str(exc_info.value.detail).lower()


def test_pdf_html_consumes_v2_semantics_and_adds_history_with_one_prior_evaluation() -> None:
    previous = _evaluation(
        datetime(2026, 8, 1, 12, tzinfo=UTC),
        weight=99,
        muscle=62.4,
        muscle_origin="reported",
        bmr=1350,
        bmr_origin="reported",
    )
    current = _evaluation(
        datetime(2026, 9, 1, 12, tzinfo=UTC),
        weight=82.2,
        muscle=40,
        muscle_origin="legacy_unknown",
        bmr=1880,
        bmr_origin="legacy_unknown",
        notes=None,
    )
    report = build_body_composition_report_read(_member(), current, history=[previous, current])

    html = render_premium_report_html(build_body_composition_premium_pdf_payload(report, technical=True))

    assert "Avaliação nº 2" in html
    assert "linha de base" not in html.lower()
    assert "Score de composição corporal" in html
    assert "Faixa intermediária" in html
    assert "Análise Cordex" in html
    assert report.analysis_cordex in html
    assert "Comparação indisponível — métodos/fontes diferentes" in html
    assert "-22,4 kg" not in html
    assert "Sem observações registradas nesta avaliação." in html
    assert "UTC" not in html
    assert html.count('<section class="clinical-page') == 3
    assert "Comparação disponível a partir de uma avaliação anterior" in html


def test_pdf_paginates_eligible_history_series_in_groups_of_four() -> None:
    history = [
        _evaluation(datetime(2026, month, 1, 12, tzinfo=UTC), weight=100 - month)
        for month in (6, 7, 8, 9)
    ]
    report = build_body_composition_report_read(_member(), history[-1], history=history)

    html = render_premium_report_html(build_body_composition_premium_pdf_payload(report, technical=True))

    assert html.count('<section class="clinical-page') == 4
    assert "Evolução histórica" in html
    assert '<svg class="clinical-history-chart"' in html


def test_pdf_history_limits_rows_to_recent_unique_dates() -> None:
    history = [
        _evaluation(datetime(2026, 1, day, 12, tzinfo=UTC), weight=100 - day)
        for day in range(1, 16)
    ]
    report = build_body_composition_report_read(_member(), history[-1], history=history)

    html = render_premium_report_html(build_body_composition_premium_pdf_payload(report, technical=True))

    assert "01/01/2026" not in html
    assert "10/01/2026" in html
    assert "15/01/2026" in html
