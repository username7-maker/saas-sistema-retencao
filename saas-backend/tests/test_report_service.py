from types import SimpleNamespace

from app.services import report_service
from tests.conftest import make_mock_db


def test_generate_executive_pdf_accepts_serialized_dashboard(monkeypatch):
    monkeypatch.setattr(
        report_service,
        "get_executive_dashboard",
        lambda db: {
            "total_members": 120,
            "active_members": 88,
            "mrr": 15432.5,
            "churn_rate": 3.2,
            "nps_avg": 61.4,
            "risk_distribution": {"green": 70, "yellow": 12, "red": 6},
        },
    )

    buffer, filename = report_service.generate_dashboard_pdf(make_mock_db(), "executive")

    assert filename.startswith("report_executive_")
    assert buffer.getvalue().startswith(b"%PDF")


def test_send_monthly_reports_accepts_serialized_consolidated_sources(monkeypatch):
    monkeypatch.setattr(
        report_service,
        "get_executive_dashboard",
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
        report_service,
        "get_operational_dashboard",
        lambda db, page=1, page_size=10: {
            "realtime_checkins": 4,
            "inactive_7d_total": 12,
            "inactive_7d_items": [],
        },
    )
    monkeypatch.setattr(
        report_service,
        "get_commercial_dashboard",
        lambda db: {
            "cac": 42.0,
            "pipeline": {"won": 3, "new": 5},
            "conversion_by_source": [],
        },
    )
    monkeypatch.setattr(
        report_service,
        "get_financial_dashboard",
        lambda db: {
            "delinquency_rate": 1.2,
            "monthly_revenue": [{"value": 15432.5}],
            "projections": [],
        },
    )
    monkeypatch.setattr(
        report_service,
        "get_retention_dashboard",
        lambda db, red_page=1, yellow_page=1, page_size=10: {
            "red": {"total": 6, "items": []},
            "yellow": {"total": 12, "items": []},
        },
    )
    monkeypatch.setattr(report_service, "send_email_with_attachment", lambda *args, **kwargs: True)

    db = make_mock_db(
        scalars_returns=[
            SimpleNamespace(email="owner@teste.com"),
            SimpleNamespace(email="manager@teste.com"),
        ]
    )

    result = report_service.send_monthly_reports(db)

    assert result == {"sent": 2, "failed": 0, "total_recipients": 2}
