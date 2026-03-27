from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID
from unittest.mock import MagicMock, patch


def test_create_assessment_clears_queue_resolution_flags():
    from app.services.assessment_service import create_assessment

    member_id = UUID("33333333-3333-3333-3333-333333333333")
    evaluator_id = UUID("44444444-4444-4444-4444-444444444444")
    member = SimpleNamespace(
        id=member_id,
        extra_data={
            "assessment_queue_resolution": "scheduled",
            "assessment_queue_resolution_note": "Ja foi marcada",
            "assessment_queue_resolution_at": "2026-03-27T10:00:00+00:00",
        },
    )

    db = MagicMock()
    db.scalar.return_value = 0

    with (
        patch("app.services.assessment_service.get_member_or_404", return_value=member),
        patch("app.services.assessment_service._calculate_next_assessment_due", return_value=datetime(2026, 6, 25, tzinfo=timezone.utc).date()),
        patch("app.services.assessment_service.generate_ai_insights"),
        patch("app.services.assessment_service.sync_assessment_intelligence_tasks"),
    ):
        create_assessment(
            db,
            member_id,
            evaluator_id,
            {"assessment_date": "2026-03-27T12:00:00+00:00"},
            commit=False,
        )

    assert "assessment_queue_resolution" not in member.extra_data
    assert "assessment_queue_resolution_note" not in member.extra_data
    assert "assessment_queue_resolution_at" not in member.extra_data
