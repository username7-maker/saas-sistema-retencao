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
        waist_cm=Decimal("80.00"),
        hip_cm=Decimal("96.00"),
        chest_cm=Decimal("98.00"),
        arm_cm=Decimal("32.00"),
        thigh_cm=Decimal("58.00"),
        waist_hip_ratio=Decimal("0.83"),
        basal_metabolic_rate=Decimal("1737.25"),
        observations="Sem bioimpedancia.",
        sex_used_for_formula="male",
        age_used_for_formula=22,
        extra_data={
            "perimetry_evolution": {
                "shoulders_cm": "112.0",
                "right_arm_relaxed_cm": "32.0",
                "left_arm_relaxed_cm": "31.8",
            }
        },
        anthropometry_snapshot_json={
            "indicator_origins": {
                "body_fat_pct": "anthropometry_calculated",
                "muscle_mass_kg": "unavailable",
            },
            "measurements": {
                "skinfold_triceps_mm": {"attempts": ["9.0", "9.0"], "consolidated_value": "9.0", "unit": "mm", "side": "right"},
                "shoulders_cm": {"attempts": ["112.0", "112.0"], "consolidated_value": "112.0", "unit": "cm", "side": "right"},
            },
            "unavailable_metrics": {
                "muscle_mass_kg": "Massa muscular: indisponivel nesta modalidade"
            },
        },
    )
    member = SimpleNamespace(id=uuid.uuid4(), full_name="Aluno Teste")

    payload = build_anthropometric_report_payload(member, assessment, generated_by="Prof Teste")

    assert payload.title == "Relatorio premium de avaliacao antropometrica"
    assert payload.report_kind == "body_composition"
    assert payload.parameters["protocol"] == "petroski_1995_male_18_66"
    assert payload.parameters["assessment_method"] == "manual_anthropometry"
    report = payload.parameters["report"]
    assert report["body_fat_context"]["used_source"] == "anthropometry"
    assert any(row["key"] == "shoulders_cm" and row["current_value"] == 112.0 for row in report["measurement_rows"])
    metric_labels = [metric["label"] for metric in report["primary_cards"] + report["composition_metrics"] + report["muscle_fat_metrics"]]
    assert "Massa muscular" not in metric_labels
    assert payload.parameters["composition_detail_subtitle"].startswith("Valores separados por origem: medidas manuais")
