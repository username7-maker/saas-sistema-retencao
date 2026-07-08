"""Tests for daily_cockpit_service (spec 053 / slot M1/cockpit-api)."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.enums import LeadStage, MemberStatus, RiskLevel, TaskPriority, TaskStatus
from app.services.daily_cockpit_service import (
    LIST_CAP,
    OPEN_LEAD_STAGES,
    _actions_today,
    _attention_reason,
    _end_of_today_utc,
    _followup_reason,
    _leads_needing_followup,
    _members_attention,
    _triage_pending_count,
    get_daily_cockpit,
)

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime(2026, 7, 8, 15, 0, 0, tzinfo=timezone.utc)


def _db(scalar_value=0, scalars_list=None):
    db = MagicMock()
    db.scalar.return_value = scalar_value
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = scalars_list or []
    db.scalars.return_value = mock_scalars
    return db


def _lead(days_ago: int | None, stage=LeadStage.CONTACT):
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Lead Teste",
        phone="11988887777",
        stage=stage,
        last_contact_at=None if days_ago is None else NOW - timedelta(days=days_ago),
    )


def _member(risk=RiskLevel.RED, days_ago: int | None = 12, retention_stage="recovery"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Aluno Teste",
        risk_level=risk,
        retention_stage=retention_stage,
        last_checkin_at=None if days_ago is None else NOW - timedelta(days=days_ago),
    )


def _task(due_delta_hours: int, member=None, lead=None, priority=TaskPriority.HIGH):
    return SimpleNamespace(
        id=uuid.uuid4(),
        title="Ligar pro aluno",
        priority=priority,
        due_date=NOW + timedelta(hours=due_delta_hours),
        member=member,
        lead=lead,
    )


class TestOpenLeadStages:
    def test_excludes_won_and_lost(self):
        assert LeadStage.WON not in OPEN_LEAD_STAGES
        assert LeadStage.LOST not in OPEN_LEAD_STAGES
        assert LeadStage.NEW in OPEN_LEAD_STAGES


class TestFollowupReason:
    def test_never_contacted(self):
        assert _followup_reason(None) == "Nunca contatado"

    def test_singular_and_plural(self):
        assert _followup_reason(1) == "Sem contato há 1 dia"
        assert _followup_reason(3) == "Sem contato há 3 dias"

    def test_less_than_one_day(self):
        assert _followup_reason(0) == "Último contato há menos de 1 dia"


class TestLeadsNeedingFollowup:
    def test_maps_lead_fields(self):
        lead = _lead(days_ago=3)
        db = _db(scalar_value=17, scalars_list=[lead])
        items, total = _leads_needing_followup(db, gym_id=GYM_ID, now=NOW)
        assert total == 17
        assert len(items) == 1
        item = items[0]
        assert item.lead_id == lead.id
        assert item.stage == "contact"
        assert item.days_since_contact == 3
        assert item.reason == "Sem contato há 3 dias"
        assert item.href == "/crm"

    def test_never_contacted_lead(self):
        db = _db(scalar_value=1, scalars_list=[_lead(days_ago=None)])
        items, _ = _leads_needing_followup(db, gym_id=GYM_ID, now=NOW)
        assert items[0].days_since_contact is None
        assert items[0].reason == "Nunca contatado"


class TestAttentionReason:
    def test_days_and_stage(self):
        assert _attention_reason("red", "recovery", 12) == "12 dias sem treinar · estágio recuperação"

    def test_no_checkin_recorded(self):
        assert _attention_reason("yellow", None, None) == "Sem check-in registrado"

    def test_fallback_by_level(self):
        assert _attention_reason("red", None, 0) == "Risco alto"
        assert _attention_reason("yellow", None, 0) == "Risco moderado"


class TestMembersAttention:
    def test_maps_member_fields(self):
        member = _member()
        db = _db(scalar_value=23, scalars_list=[member])
        items, total = _members_attention(db, gym_id=GYM_ID, now=NOW)
        assert total == 23
        item = items[0]
        assert item.member_id == member.id
        assert item.risk_level == "red"
        assert item.retention_stage == "recovery"
        assert item.days_without_checkin == 12
        assert item.reason == "12 dias sem treinar · estágio recuperação"
        assert item.href == "/dashboard/retention"


class TestActionsToday:
    def test_overdue_flag_and_target_member(self):
        member = SimpleNamespace(full_name="Aluno Alvo")
        overdue_task = _task(due_delta_hours=-24, member=member)
        db = _db(scalar_value=6, scalars_list=[overdue_task])
        items, total = _actions_today(db, gym_id=GYM_ID, now=NOW)
        assert total == 6
        item = items[0]
        assert item.overdue is True
        assert item.target_name == "Aluno Alvo"
        assert item.priority == "high"
        assert item.href == "/tasks"

    def test_future_today_not_overdue_and_lead_target(self):
        lead = SimpleNamespace(full_name="Lead Alvo")
        task = _task(due_delta_hours=3, member=None, lead=lead)
        db = _db(scalar_value=1, scalars_list=[task])
        items, _ = _actions_today(db, gym_id=GYM_ID, now=NOW)
        assert items[0].overdue is False
        assert items[0].target_name == "Lead Alvo"

    def test_no_target(self):
        task = _task(due_delta_hours=1, member=None, lead=None)
        db = _db(scalar_value=1, scalars_list=[task])
        items, _ = _actions_today(db, gym_id=GYM_ID, now=NOW)
        assert items[0].target_name is None


class TestEndOfToday:
    def test_end_of_today_is_after_now(self):
        end = _end_of_today_utc(NOW)
        assert end > NOW
        assert end.tzinfo is not None


class TestTriagePendingCount:
    def test_returns_count(self):
        db = MagicMock()
        db.scalar.return_value = 4
        assert _triage_pending_count(db, gym_id=GYM_ID) == 4

    def test_none_becomes_zero(self):
        db = MagicMock()
        db.scalar.return_value = None
        assert _triage_pending_count(db, gym_id=GYM_ID) == 0


class TestGetDailyCockpit:
    @patch("app.services.daily_cockpit_service._triage_pending_count", return_value=4)
    @patch("app.services.daily_cockpit_service._actions_today", return_value=([], 6))
    @patch("app.services.daily_cockpit_service._members_attention", return_value=([], 23))
    @patch("app.services.daily_cockpit_service._leads_needing_followup", return_value=([], 17))
    def test_composes_response(self, mock_leads, mock_members, mock_actions, mock_triage):
        db = MagicMock()
        result = get_daily_cockpit(db, gym_id=GYM_ID)
        assert result.counts.leads_followup == 17
        assert result.counts.members_attention == 23
        assert result.counts.actions_today == 6
        assert result.triage_pending_count == 4
        assert result.generated_at.tzinfo is not None
        for mock_fn in (mock_leads, mock_members, mock_actions):
            assert mock_fn.call_args.kwargs["gym_id"] == GYM_ID


class TestListCap:
    def test_cap_is_ten(self):
        assert LIST_CAP == 10
