import logging
import signal
import time

from app.background_jobs.scheduler import build_scheduler, should_start_scheduler_in_worker
from app.background_jobs.jobs import retention_alert_backfill_job
from app.core.logging_config import configure_logging
from app.core.config import settings


configure_logging()

if settings.sentry_dsn:
    import sentry_sdk

    def _before_send_sentry(event, _hint):
        event.pop("user", None)
        event.pop("request", None)
        return event

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        send_default_pii=False,
        traces_sample_rate=0.02,
        before_send=_before_send_sentry,
    )

running = True
logger = logging.getLogger(__name__)


def _stop_handler(*_args) -> None:
    global running
    running = False


def main() -> None:
    if not should_start_scheduler_in_worker():
        logger.warning(
            "Scheduler worker started with ENABLE_SCHEDULER=false; exiting without starting jobs.",
            extra={"extra_fields": {"event": "scheduler_worker_disabled", "status": "disabled"}},
        )
        return

    logger.info(
        "Scheduler worker starting dedicated scheduler process.",
        extra={"extra_fields": {"event": "scheduler_worker_starting", "status": "starting", "release_sha": settings.release_sha}},
    )
    retention_alert_backfill_job()
    scheduler = build_scheduler()
    scheduler.start()
    logger.info(
        "Scheduler worker started dedicated scheduler process.",
        extra={"extra_fields": {"event": "scheduler_worker_started", "status": "started"}},
    )
    signal.signal(signal.SIGTERM, _stop_handler)
    signal.signal(signal.SIGINT, _stop_handler)
    try:
        while running:
            time.sleep(1)
    finally:
        logger.info(
            "Scheduler worker shutting down dedicated scheduler process.",
            extra={"extra_fields": {"event": "scheduler_worker_stopping", "status": "stopping"}},
        )
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
