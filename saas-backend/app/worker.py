import logging
import signal
import time

from app.background_jobs.scheduler import build_scheduler
from app.core.logging_config import configure_logging


configure_logging()

running = True
logger = logging.getLogger(__name__)


def _stop_handler(*_args) -> None:
    global running
    running = False


def main() -> None:
    logger.info("Scheduler worker starting dedicated scheduler process.")
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Scheduler worker started dedicated scheduler process.")
    signal.signal(signal.SIGTERM, _stop_handler)
    signal.signal(signal.SIGINT, _stop_handler)
    try:
        while running:
            time.sleep(1)
    finally:
        logger.info("Scheduler worker shutting down dedicated scheduler process.")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
