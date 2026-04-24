from datetime import datetime, timezone
from types import SimpleNamespace

from app.services import report_service
from app.services.premium_report_service import (
    PremiumReportBranding,
    PremiumReportMetric,
    PremiumReportNarrative,
    PremiumReportPayload,
    PremiumReportSection,
    build_dashboard_report_payload,
    render_premium_report_html,
)
from tests.conftest import make_mock_db


def test_build_dashboard_report_payload_accepts_serialized_executive_dashboard(monkeypatch):
    monkeypatch.setattr(
        "app.services.premium_report_service.get_executive_dashboard",
        lambda db: {
            "total_members": 120,
            "active_members": 88,
            "mrr": 15432.5,
            "churn_rate": 3.2,
            "nps_avg": 61.4,
            "risk_distribution": {"green": 70, "yellow": 12, "red": 6},
        },
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_mrr_dashboard",
        lambda *_args, **_kwargs: [{"month": "2026-01", "value": 12000}, {"month": "2026-02", "value": 15432.5}],
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_churn_dashboard",
        lambda *_args, **_kwargs: [{"month": "2026-01", "churn_rate": 3.8}, {"month": "2026-02", "churn_rate": 3.2}],
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_growth_mom_dashboard",
        lambda *_args, **_kwargs: [{"month": "2026-01", "growth_mom": 1.5}, {"month": "2026-02", "growth_mom": 2.1}],
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_weekly_summary",
        lambda *_args, **_kwargs: {"checkins_this_week": 88, "checkins_delta_pct": 4.5, "new_registrations": 12},
    )

    payload = build_dashboard_report_payload(make_mock_db(scalar_returns=[None]), "executive", generated_by="Owner")

    assert payload.report_kind == "dashboard"
    assert payload.report_scope == "executive"
    assert payload.generated_by == "Owner"
    assert payload.sections[0].title == "Resumo executivo"
    assert any(metric.label == "MRR" and metric.value.startswith("R$") for metric in payload.sections[0].metrics)
    assert payload.sections[0].charts[0].title == "MRR recente"
    assert "Base com" in (payload.cover_summary or "")


def test_render_premium_report_html_renders_core_blocks():
    payload = PremiumReportPayload(
        report_kind="dashboard",
        report_scope="executive",
        title="Relatorio Executivo",
        subtitle="Leitura premium",
        generated_at=datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc),
        generated_by="Owner",
        version="premium-v1",
        branding=PremiumReportBranding(gym_name="Academia Piloto"),
        parameters={"dashboard": "executive"},
        cover_summary="Resumo da academia no periodo.",
        sections=[
            PremiumReportSection(
                title="Resumo executivo",
                metrics=[PremiumReportMetric("MRR", "R$ 10.000,00")],
                narratives=[PremiumReportNarrative("Leitura", "Tudo sob controle.")],
            )
        ],
        footer_note="Rodape de teste",
    )

    html = render_premium_report_html(payload)

    assert "Relatorio Executivo" in html
    assert "Academia Piloto" in html
    assert "MRR" in html
    assert "Tudo sob controle." in html
    assert "Rodape de teste" in html


def test_render_premium_report_html_uses_clinical_layout_for_body_composition():
    payload = PremiumReportPayload(
        report_kind="body_composition",
        report_scope="member_summary",
        title="Relatorio premium de bioimpedancia",
        subtitle="Erick Bedin",
        generated_at=datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc),
        generated_by="Sistema",
        version="premium-v3",
        branding=PremiumReportBranding(gym_name="Academia Piloto"),
        parameters={
            "technical": False,
            "report": {
                "header": {
                    "member_name": "Erick Bedin",
                    "gym_name": "Academia Piloto",
                    "trainer_name": "Automicai Owner",
                    "measured_at": "2026-04-14T10:00:00+00:00",
                    "age_years": 21,
                    "sex": "male",
                    "height_cm": 178,
                    "weight_kg": 84.5,
                },
                "primary_cards": [
                    {"key": "weight_kg", "label": "Peso", "formatted_value": "84,5 kg", "delta_absolute": -1.2, "unit": "kg"},
                    {"key": "body_fat_percent", "label": "% gordura corporal", "formatted_value": "23,0%", "delta_absolute": -1.8, "unit": "%"},
                ],
                "composition_metrics": [
                    {"key": "body_water_kg", "label": "Agua corporal", "formatted_value": "43,3 kg", "reference_min": 39, "reference_max": 48, "unit": "kg"},
                ],
                "muscle_fat_metrics": [
                    {"key": "weight_kg", "label": "Peso", "formatted_value": "84,5 kg", "value": 84.5, "reference_min": 65, "reference_max": 80, "status": "high"},
                ],
                "risk_metrics": [
                    {"key": "health_score", "label": "Health score", "formatted_value": "60", "value": 60, "status": "adequate"},
                    {"key": "bmi", "label": "IMC", "formatted_value": "26,7", "value": 26.7, "reference_min": 18.5, "reference_max": 24.9, "status": "high"},
                    {"key": "waist_hip_ratio", "label": "Relacao cintura-quadril", "formatted_value": "0,88", "value": 0.88, "reference_min": 0.75, "reference_max": 0.9, "status": "adequate"},
                    {"key": "visceral_fat_level", "label": "Gordura visceral", "formatted_value": "9", "value": 9, "reference_min": 1, "reference_max": 12, "status": "adequate"},
                    {"key": "physical_age", "label": "Idade fisica", "formatted_value": "28 anos", "value": 28, "status": "unknown"},
                ],
                "goal_metrics": [
                    {"key": "target_weight_kg", "label": "Peso-alvo", "formatted_value": "78 kg", "status": "unknown"},
                ],
                "comparison_rows": [
                    {
                        "key": "weight_kg",
                        "label": "Peso",
                        "previous_formatted": "85,7 kg",
                        "current_formatted": "84,5 kg",
                        "difference_absolute": -1.2,
                        "unit": "kg",
                        "trend": "down",
                    }
                ],
                "history_series": [
                    {
                        "key": "weight_kg",
                        "label": "Peso",
                        "unit": "kg",
                        "points": [
                            {"evaluation_date": "2026-03-10", "value": 85.7},
                            {"evaluation_date": "2026-04-14", "value": 84.5},
                        ],
                    }
                ],
                "insights": [
                    {
                        "key": "positive",
                        "title": "Reducao de gordura com preservacao muscular",
                        "message": "Houve reducao de gordura corporal sem perda relevante de massa muscular.",
                        "tone": "positive",
                        "reasons": ["% gordura caiu", "massa muscular preservada"],
                    }
                ],
                "teacher_notes": "Manter progressao de treino.",
                "methodological_note": "Comparacoes historicas sao mais confiaveis em condicoes semelhantes.",
                "data_quality_flags": ["ocr_low_confidence"],
                "parsing_confidence": 0.82,
            },
        },
        sections=[],
        footer_note="Rodape de teste",
    )

    html = render_premium_report_html(payload)

    assert "Analise da Composicao Corporal" in html
    assert "Pontuacao corporal" in html
    assert "Historico da Composicao Corporal" in html
    assert "Comparativo rapido" in html
    assert "Leitura final" in html
    assert "Erick Bedin" in html
    assert "OCR 82%" in html


def test_build_consolidated_dashboard_payload_includes_board_pack_sections(monkeypatch):
    monkeypatch.setattr(
        "app.services.premium_report_service.get_executive_dashboard",
        lambda *_args, **_kwargs: {
            "total_members": 120,
            "active_members": 96,
            "mrr": 18200.0,
            "churn_rate": 2.7,
            "nps_avg": 64.2,
            "risk_distribution": {"green": 80, "yellow": 12, "red": 4},
        },
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_operational_dashboard",
        lambda *_args, **_kwargs: {
            "realtime_checkins": 14,
            "inactive_7d_total": 23,
            "inactive_7d_items": [{"full_name": "Ana Silva", "risk_level": {"value": "red"}, "last_checkin_at": "2026-04-01"}],
            "birthday_today_total": 2,
            "birthday_today_items": [{"full_name": "Bruno Lima", "plan_name": "Plano Anual"}],
            "heatmap": [{"hour_bucket": 18, "total_checkins": 19}, {"hour_bucket": 7, "total_checkins": 11}],
        },
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_commercial_dashboard",
        lambda *_args, **_kwargs: {
            "pipeline": {"new": 7, "contacted": 4},
            "conversion_by_source": [{"source": "Instagram", "conversion_rate": 22.0, "won": 11, "total": 50}],
            "cac": 78.0,
            "stale_leads_total": 6,
            "stale_leads": [{"full_name": "Lead Parado", "stage": "contacted", "last_contact_at": "2026-04-01"}],
        },
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_financial_dashboard",
        lambda *_args, **_kwargs: {
            "monthly_revenue": [{"month": "2026-01", "value": 17000}, {"month": "2026-02", "value": 18200}],
            "delinquency_rate": 3.5,
            "projections": [{"horizon_months": 3, "projected_revenue": 19000}],
        },
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_retention_dashboard",
        lambda *_args, **_kwargs: {
            "red": {"total": 4, "items": [{"full_name": "Ana Silva", "risk_score": 88, "plan_name": "Plano Mensal"}]},
            "yellow": {"total": 12, "items": [{"full_name": "Bruno Lima", "risk_score": 63, "plan_name": "Plano Anual"}]},
            "nps_trend": [{"month": "2026-01", "average_score": 61.0}, {"month": "2026-02", "average_score": 64.0}],
            "mrr_at_risk": 4200.0,
            "avg_red_score": 84.0,
            "avg_yellow_score": 61.0,
            "churn_distribution": {"seasonal": 8, "onboarding_fragile": 3},
            "last_contact_map": {},
        },
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_mrr_dashboard",
        lambda *_args, **_kwargs: [{"month": "2026-01", "value": 17000}, {"month": "2026-02", "value": 18200}],
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_churn_dashboard",
        lambda *_args, **_kwargs: [{"month": "2026-01", "churn_rate": 3.0}, {"month": "2026-02", "churn_rate": 2.7}],
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_growth_mom_dashboard",
        lambda *_args, **_kwargs: [{"month": "2026-01", "growth_mom": 1.0}, {"month": "2026-02", "growth_mom": 2.0}],
    )
    monkeypatch.setattr(
        "app.services.premium_report_service.get_weekly_summary",
        lambda *_args, **_kwargs: {"checkins_this_week": 88, "checkins_delta_pct": 4.5, "new_registrations": 12},
    )

    payload = build_dashboard_report_payload(make_mock_db(scalar_returns=[None]), "consolidated", generated_by="Owner")

    assert payload.title == "Board Pack Consolidado"
    assert len(payload.sections) == 5
    assert payload.sections[0].charts[0].title == "MRR recente"
    assert payload.sections[-1].charts[0].title == "Curva de NPS"
    assert "Board pack do periodo" in (payload.cover_summary or "")


def test_build_retention_dashboard_payload_includes_nps_and_churn_distribution(monkeypatch):
    monkeypatch.setattr(
        "app.services.premium_report_service.get_retention_dashboard",
        lambda *_args, **_kwargs: {
            "red": {"total": 5, "items": [{"full_name": "Ana Silva", "risk_score": 90, "plan_name": "Plano Mensal"}]},
            "yellow": {"total": 8, "items": [{"full_name": "Bruno Lima", "risk_score": 67, "plan_name": "Plano Anual"}]},
            "nps_trend": [{"month": "2026-01", "average_score": 58.0}, {"month": "2026-02", "average_score": 63.0}],
            "mrr_at_risk": 5100.0,
            "avg_red_score": 81.5,
            "avg_yellow_score": 62.0,
            "churn_distribution": {"seasonal": 4, "mixed_pattern": 2},
            "last_contact_map": {},
        },
    )

    payload = build_dashboard_report_payload(make_mock_db(scalar_returns=[None]), "retention", generated_by="Owner")

    section = payload.sections[0]
    assert any(metric.label == "MRR em risco" for metric in section.metrics)
    assert [chart.title for chart in section.charts] == ["Curva de NPS", "Distribuicao por tipo de churn"]
    assert section.tables[1].title == "Fila amarela prioritária"


def test_generate_executive_pdf_uses_premium_renderer(monkeypatch):
    monkeypatch.setattr(
        report_service,
        "build_dashboard_report_payload",
        lambda *_args, **_kwargs: PremiumReportPayload(
            report_kind="dashboard",
            report_scope="executive",
            title="Relatorio Executivo",
            subtitle="Leitura premium",
            generated_at=datetime.now(tz=timezone.utc),
            generated_by="Owner",
            version="premium-v1",
            branding=PremiumReportBranding(gym_name="Academia Piloto"),
            parameters={"dashboard": "executive"},
            sections=[],
        ),
    )
    monkeypatch.setattr(report_service, "render_premium_report_pdf", lambda _payload: b"%PDF-1.4 premium")

    buffer, filename = report_service.generate_dashboard_pdf(make_mock_db(), "executive", generated_by="Owner")

    assert filename.startswith("report_executive_")
    assert buffer.getvalue().startswith(b"%PDF")


def test_send_monthly_reports_uses_premium_pipeline(monkeypatch):
    monkeypatch.setattr(
        report_service,
        "generate_dashboard_pdf",
        lambda *_args, **_kwargs: (SimpleNamespace(getvalue=lambda: b"%PDF-1.4 monthly"), "report_consolidated.pdf"),
    )
    monkeypatch.setattr(
        report_service,
        "send_email_with_attachment_result",
        lambda *args, **kwargs: SimpleNamespace(sent=True, blocked=False, reason=None),
    )

    db = make_mock_db(
        scalars_returns=[
            SimpleNamespace(email="owner@teste.com"),
            SimpleNamespace(email="manager@teste.com"),
        ]
    )

    result = report_service.send_monthly_reports(db)

    assert result == {"sent": 2, "failed": 0, "blocked": 0, "blocked_reasons": {}, "total_recipients": 2}


def test_execute_monthly_reports_dispatch_job_logs_completion_without_commit(monkeypatch):
    audit_calls = []
    monkeypatch.setattr(
        report_service,
        "send_monthly_reports",
        lambda *_args, **_kwargs: {"sent": 2, "failed": 0, "total_recipients": 2},
    )
    monkeypatch.setattr(
        report_service,
        "log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    db = SimpleNamespace(get=lambda *_args, **_kwargs: SimpleNamespace(id="user-1"), flush=lambda: None)
    result = report_service.execute_monthly_reports_dispatch_job(
        db,
        gym_id="gym-1",
        job_id="job-1",
        requested_by_user_id="user-1",
    )

    assert result["sent"] == 2
    assert audit_calls[0]["action"] == "monthly_reports_dispatched"
