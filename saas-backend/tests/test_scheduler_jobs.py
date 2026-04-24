from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch
from contextlib import contextmanager

import pytest

from app.background_jobs import jobs
from app.core.config import settings


def _gym(gym_id: str) -> SimpleNamespace:
    return SimpleNamespace(id=gym_id)


@pytest.mark.parametrize(
    ("job_func", "runner_patch", "success_result"),
    [
        (jobs.daily_crm_followup_job, "app.background_jobs.jobs.run_followup_automation", 3),
        (jobs.daily_automations_job, "app.background_jobs.jobs.run_automation_rules", [{"rule_id": "rule-1"}]),
        (jobs.sunday_briefing_job, "app.background_jobs.jobs.generate_and_send_weekly_briefing", {"sent": 1}),
        (jobs.proposal_followup_job, "app.background_jobs.jobs.process_proposal_followups", {"created": 1}),
        (jobs.daily_preferred_shift_sync_job, "app.background_jobs.jobs.sync_preferred_shifts_from_checkins", 5),
    ],
)
def test_multi_tenant_jobs_continue_after_a_gym_failure(job_func, runner_patch, success_result):
    db = MagicMock()
    gyms = [_gym("gym-a"), _gym("gym-b")]

    with (
        patch("app.background_jobs.jobs.SessionLocal", return_value=db),
        patch("app.background_jobs.jobs._active_gyms", return_value=gyms),
        patch("app.background_jobs.jobs.set_current_gym_id") as mock_set_gym,
        patch("app.background_jobs.jobs.clear_current_gym_id"),
        patch(runner_patch, side_effect=[RuntimeError("boom"), success_result]) as runner,
        patch.object(settings, "scheduler_critical_lock_fail_open", True),
        patch.object(settings, "monthly_reports_dispatch_enabled", True),
    ):
        job_func()

    assert runner.call_count == 2
    assert db.rollback.call_count == 1
    assert db.commit.call_count == 1
    mock_set_gym.assert_has_calls([call("gym-a"), call("gym-b")])
    db.close.assert_called_once()


def test_daily_nps_dispatch_job_enqueues_durable_job_per_gym():
    db = MagicMock()
    gyms = [_gym("gym-a"), _gym("gym-b")]

    with (
        patch("app.background_jobs.jobs.SessionLocal", return_value=db),
        patch("app.background_jobs.jobs._active_gyms", return_value=gyms),
        patch("app.background_jobs.jobs.set_current_gym_id") as mock_set_gym,
        patch("app.background_jobs.jobs.clear_current_gym_id"),
        patch(
            "app.background_jobs.jobs.enqueue_nps_dispatch_job",
            side_effect=[
                (SimpleNamespace(id="job-a", status="pending"), True),
                (SimpleNamespace(id="job-b", status="pending"), False),
            ],
        ) as enqueue_job,
        patch.object(settings, "scheduler_critical_lock_fail_open", True),
    ):
        jobs.daily_nps_dispatch_job()

    assert enqueue_job.call_count == 2
    assert db.commit.call_count == 2
    mock_set_gym.assert_has_calls([call("gym-a"), call("gym-b")])
    db.close.assert_called_once()


def test_monthly_reports_job_enqueues_durable_job_per_gym():
    db = MagicMock()
    gyms = [_gym("gym-a"), _gym("gym-b")]

    with (
        patch("app.background_jobs.jobs.SessionLocal", return_value=db),
        patch("app.background_jobs.jobs._active_gyms", return_value=gyms),
        patch("app.background_jobs.jobs.set_current_gym_id") as mock_set_gym,
        patch("app.background_jobs.jobs.clear_current_gym_id"),
        patch(
            "app.background_jobs.jobs.enqueue_monthly_reports_dispatch_job",
            side_effect=[
                (SimpleNamespace(id="job-a", status="pending"), True),
                (SimpleNamespace(id="job-b", status="retry_scheduled"), False),
            ],
        ) as enqueue_job,
        patch.object(settings, "scheduler_critical_lock_fail_open", True),
        patch.object(settings, "monthly_reports_dispatch_enabled", True),
    ):
        jobs.monthly_reports_job()

    assert enqueue_job.call_count == 2
    assert db.commit.call_count == 2
    mock_set_gym.assert_has_calls([call("gym-a"), call("gym-b")])
    db.close.assert_called_once()


def test_daily_loyalty_update_job_commits_per_successful_gym():
    first_scalars = RuntimeError("boom")
    second_batch = MagicMock()
    second_batch.all.return_value = [
        SimpleNamespace(join_date=date(2025, 1, 15), loyalty_months=0),
        SimpleNamespace(join_date=date(2024, 12, 1), loyalty_months=0),
    ]
    empty_batch = MagicMock()
    empty_batch.all.return_value = []
    db = MagicMock()
    db.scalars.side_effect = [first_scalars, second_batch, empty_batch]
    gyms = [_gym("gym-a"), _gym("gym-b")]

    with (
        patch("app.background_jobs.jobs.SessionLocal", return_value=db),
        patch("app.background_jobs.jobs._active_gyms", return_value=gyms),
        patch("app.background_jobs.jobs.set_current_gym_id") as mock_set_gym,
        patch("app.background_jobs.jobs.clear_current_gym_id"),
        patch.object(settings, "scheduler_critical_lock_fail_open", True),
        patch.object(settings, "loyalty_update_batch_size", 500),
    ):
        jobs.daily_loyalty_update_job()

    assert db.rollback.call_count == 1
    assert db.commit.call_count == 1
    assert db.flush.call_count == 1
    mock_set_gym.assert_has_calls([call("gym-a"), call("gym-b")])
    db.close.assert_called_once()


def test_monthly_reports_job_skips_when_dispatch_disabled():
    with (
        patch.object(settings, "monthly_reports_dispatch_enabled", False),
        patch("app.background_jobs.jobs.SessionLocal") as session_local,
        patch("app.background_jobs.jobs.enqueue_monthly_reports_dispatch_job") as enqueue_monthly_reports_dispatch_job,
    ):
        jobs.monthly_reports_job()

    session_local.assert_not_called()
    enqueue_monthly_reports_dispatch_job.assert_not_called()


def test_nurturing_followup_job_uses_allowlisted_unscoped_reason():
    db = MagicMock()
    seen_reasons: list[str] = []

    @contextmanager
    def _capture(reason: str):
        seen_reasons.append(reason)
        yield

    with (
        patch("app.background_jobs.jobs.SessionLocal", return_value=db),
        patch("app.background_jobs.jobs.unscoped_tenant_access", side_effect=_capture),
        patch("app.background_jobs.jobs.run_nurturing_followup", return_value={"processed": 1}),
        patch("app.background_jobs.jobs.clear_current_gym_id"),
        patch.object(settings, "scheduler_critical_lock_fail_open", True),
    ):
        jobs.nurturing_followup_job()

    assert seen_reasons == ["jobs.nurturing_followup_job"]
    db.close.assert_called_once()


def test_booking_reminder_job_uses_allowlisted_unscoped_reason():
    db = MagicMock()
    seen_reasons: list[str] = []

    @contextmanager
    def _capture(reason: str):
        seen_reasons.append(reason)
        yield

    with (
        patch("app.background_jobs.jobs.SessionLocal", return_value=db),
        patch("app.background_jobs.jobs.unscoped_tenant_access", side_effect=_capture),
        patch("app.background_jobs.jobs.process_booking_reminders", return_value={"processed": 1, "sent": 1}),
        patch("app.background_jobs.jobs.clear_current_gym_id"),
        patch.object(settings, "scheduler_critical_lock_fail_open", True),
    ):
        jobs.booking_reminder_job()

    assert seen_reasons == ["jobs.booking_reminder_job"]
    db.close.assert_called_once()
