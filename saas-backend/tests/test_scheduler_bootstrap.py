import asyncio
from unittest.mock import MagicMock, patch


async def _run_lifespan(lifespan_context_manager) -> None:
    async with lifespan_context_manager(None):
        return None


def test_scheduler_helper_disables_api_by_default(monkeypatch):
    from app.background_jobs import scheduler

    monkeypatch.setattr(scheduler.settings, "enable_scheduler", False)
    monkeypatch.setattr(scheduler.settings, "enable_scheduler_in_api", False)

    assert scheduler.should_start_scheduler_in_api() is False
    assert scheduler.should_start_scheduler_in_worker() is False


def test_scheduler_helper_allows_worker_without_api(monkeypatch):
    from app.background_jobs import scheduler

    monkeypatch.setattr(scheduler.settings, "enable_scheduler", True)
    monkeypatch.setattr(scheduler.settings, "enable_scheduler_in_api", False)

    assert scheduler.should_start_scheduler_in_api() is False
    assert scheduler.should_start_scheduler_in_worker() is True


def test_api_lifespan_does_not_start_scheduler_when_not_explicitly_enabled():
    from app.main import lifespan

    with patch("app.main.should_start_scheduler_in_api", return_value=False), patch(
        "app.main.build_scheduler"
    ) as build_scheduler, patch("app.main.websocket_manager.set_event_loop") as set_event_loop, patch(
        "app.main.websocket_manager.clear_event_loop"
    ) as clear_event_loop:
        asyncio.run(_run_lifespan(lifespan))

    build_scheduler.assert_not_called()
    set_event_loop.assert_called_once()
    clear_event_loop.assert_called_once()


def test_api_lifespan_starts_and_stops_scheduler_when_explicitly_enabled():
    from app.main import lifespan

    scheduler = MagicMock()
    with patch("app.main.should_start_scheduler_in_api", return_value=True), patch(
        "app.main.build_scheduler", return_value=scheduler
    ) as build_scheduler, patch("app.main.websocket_manager.set_event_loop") as set_event_loop, patch(
        "app.main.websocket_manager.clear_event_loop"
    ) as clear_event_loop:
        asyncio.run(_run_lifespan(lifespan))

    build_scheduler.assert_called_once()
    scheduler.start.assert_called_once()
    scheduler.shutdown.assert_called_once_with(wait=False)
    set_event_loop.assert_called_once()
    clear_event_loop.assert_called_once()


def test_worker_does_not_start_scheduler_when_disabled():
    import app.worker as worker_module

    with patch("app.worker.should_start_scheduler_in_worker", return_value=False), patch(
        "app.worker.build_scheduler"
    ) as build_scheduler:
        worker_module.main()

    build_scheduler.assert_not_called()


def test_worker_starts_scheduler_when_enabled():
    import app.worker as worker_module

    scheduler = MagicMock()
    original_running = worker_module.running
    worker_module.running = False
    try:
        with patch("app.worker.should_start_scheduler_in_worker", return_value=True), patch(
            "app.worker.build_scheduler", return_value=scheduler
        ) as build_scheduler, patch("app.worker.signal.signal"):
            worker_module.main()
    finally:
        worker_module.running = original_running

    build_scheduler.assert_called_once()
    scheduler.start.assert_called_once()
    scheduler.shutdown.assert_called_once_with(wait=False)


def test_instrument_scheduler_job_logs_completion(caplog):
    from app.background_jobs.scheduler import instrument_scheduler_job

    def job():
        return "ok"

    wrapped = instrument_scheduler_job("daily_risk", job)

    with caplog.at_level("INFO"):
        result = wrapped()

    assert result == "ok"
    events = [record.extra_fields["event"] for record in caplog.records if hasattr(record, "extra_fields")]
    assert events == ["job_started", "job_completed"]
    completed = next(record for record in caplog.records if getattr(record, "extra_fields", {}).get("event") == "job_completed")
    assert completed.extra_fields["job_name"] == "daily_risk"
    assert completed.extra_fields["status"] == "completed"
    assert completed.extra_fields["duration_ms"] >= 0


def test_instrument_scheduler_job_logs_failure_and_reraises(caplog):
    from app.background_jobs.scheduler import instrument_scheduler_job

    def job():
        raise RuntimeError("boom")

    wrapped = instrument_scheduler_job("daily_risk", job)

    with caplog.at_level("INFO"):
        try:
            wrapped()
        except RuntimeError as exc:
            assert str(exc) == "boom"
        else:
            raise AssertionError("Expected RuntimeError")

    events = [record.extra_fields["event"] for record in caplog.records if hasattr(record, "extra_fields")]
    assert events == ["job_started", "job_failed"]
    failed = next(record for record in caplog.records if getattr(record, "extra_fields", {}).get("event") == "job_failed")
    assert failed.extra_fields["job_name"] == "daily_risk"
    assert failed.extra_fields["status"] == "failed"
    assert failed.extra_fields["duration_ms"] >= 0
