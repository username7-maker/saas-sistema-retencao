"""Tests for nps_service and member_timeline_service."""

import uuid
from datetime import datetime, date, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models import MemberStatus, NPSSentiment, NPSTrigger, RiskLevel

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


# ---------------------------------------------------------------------------
# nps_service — create_response
# ---------------------------------------------------------------------------

class TestCreateResponse:
    @patch("app.services.nps_service.invalidate_dashboard_cache")
    @patch("app.services.nps_service.log_audit_event")
    @patch("app.services.nps_service.analyze_sentiment", return_value=(NPSSentiment.POSITIVE, "Otimo"))
    def test_creates_response_and_updates_member(self, mock_sentiment, mock_audit, mock_cache):
        member = SimpleNamespace(id=MEMBER_ID, nps_last_score=7)
        db = MagicMock()
        db.get.return_value = member

        from app.schemas.nps import NPSResponseCreate
        payload = NPSResponseCreate(
            member_id=MEMBER_ID, score=9,
            comment="Otimo!", trigger=NPSTrigger.MONTHLY,
        )
        from app.services.nps_service import create_response
        create_response(db, payload)
        assert member.nps_last_score == 9
        db.commit.assert_called_once()

    @patch("app.services.nps_service.invalidate_dashboard_cache")
    @patch("app.services.nps_service.log_audit_event")
    @patch("app.services.nps_service.analyze_sentiment", return_value=(NPSSentiment.POSITIVE, "Otimo"))
    def test_creates_response_without_committing_when_router_owns_transaction(self, mock_sentiment, mock_audit, mock_cache):
        member = SimpleNamespace(id=MEMBER_ID, nps_last_score=7)
        db = MagicMock()
        db.get.return_value = member

        from app.schemas.nps import NPSResponseCreate

        payload = NPSResponseCreate(
            member_id=MEMBER_ID,
            score=9,
            comment="Otimo!",
            trigger=NPSTrigger.MONTHLY,
        )
        from app.services.nps_service import create_response

        create_response(db, payload, commit=False)

        assert member.nps_last_score == 9
        db.commit.assert_not_called()
        db.flush.assert_called_once()

    @patch("app.services.nps_service.invalidate_dashboard_cache")
    @patch("app.services.nps_service.log_audit_event")
    @patch("app.services.nps_service.analyze_sentiment", return_value=(NPSSentiment.NEGATIVE, "Ruim"))
    def test_negative_logs_audit(self, mock_sentiment, mock_audit, mock_cache):
        member = SimpleNamespace(id=MEMBER_ID, nps_last_score=5)
        db = MagicMock()
        db.get.return_value = member

        from app.schemas.nps import NPSResponseCreate
        payload = NPSResponseCreate(
            member_id=MEMBER_ID, score=3,
            comment="Ruim", trigger=NPSTrigger.MONTHLY,
        )
        from app.services.nps_service import create_response
        create_response(db, payload)
        mock_audit.assert_called()


# ---------------------------------------------------------------------------
# nps_service — run_nps_dispatch
# ---------------------------------------------------------------------------

class TestRunNpsDispatch:
    @patch("app.services.nps_service.send_email", return_value=True)
    @patch("app.services.nps_service.log_audit_event")
    def test_dispatches_surveys(self, mock_audit, mock_email):
        member = SimpleNamespace(
            id=MEMBER_ID, email="aluno@t.com", full_name="Aluno",
            status=MemberStatus.ACTIVE, risk_level=RiskLevel.GREEN,
            join_date=date.today() - timedelta(days=30),
            deleted_at=None,
        )
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [member]
        db.scalars.return_value = mock_scalars
        db.scalar.return_value = None  # No recent NPS audit log

        from app.services.nps_service import run_nps_dispatch
        result = run_nps_dispatch(db)
        assert isinstance(result, dict)

    @patch("app.services.nps_service.send_email", return_value=True)
    @patch("app.services.nps_service.log_audit_event")
    def test_dispatches_surveys_without_committing_when_router_owns_transaction(self, mock_audit, mock_email):
        member = SimpleNamespace(
            id=MEMBER_ID, email="aluno@t.com", full_name="Aluno",
            status=MemberStatus.ACTIVE, risk_level=RiskLevel.GREEN,
            join_date=date.today() - timedelta(days=30),
            deleted_at=None,
        )
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [member]
        db.scalars.return_value = mock_scalars
        db.scalar.return_value = None

        from app.services.nps_service import run_nps_dispatch

        result = run_nps_dispatch(db, commit=False)

        assert isinstance(result, dict)
        db.commit.assert_not_called()
        db.flush.assert_called_once()


# ---------------------------------------------------------------------------
# nps_service — nps_evolution
# ---------------------------------------------------------------------------

class TestNpsEvolution:
    def test_returns_points(self):
        db = MagicMock()
        row = SimpleNamespace(month="2026-01", avg_score=8.5, responses=50)
        db.execute.return_value.all.return_value = [row]
        from app.services.nps_service import nps_evolution
        result = nps_evolution(db, months=6)
        assert len(result) == 1
        assert result[0].month == "2026-01"
        assert result[0].average_score == 8.5


# ---------------------------------------------------------------------------
# member_timeline_service
# ---------------------------------------------------------------------------

class TestMemberTimeline:
    def test_builds_timeline(self):
        assessments = [
            SimpleNamespace(
                assessment_date=datetime(2026, 3, 5, tzinfo=timezone.utc),
                assessment_number=1,
                weight_kg=75.0, body_fat_pct=18.0, strength_score=70,
                flexibility_score=None, cardio_score=None,
            ),
        ]
        checkins = [
            SimpleNamespace(checkin_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc), source=SimpleNamespace(value="manual")),
        ]
        risk_alerts = [
            SimpleNamespace(created_at=datetime(2026, 3, 4, tzinfo=timezone.utc), level=SimpleNamespace(value="yellow"), score=45, resolved=False),
        ]
        nps_items = [
            SimpleNamespace(created_at=datetime(2026, 3, 2, tzinfo=timezone.utc), score=9, sentiment=SimpleNamespace(value="positive"), comment="Otimo"),
        ]
        tasks = [
            SimpleNamespace(
                created_at=datetime(2026, 3, 3, tzinfo=timezone.utc), title="Follow-up",
                status=SimpleNamespace(value="todo"), priority=SimpleNamespace(value="medium"),
                completed_at=None, due_date=None, extra_data={}, deleted_at=None,
                member_id=MEMBER_ID,
            ),
        ]
        audit_events = []
        bce_list = [
            SimpleNamespace(
                evaluation_date=date(2026, 3, 6),
                source="ocr_receipt",
                ai_risk_flags_json=["percentual de gordura acima da faixa", "gordura visceral acima da faixa"],
                health_score=62,
                actuar_sync_status="sync_pending",
            ),
        ]

        db = MagicMock()
        # Order matches member_timeline_service: assessments, goals, training_plans,
        # checkins, risk_alerts, nps_responses, tasks, audit_events, body_composition
        scalars_results = [
            MagicMock(all=MagicMock(return_value=assessments)),
            MagicMock(all=MagicMock(return_value=[])),   # goals
            MagicMock(all=MagicMock(return_value=[])),   # training_plans
            MagicMock(all=MagicMock(return_value=checkins)),
            MagicMock(all=MagicMock(return_value=risk_alerts)),
            MagicMock(all=MagicMock(return_value=nps_items)),
            MagicMock(all=MagicMock(return_value=tasks)),
            MagicMock(all=MagicMock(return_value=audit_events)),
            MagicMock(all=MagicMock(return_value=bce_list)),
        ]
        db.scalars.side_effect = scalars_results
        db.scalar.return_value = None  # constraints

        from app.services.member_timeline_service import get_member_timeline
        result = get_member_timeline(db, MEMBER_ID)
        assert len(result) == 6  # 1 assessment + 1 checkin + 1 risk + 1 nps + 1 task + 1 bioimpedancia
        assert result[0]["title"] == "Bioimpedancia registrada"
        assert "health score 62" in result[0]["detail"]
        assert "sync pendente" in result[0]["detail"]

    def test_empty_timeline(self):
        db = MagicMock()
        empty = MagicMock(all=MagicMock(return_value=[]))
        db.scalars.side_effect = [empty, empty, empty, empty, empty, empty, empty, empty, empty]
        db.scalar.return_value = None  # constraints

        from app.services.member_timeline_service import get_member_timeline
        result = get_member_timeline(db, MEMBER_ID)
        assert result == []
