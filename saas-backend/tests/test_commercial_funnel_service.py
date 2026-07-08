"""Tests for commercial_funnel_service (spec 053 / slot M1/funnel-api)."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from app.schemas.commercial_funnel import ConversionBreakdown
from app.services.commercial_funnel_service import (
    SAO_PAULO_TZ,
    _count_contacts,
    _count_responses,
    _count_risk_recovered,
    _week_window,
    get_weekly_funnel,
)

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
# Quarta-feira 2026-07-08 12:00 em São Paulo (15:00 UTC)
NOW = datetime(2026, 7, 8, 15, 0, 0, tzinfo=timezone.utc)


class TestWeekWindow:
    def test_current_week_starts_monday_sao_paulo(self):
        start, end = _week_window(NOW, 0)
        start_sp = start.astimezone(SAO_PAULO_TZ)
        assert start_sp.weekday() == 0  # segunda
        assert (start_sp.hour, start_sp.minute) == (0, 0)
        assert start_sp.date() == datetime(2026, 7, 6).date()
        assert end == NOW  # semana corrente termina em now

    def test_previous_week_offset(self):
        start, end = _week_window(NOW, -1)
        cur_start, _ = _week_window(NOW, 0)
        assert start == cur_start - timedelta(days=7)
        assert end == cur_start  # semana fechada: end = início da semana seguinte

    def test_window_is_utc_aware(self):
        start, end = _week_window(NOW, 0)
        assert start.tzinfo is not None
        assert end.tzinfo is not None


class TestCountContacts:
    def test_sums_messages_and_tasks(self):
        db = MagicMock()
        db.scalar.side_effect = [30, 12]  # mensagens outbound, tasks done
        start, end = _week_window(NOW, 0)
        assert _count_contacts(db, gym_id=GYM_ID, start=start, end=end) == 42

    def test_none_counts_become_zero(self):
        db = MagicMock()
        db.scalar.side_effect = [None, None]
        start, end = _week_window(NOW, 0)
        assert _count_contacts(db, gym_id=GYM_ID, start=start, end=end) == 0


class TestCountResponses:
    def test_returns_inbound_count(self):
        db = MagicMock()
        db.scalar.return_value = 18
        start, end = _week_window(NOW, 0)
        assert _count_responses(db, gym_id=GYM_ID, start=start, end=end) == 18


def _history_row(member_id, level, days_ago):
    return SimpleNamespace(
        member_id=member_id,
        level=level,
        recorded_at=NOW - timedelta(days=days_ago),
    )


def _db_with_history(green_ids, rows):
    db = MagicMock()
    ids_result = MagicMock()
    ids_result.all.return_value = green_ids
    rows_result = MagicMock()
    rows_result.all.return_value = rows
    db.scalars.side_effect = [ids_result, rows_result]
    return db


class TestCountRiskRecovered:
    def test_red_to_green_in_window_counts(self):
        member = uuid.uuid4()
        rows = [
            _history_row(member, "red", days_ago=5),
            _history_row(member, "green", days_ago=1),
        ]
        db = _db_with_history([member], rows)
        start, end = _week_window(NOW, 0)
        assert _count_risk_recovered(db, gym_id=GYM_ID, start=start, end=end) == 1

    def test_green_to_green_does_not_count(self):
        member = uuid.uuid4()
        rows = [
            _history_row(member, "green", days_ago=5),
            _history_row(member, "green", days_ago=1),
        ]
        db = _db_with_history([member], rows)
        start, end = _week_window(NOW, 0)
        assert _count_risk_recovered(db, gym_id=GYM_ID, start=start, end=end) == 0

    def test_member_counts_once_with_two_transitions(self):
        member = uuid.uuid4()
        rows = [
            _history_row(member, "yellow", days_ago=2),
            _history_row(member, "green", days_ago=1, ),
            _history_row(member, "red", days_ago=0.5),
            _history_row(member, "green", days_ago=0.1),
        ]
        db = _db_with_history([member], rows)
        start, end = _week_window(NOW, 0)
        assert _count_risk_recovered(db, gym_id=GYM_ID, start=start, end=end) == 1

    def test_no_green_rows_returns_zero_without_second_query(self):
        db = _db_with_history([], [])
        start, end = _week_window(NOW, 0)
        assert _count_risk_recovered(db, gym_id=GYM_ID, start=start, end=end) == 0
        assert db.scalars.call_count == 1


class TestGetWeeklyFunnel:
    @patch("app.services.commercial_funnel_service._count_conversions")
    @patch("app.services.commercial_funnel_service._count_responses")
    @patch("app.services.commercial_funnel_service._count_contacts")
    def test_composes_stages_with_previous_week(self, mock_contacts, mock_responses, mock_conversions):
        mock_contacts.side_effect = [42, 35]
        mock_responses.side_effect = [18, 11]
        mock_conversions.side_effect = [
            ConversionBreakdown(leads_won=2, members_joined=2, risk_recovered=1),
            ConversionBreakdown(leads_won=1, members_joined=1, risk_recovered=1),
        ]
        db = MagicMock()
        result = get_weekly_funnel(db, gym_id=GYM_ID, week_offset=0)
        assert result.contacts.value == 42
        assert result.contacts.previous_value == 35
        assert result.responses.value == 18
        assert result.responses.previous_value == 11
        assert result.conversions.value == 5
        assert result.conversions.previous_value == 3
        assert result.conversion_breakdown.leads_won == 2
        assert result.contacts.label == "Contatos feitos"
        assert result.week_offset == 0

    @patch("app.services.commercial_funnel_service._count_conversions")
    @patch("app.services.commercial_funnel_service._count_responses")
    @patch("app.services.commercial_funnel_service._count_contacts")
    def test_empty_week_returns_zeros(self, mock_contacts, mock_responses, mock_conversions):
        mock_contacts.side_effect = [0, 0]
        mock_responses.side_effect = [0, 0]
        mock_conversions.side_effect = [
            ConversionBreakdown(leads_won=0, members_joined=0, risk_recovered=0),
            ConversionBreakdown(leads_won=0, members_joined=0, risk_recovered=0),
        ]
        db = MagicMock()
        result = get_weekly_funnel(db, gym_id=GYM_ID, week_offset=0)
        assert result.contacts.value == 0
        assert result.responses.value == 0
        assert result.conversions.value == 0
        assert result.conversion_breakdown.risk_recovered == 0

    @patch("app.services.commercial_funnel_service._count_conversions")
    @patch("app.services.commercial_funnel_service._count_responses")
    @patch("app.services.commercial_funnel_service._count_contacts")
    def test_gym_id_propagated(self, mock_contacts, mock_responses, mock_conversions):
        mock_contacts.side_effect = [0, 0]
        mock_responses.side_effect = [0, 0]
        mock_conversions.side_effect = [
            ConversionBreakdown(leads_won=0, members_joined=0, risk_recovered=0),
            ConversionBreakdown(leads_won=0, members_joined=0, risk_recovered=0),
        ]
        db = MagicMock()
        get_weekly_funnel(db, gym_id=GYM_ID, week_offset=0)
        for mock_fn in (mock_contacts, mock_responses, mock_conversions):
            assert all(call.kwargs["gym_id"] == GYM_ID for call in mock_fn.call_args_list)
