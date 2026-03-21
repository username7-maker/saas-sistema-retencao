"""Tests for weekly briefing tenant isolation and WhatsApp instance routing."""
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.weekly_briefing_service import (
    _collect_weekly_metrics,
    generate_and_send_weekly_briefing,
)


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def test_collect_metrics_passes_gym_id_to_queries():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(tz=timezone.utc)
    db = MagicMock()
    db.scalar.side_effect = [10, 8, 3, Decimal("500.00"), 100]

    result = _collect_weekly_metrics(db, GYM_ID, now, now - timedelta(days=7), now - timedelta(days=14))

    assert db.scalar.call_count == 5
    assert result["checkins_this_week"] == 10
    assert result["total_active"] == 100
    for call in db.scalar.call_args_list:
        params = call.args[0].compile().params
        assert any(value == GYM_ID for value in params.values())


def test_briefing_uses_gym_instance():
    db = MagicMock()
    db.scalar.side_effect = [10, 8, 3, Decimal("500.00"), 100]
    db.scalars.return_value.all.return_value = [
        SimpleNamespace(id=uuid.uuid4(), gym_id=GYM_ID, phone="11999990001")
    ]
    captured: list[dict] = []

    with patch(
        "app.services.weekly_briefing_service.get_gym_instance",
        return_value="gym_abc123",
    ), patch(
        "app.services.weekly_briefing_service.send_whatsapp_sync",
        side_effect=lambda *args, **kwargs: (
            captured.append(kwargs),
            SimpleNamespace(status="sent"),
        )[1],
    ):
        result = generate_and_send_weekly_briefing(db, GYM_ID)

    assert result["briefing_sent_to"] == 1
    assert captured[0]["instance"] == "gym_abc123"


def test_briefing_passes_none_instance_when_disconnected():
    db = MagicMock()
    db.scalar.side_effect = [10, 8, 3, Decimal("500.00"), 100]
    db.scalars.return_value.all.return_value = [
        SimpleNamespace(id=uuid.uuid4(), gym_id=GYM_ID, phone="11999990001")
    ]
    captured: list[dict] = []

    with patch(
        "app.services.weekly_briefing_service.get_gym_instance",
        return_value=None,
    ), patch(
        "app.services.weekly_briefing_service.send_whatsapp_sync",
        side_effect=lambda *args, **kwargs: (
            captured.append(kwargs),
            SimpleNamespace(status="skipped"),
        )[1],
    ):
        generate_and_send_weekly_briefing(db, GYM_ID)

    assert captured[0]["instance"] is None
