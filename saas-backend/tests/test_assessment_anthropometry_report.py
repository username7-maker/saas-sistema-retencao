import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.services.assessment_anthropometry_report_service import build_anthropometric_report_payload


def test_report_payload_identifies_anthropometry_and_omits_unavailable_cards() -> None:
    assessment = SimpleNamespace(
        id=uuid.uuid4(),
        assessment_date=datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc),
        next_assessment_due=date(2026, 10, 14),
        assessment_number=2,
        measurement_protocol="petroski_1995_male_18_66",
        formula_version="anthropometry-v1:petroski_1995_male_18_66",
        weight_kg=Decimal("73.60"),
        height_cm=Decimal("177.00"),
        bmi=Decimal("23.49"),
        body_fat_pct=Decimal("12.49"),
        fat_mass_kg=Decimal("9.19"),
        lean_mass_kg=Decimal("64.41"),
        waist_hip_ratio=Decimal("0.83"),
        basal_metabolic_rate=Decimal("1737.25"),
        observations="Sem bioimpedancia.",
        anthropometry_snapshot_json={
            "indicator_origins": {
                "body_fat_pct": "anthropometry_calculated",
                "muscle_mass_kg": "unavailable",
            },
            "measurements": {
                "skinfold_triceps_mm": {"attempts": ["9.0", "9.0"], "consolidated_value": "9.0", "unit": "mm", "side": "right"}
            },
            "unavailable_metrics": {
                "muscle_mass_kg": "Massa muscular: indisponivel nesta modalidade"
            },
        },
    )
    member = SimpleNamespace(id=uuid.uuid4(), full_name="Aluno Teste")

    payload = build_anthropometric_report_payload(member, assessment, generated_by="Prof Teste")

    assert payload.title == "Avaliacao antropometrica"
    assert payload.report_kind == "anthropometric_assessment"
    assert payload.parameters["protocol"] == "petroski_1995_male_18_66"
    metric_labels = [metric.label for section in payload.sections for metric in section.metrics]
    assert "Massa muscular" not in metric_labels
    assert any(table.title == "Metricas indisponiveis" for section in payload.sections for table in section.tables)
    assert all(metric.value != "0" for section in payload.sections for metric in section.metrics)
