from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.services.premium_report_service import (
    PremiumReportBranding,
    PremiumReportMetric,
    PremiumReportNarrative,
    PremiumReportPayload,
    PremiumReportSection,
    PremiumReportTable,
    render_premium_report_pdf,
)


def build_anthropometric_report_payload(
    member: Any,
    assessment: Any,
    *,
    generated_by: str | None = None,
) -> PremiumReportPayload:
    snapshot = getattr(assessment, "anthropometry_snapshot_json", None) or {}
    protocol_key = getattr(assessment, "measurement_protocol", None)
    formula_version = getattr(assessment, "formula_version", None)
    unavailable = snapshot.get("unavailable_metrics") if isinstance(snapshot, dict) else {}
    measurements = snapshot.get("measurements", {}) if isinstance(snapshot, dict) else {}
    origins = snapshot.get("indicator_origins", {}) if isinstance(snapshot, dict) else {}

    metrics = _metrics_from_assessment(assessment)
    measurement_rows = [
        [
            _field_label(field),
            ", ".join(item.get("attempts", [])),
            str(item.get("consolidated_value") or "-"),
            str(item.get("unit") or "-"),
            str(item.get("side") or "-"),
        ]
        for field, item in sorted(measurements.items())
        if isinstance(item, dict)
    ]
    unavailable_rows = [
        [_metric_label(key), str(value)]
        for key, value in sorted((unavailable or {}).items())
    ]
    origin_rows = [
        [_metric_label(key), _origin_label(value)]
        for key, value in sorted((origins or {}).items())
    ]

    sections = [
        PremiumReportSection(
            title="Resultados calculados",
            subtitle="Indicadores oficiais desta avaliacao antropometrica.",
            metrics=metrics,
            narratives=[
                PremiumReportNarrative(
                    "Metodo",
                    (
                        f"Protocolo {protocol_key or '-'} na versao {formula_version or '-'}. "
                        "Os resultados sao estimativas antropometricas, nao medidas de bioimpedancia."
                    ),
                    tone="neutral",
                )
            ],
        ),
        PremiumReportSection(
            title="Medidas e auditoria",
            subtitle="Tentativas, consolidacao e origem de cada indicador.",
            tables=[
                PremiumReportTable(
                    title="Tentativas registradas",
                    columns=["Medida", "Tentativas", "Valor oficial", "Unidade", "Lado"],
                    rows=measurement_rows,
                ),
                PremiumReportTable(
                    title="Origem dos indicadores",
                    columns=["Indicador", "Origem"],
                    rows=origin_rows,
                ),
                PremiumReportTable(
                    title="Metricas indisponiveis",
                    columns=["Metrica", "Status"],
                    rows=unavailable_rows,
                ),
            ],
        ),
    ]

    return PremiumReportPayload(
        report_kind="anthropometric_assessment",
        report_scope="member_summary",
        title="Avaliacao antropometrica",
        subtitle="Avaliacao sem bioimpedancia",
        generated_at=datetime.now(tz=timezone.utc),
        generated_by=generated_by,
        version="anthropometry-report-v1",
        branding=PremiumReportBranding(),
        parameters={
            "protocol": protocol_key,
            "formula_version": formula_version,
            "assessment_method": getattr(assessment, "assessment_method", None),
            "record_origin": getattr(assessment, "record_origin", None),
        },
        entity_id=str(getattr(member, "id", "")),
        evaluation_id=str(getattr(assessment, "id", "")),
        subject_name=getattr(member, "full_name", None),
        cover_summary=(
            "Relatorio gerado a partir de medidas manuais e protocolo antropometrico. "
            "Campos exclusivos da bioimpedancia permanecem indisponiveis."
        ),
        sections=sections,
        footer_note="Massa livre de gordura nao e massa muscular. Nenhuma metrica exclusiva da bioimpedancia foi inferida.",
    )


def generate_anthropometric_assessment_pdf(
    member: Any,
    assessment: Any,
    *,
    generated_by: str | None = None,
) -> tuple[bytes, str]:
    payload = build_anthropometric_report_payload(member, assessment, generated_by=generated_by)
    pdf = render_premium_report_pdf(payload)
    assessed_at = getattr(assessment, "assessment_date", None)
    if isinstance(assessed_at, datetime):
        date_slug = assessed_at.date().isoformat()
    else:
        date_slug = datetime.now(tz=timezone.utc).date().isoformat()
    member_slug = _slug(getattr(member, "full_name", "aluno"))
    filename = f"avaliacao_antropometrica_{member_slug}_{date_slug}_{getattr(assessment, 'id')}.pdf"
    return pdf, filename


def _metrics_from_assessment(assessment: Any) -> list[PremiumReportMetric]:
    candidates = [
        ("Peso", getattr(assessment, "weight_kg", None), "kg"),
        ("Altura", getattr(assessment, "height_cm", None), "cm"),
        ("IMC", getattr(assessment, "bmi", None), ""),
        ("Gordura corporal", getattr(assessment, "body_fat_pct", None), "%"),
        ("Massa de gordura", getattr(assessment, "fat_mass_kg", None), "kg"),
        ("Massa livre de gordura", getattr(assessment, "lean_mass_kg", None), "kg"),
        ("Relacao cintura-quadril", getattr(assessment, "waist_hip_ratio", None), ""),
        ("TMB estimada", getattr(assessment, "basal_metabolic_rate", None), "kcal"),
    ]
    return [
        PremiumReportMetric(label, _format_metric(value, unit), hint="antropometria", tone="neutral")
        for label, value, unit in candidates
        if value is not None
    ]


def _format_metric(value: Any, unit: str) -> str:
    number = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"{number}{f' {unit}' if unit else ''}"


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
