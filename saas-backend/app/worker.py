import signal
import time

from app.background_jobs.scheduler import build_scheduler


running = True


def _stop_handler(*_args) -> None:
    global running
    running = False


def main() -> None:
    scheduler = build_scheduler()
    scheduler.start()
    signal.signal(signal.SIGTERM, _stop_handler)
    signal.signal(signal.SIGINT, _stop_handler)
    try:
        while running:
            time.sleep(1)
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
