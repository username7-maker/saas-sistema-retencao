import logging
import signal
import time

from app.background_jobs.scheduler import build_scheduler, should_start_scheduler_in_worker
from app.core.logging_config import configure_logging


configure_logging()

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
        extra={"extra_fields": {"event": "scheduler_worker_starting", "status": "starting"}},
    )
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
