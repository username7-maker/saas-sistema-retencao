from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

from app.background_jobs import jobs
from app.core.config import settings


def _gym(gym_id: str) -> SimpleNamespace:
    return SimpleNamespace(id=gym_id)


@pytest.mark.parametrize(
    ("job_func", "runner_patch", "success_result"),
    [
        (jobs.daily_nps_dispatch_job, "app.background_jobs.jobs.run_nps_dispatch", {"sent": 1}),
        (jobs.daily_crm_followup_job, "app.background_jobs.jobs.run_followup_automation", 3),
        (jobs.monthly_reports_job, "app.background_jobs.jobs.send_monthly_reports", {"reports": 1}),
        (jobs.daily_automations_job, "app.background_jobs.jobs.run_automation_rules", [{"rule_id": "rule-1"}]),
        (jobs.sunday_briefing_job, "app.background_jobs.jobs.generate_and_send_weekly_briefing", {"sent": 1}),
        (jobs.proposal_followup_job, "app.background_jobs.jobs.process_proposal_followups", {"created": 1}),
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
    ):
        job_func()

    assert runner.call_count == 2
    assert db.rollback.call_count == 1
    assert db.commit.call_count == 1
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
