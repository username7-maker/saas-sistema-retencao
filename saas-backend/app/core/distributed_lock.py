"""Redis-based distributed lock for background scheduler jobs.

Prevents duplicate job execution when multiple backend instances are running
(e.g. Railway auto-scaling). If Redis is unavailable, jobs run without
locking (prefer occasional duplicate over silent skip).
"""

import functools
import logging
import uuid
from collections.abc import Callable
from typing import Any

from app.core.config import settings

try:
    from redis import Redis
except ImportError:
    Redis = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_KEY_PREFIX = "aigymos:scheduler-lock"

_redis_client: "Redis | None" = None
_redis_checked = False


def _log_lock_event(
    level: int,
    message: str,
    *,
    event: str,
    lock_name: str,
    ttl_seconds: int | None = None,
    status: str,
    fail_open: bool | None = None,
    exc_info: Any = None,
) -> None:
    extra_fields: dict[str, Any] = {
        "event": event,
        "job_name": lock_name,
        "lock_name": lock_name,
        "status": status,
    }
    if ttl_seconds is not None:
        extra_fields["ttl_seconds"] = ttl_seconds
    if fail_open is not None:
        extra_fields["fail_open"] = fail_open
    logger.log(level, message, exc_info=exc_info, extra={"extra_fields": extra_fields})


def _get_redis() -> "Redis | None":
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    if not settings.redis_url or Redis is None:
        return None
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        logger.info("Distributed lock: Redis connected.")
    except Exception:
        logger.exception("Distributed lock: failed connecting to Redis. Jobs will run without lock.")
        _redis_client = None
    return _redis_client


def with_distributed_lock(
    lock_name: str,
    ttl_seconds: int = 1800,
    fail_open: bool | Callable[[], bool] = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that acquires a Redis lock before running a job.

    Args:
        lock_name: Unique identifier for this job's lock.
        ttl_seconds: Max time the lock is held (auto-expires as safety net).
                     Default 30 minutes — long enough for most jobs.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            resolved_fail_open = fail_open() if callable(fail_open) else fail_open
            redis = _get_redis()
            if redis is None:
                if not resolved_fail_open:
                    _log_lock_event(
                        logging.WARNING,
                        "Distributed lock unavailable; skipping execution.",
                        event="job_skipped_lock_unavailable",
                        lock_name=lock_name,
                        ttl_seconds=ttl_seconds,
                        status="skipped_lock_unavailable",
                        fail_open=resolved_fail_open,
                    )
                    return None
                _log_lock_event(
                    logging.WARNING,
                    "Distributed lock unavailable; running without lock.",
                    event="lock_unavailable",
                    lock_name=lock_name,
                    ttl_seconds=ttl_seconds,
                    status="unavailable",
                    fail_open=resolved_fail_open,
                )
                return func(*args, **kwargs)

            lock_key = f"{_KEY_PREFIX}:{lock_name}"
            lock_value = str(uuid.uuid4())

            try:
                acquired = redis.set(lock_key, lock_value, nx=True, ex=ttl_seconds)
            except Exception:
                _log_lock_event(
                    logging.ERROR,
                    "Distributed lock acquire failed; running without lock.",
                    event="lock_acquire_failed",
                    lock_name=lock_name,
                    ttl_seconds=ttl_seconds,
                    status="degraded",
                    fail_open=resolved_fail_open,
                    exc_info=True,
                )
                if not resolved_fail_open:
                    _log_lock_event(
                        logging.WARNING,
                        "Distributed lock acquire failed; skipping execution.",
                        event="job_skipped_lock_unavailable",
                        lock_name=lock_name,
                        ttl_seconds=ttl_seconds,
                        status="skipped_lock_unavailable",
                        fail_open=resolved_fail_open,
                    )
                    return None
                return func(*args, **kwargs)

            if not acquired:
                _log_lock_event(
                    logging.INFO,
                    "Distributed lock already held; skipping execution.",
                    event="job_skipped_lock",
                    lock_name=lock_name,
                    ttl_seconds=ttl_seconds,
                    status="skipped_lock",
                    fail_open=resolved_fail_open,
                )
                return None

            _log_lock_event(
                logging.INFO,
                "Distributed lock acquired.",
                event="lock_acquired",
                lock_name=lock_name,
                ttl_seconds=ttl_seconds,
                status="acquired",
                fail_open=resolved_fail_open,
            )
            try:
                return func(*args, **kwargs)
            finally:
                try:
                    # Only release if we still own the lock (compare-and-delete via Lua)
                    _release_script = """
                    if redis.call("get", KEYS[1]) == ARGV[1] then
                        return redis.call("del", KEYS[1])
                    else
                        return 0
                    end
                    """
                    redis.eval(_release_script, 1, lock_key, lock_value)
                except Exception:
                    _log_lock_event(
                        logging.ERROR,
                        "Distributed lock release failed; lock will auto-expire.",
                        event="lock_release_failed",
                        lock_name=lock_name,
                        ttl_seconds=ttl_seconds,
                        status="release_failed",
                        fail_open=resolved_fail_open,
                        exc_info=True,
                    )

        return wrapper

    return decorator
