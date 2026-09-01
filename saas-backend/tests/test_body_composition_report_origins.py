from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.assessment_anthropometry_report_service import build_anthropometric_report_payload
from app.services.body_composition_report_service import (
    body_composition_origin_label,
    build_body_composition_premium_pdf_payload,
    build_body_composition_report_read,
)
from app.services.premium_report_service import render_premium_report_html


@pytest.mark.parametrize(
    ("origin", "metric_key", "expected"),
    [
        ("reported", "muscle_mass_kg", "Medido/informado no exame"),
        ("schofield_hw_1985", "basal_metabolic_rate_kcal", "TMB estimada por Schofield-HW (1985)"),
        ("mifflin_st_jeor_1990", "basal_metabolic_rate_kcal", "TMB estimada por Mifflin-St Jeor (1990)"),
        ("lee_2000", "muscle_mass_kg", "Massa muscular estimada por Lee (2000)"),
        ("poortmans_2005", "muscle_mass_kg", "Massa muscular estimada por Poortmans (2005)"),
        ("legacy_unknown", "muscle_mass_kg", "Valor historico - origem nao identificada"),
        ("unavailable", "muscle_mass_kg", "Indisponivel - medicao necessaria"),
    ],
)
def test_calculation_origin_labels_are_public_and_unambiguous(origin: str, metric_key: str, expected: str):
    assert body_composition_origin_label(origin, metric_key=metric_key) == expected


def _bio_evaluation(
    *,
    measured_at: datetime,
    muscle_mass_kg: float,
    muscle_mass_origin: str,
    basal_metabolic_rate_kcal: float,
    basal_metabolic_rate_origin: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        evaluation_date=measured_at.date(),
        measured_at=measured_at,
        created_at=measured_at,
        age_years=15,
        sex="female",
        height_cm=165,
        weight_kg=58,
        body_fat_percent=22,
        body_fat_used_percent=22,
        body_fat_range_min=18,
        body_fat_range_max=25,
        body_fat_used_source="anthropometry",
        preferred_body_fat_source="anthropometry",
        body_fat_method="skinfold_protocol",
        body_fat_anthropometric_percent=22,
        fat_mass_estimated_kg=12.76,
        lean_mass_estimated_kg=45.24,
        fat_free_mass_kg=45.24,
        muscle_mass_kg=muscle_mass_kg,
        muscle_mass_origin=muscle_mass_origin,
        skeletal_muscle_kg=None,
        visceral_fat_level=None,
        waist_hip_ratio=0.78,
        bmi=21.3,
        basal_metabolic_rate_kcal=basal_metabolic_rate_kcal,
        basal_metabolic_rate_origin=basal_metabolic_rate_origin,
        notes=None,
        reviewed_manually=True,
        parsing_confidence=1,
        data_quality_flags_json=[],
        measured_ranges_json={},
    )


def test_report_cards_history_and_pdf_keep_metric_provenance_and_weight_header_first():
    member = SimpleNamespace(
        full_name="Aluna Teste",
        birthdate=date(2011, 1, 1),
        gym=SimpleNamespace(name="Academia Teste"),
        assigned_user=None,
    )
    previous = _bio_evaluation(
        measured_at=datetime(2026, 7, 1, 12, tzinfo=UTC),
        muscle_mass_kg=21.5,
        muscle_mass_origin="reported",
        basal_metabolic_rate_kcal=1350,
        basal_metabolic_rate_origin="reported",
    )
    current = _bio_evaluation(
        measured_at=datetime(2026, 8, 1, 12, tzinfo=UTC),
        muscle_mass_kg=22.1,
        muscle_mass_origin="poortmans_2005",
        basal_metabolic_rate_kcal=1375,
        basal_metabolic_rate_origin="schofield_hw_1985",
    )

    report = build_body_composition_report_read(member, current, history=[previous, current])
    muscle_card = next(card for card in report.primary_cards if card.key == "muscle_mass_kg")
    bmr_card = next(card for card in report.primary_cards if card.key == "basal_metabolic_rate_kcal")
    muscle_comparison = next(row for row in report.comparison_rows if row.key == "muscle_mass_kg")
    muscle_history = next(series for series in report.history_series if series.key == "muscle_mass_kg")

    assert muscle_card.origin == "poortmans_2005"
    assert muscle_card.origin_label == "Massa muscular estimada por Poortmans (2005)"
    assert bmr_card.origin == "schofield_hw_1985"
    assert bmr_card.origin_label == "TMB estimada por Schofield-HW (1985)"
    assert muscle_comparison.previous_origin == "reported"
    assert muscle_comparison.current_origin == "poortmans_2005"
    assert [point.origin for point in muscle_history.points] == ["reported", "poortmans_2005"]

    html = render_premium_report_html(build_body_composition_premium_pdf_payload(report, technical=True))
    weight_meta = html.index('<article class="clinical-meta-card clinical-meta-prominent">')

    assert html.index("Altura") < weight_meta < html.index("Idade")
    assert weight_meta < html.index('<section class="clinical-cover-evaluation-grid">')
    assert "Data / hora" in html
    assert "grid-template-columns: repeat(7, minmax(0, 1fr))" in html
    assert "Massa muscular estimada por Poortmans (2005)" in html
    assert "TMB estimada por Schofield-HW (1985)" in html
    assert "Medido/informado no exame" in html


def test_anthropometry_payload_uses_poortmans_and_schofield_instead_of_hardcoded_lee():
    assessed_at = datetime(2026, 8, 27, 12, tzinfo=UTC)
    assessment = SimpleNamespace(
        id=uuid4(),
        assessment_date=assessed_at,
        created_at=assessed_at,
        measurement_protocol="slaughter_1988_girls_8_17",
        formula_version="anthropometry-v3:slaughter:poortmans-2005:schofield-hw-1985",
        assessment_method="manual_anthropometry",
        record_origin="cordex",
        sex_used_for_formula="female",
        age_used_for_formula=15,
        height_cm=165,
        weight_kg=58,
        bmi=21.3,
        body_fat_pct=22,
        fat_mass_kg=12.76,
        lean_mass_kg=45.24,
        muscle_mass_kg=22.1,
        muscle_mass_origin="poortmans_2005",
        waist_hip_ratio=0.78,
        basal_metabolic_rate=1375,
        basal_metabolic_rate_origin="schofield_hw_1985",
        observations=None,
        anthropometry_snapshot_json={"flags": [], "measurements": {}},
        extra_data={},
    )
    member = SimpleNamespace(
        full_name="Aluna Pediatrica",
        birthdate=date(2011, 1, 1),
        gym=SimpleNamespace(name="Academia Teste"),
        assigned_user=None,
    )

    payload = build_anthropometric_report_payload(member, assessment)
    report = payload.parameters["report"]
    metrics = [
        metric
        for section in ("primary_cards", "composition_metrics", "muscle_fat_metrics")
        for metric in report[section]
    ]
    muscle_metric = next(metric for metric in metrics if metric["key"] == "muscle_mass_kg")
    bmr_metric = next(metric for metric in metrics if metric["key"] == "basal_metabolic_rate_kcal")
    html = render_premium_report_html(payload)

    assert payload.parameters["muscle_mass_formula"] == "Poortmans et al. (2005)"
    assert payload.parameters["basal_metabolic_rate_formula"] == "Schofield-HW (1985)"
    assert muscle_metric["origin"] == "poortmans_2005"
    assert muscle_metric["source_label"] == "Massa muscular estimada por Poortmans (2005)"
    assert bmr_metric["origin"] == "schofield_hw_1985"
    assert bmr_metric["source_label"] == "TMB estimada por Schofield-HW (1985)"
    assert "Poortmans et al. (2005)" in html
    assert "Schofield-HW (1985)" in html
    assert "Lee et al. (2000)" not in html
