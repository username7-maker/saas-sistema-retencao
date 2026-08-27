from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.background_jobs import jobs
from app.services.retention_alert_backfill_service import backfill_retention_alerts_for_current_gym
from app.services.risk import _prefetch_resolved_retention_episodes, sync_retention_alerts_from_member_activity


def test_backfill_is_skipped_after_completion_marker():
    db = MagicMock()
    db.scalar.return_value = "marker-id"

    with patch(
        "app.services.retention_alert_backfill_service.sync_retention_alerts_from_member_activity"
    ) as sync_retention_alerts:
        result = backfill_retention_alerts_for_current_gym(db)

    assert result == {"members_refreshed": 0, "alerts_synced": 0, "already_completed": True}
    sync_retention_alerts.assert_not_called()
    db.commit.assert_not_called()


def test_backfill_refreshes_all_members_in_batches_and_persists_marker():
    db = MagicMock()
    db.scalar.return_value = None
    db.scalars.return_value.all.return_value = list(range(501))

    with (
        patch(
            "app.services.retention_alert_backfill_service.sync_retention_alerts_from_member_activity",
            side_effect=[
                {"members_refreshed": 500, "alerts_synced": 120},
                {"members_refreshed": 1, "alerts_synced": 1},
            ],
        ) as sync_retention_alerts,
        patch("app.services.retention_alert_backfill_service.log_audit_event") as log_audit_event,
    ):
        result = backfill_retention_alerts_for_current_gym(db)

    assert result == {"members_refreshed": 501, "alerts_synced": 121, "already_completed": False}
    assert sync_retention_alerts.call_count == 2
    assert len(sync_retention_alerts.call_args_list[0].kwargs["member_ids"]) == 500
    assert len(sync_retention_alerts.call_args_list[1].kwargs["member_ids"]) == 1
    log_audit_event.assert_called_once()
    db.commit.assert_called_once()


def test_backfill_job_repairs_guard_and_processes_every_active_gym():
    db = MagicMock()
    gyms = [SimpleNamespace(id="gym-a"), SimpleNamespace(id="gym-b")]

    with (
        patch("app.background_jobs.jobs.SessionLocal", return_value=db),
        patch("app.background_jobs.jobs._active_gyms", return_value=gyms),
        patch("app.background_jobs.jobs.set_current_gym_id") as set_current_gym_id,
        patch("app.background_jobs.jobs.clear_current_gym_id"),
        patch("app.background_jobs.jobs.repair_retention_episode_guard") as repair_guard,
        patch(
            "app.background_jobs.jobs.backfill_retention_alerts_for_current_gym",
            side_effect=[
                {"members_refreshed": 10, "alerts_synced": 4, "already_completed": False},
                {"members_refreshed": 8, "alerts_synced": 3, "already_completed": False},
            ],
        ) as backfill,
        patch("app.background_jobs.jobs.settings.scheduler_critical_lock_fail_open", True),
    ):
        jobs.retention_alert_backfill_job()

    repair_guard.assert_called_once_with(db)
    assert backfill.call_count == 2
    set_current_gym_id.assert_has_calls([call("gym-a"), call("gym-b")])
    db.close.assert_called_once()


def test_activity_backfill_creates_alerts_only_from_seven_days_onward():
    now = datetime(2026, 8, 20, tzinfo=timezone.utc)
    gym_id = uuid4()
    recent_member = SimpleNamespace(
        id=uuid4(), gym_id=gym_id, last_checkin_at=now - timedelta(days=6), join_date=None, risk_score=10
    )
    inactive_member = SimpleNamespace(
        id=uuid4(), gym_id=gym_id, last_checkin_at=now - timedelta(days=41), join_date=None, risk_score=20
    )
    members_result = MagicMock()
    members_result.all.return_value = [recent_member, inactive_member]
    alerts_result = MagicMock()
    alerts_result.all.return_value = []
    db = MagicMock()
    db.scalars.side_effect = [members_result, alerts_result]
    db.execute.return_value.all.return_value = []

    result = sync_retention_alerts_from_member_activity(
        db,
        member_ids=[recent_member.id, inactive_member.id],
        now=now,
    )

    assert result == {"members_refreshed": 2, "alerts_synced": 1}
    added_alerts = [
        entry.args[0]
        for entry in db.add.call_args_list
        if getattr(entry.args[0], "member_id", None) == inactive_member.id
    ]
    assert len(added_alerts) == 1
    assert added_alerts[0].automation_stage == "d41"
    assert added_alerts[0].score == 40


def test_resolved_episode_query_only_suppresses_human_resolutions():
    db = MagicMock()
    db.execute.return_value.all.return_value = []

    _prefetch_resolved_retention_episodes(db, member_ids={uuid4()})

    stmt = db.execute.call_args.args[0]
    compiled = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "resolved_by_user_id IS NOT NULL" in compiled
