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
    from redis.exceptions import RedisError
except ImportError:
    Redis = None  # type: ignore[assignment,misc]
    RedisError = Exception  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_KEY_PREFIX = "aigymos:scheduler-lock"

_redis_client: "Redis | None" = None
_redis_checked = False


def _get_redis() -> "Redis | None":
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    if not settings.redis_url or Redis is None:
        logger.info("Distributed lock: Redis indisponivel, jobs rodarao sem lock.")
        return None
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        logger.info("Distributed lock: Redis conectado.")
    except Exception:
        logger.exception("Distributed lock: falha ao conectar Redis. Jobs rodarao sem lock.")
        _redis_client = None
    return _redis_client


def with_distributed_lock(
    lock_name: str,
    ttl_seconds: int = 1800,
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
            redis = _get_redis()
            if redis is None:
                return func(*args, **kwargs)

            lock_key = f"{_KEY_PREFIX}:{lock_name}"
            lock_value = str(uuid.uuid4())

            try:
                acquired = redis.set(lock_key, lock_value, nx=True, ex=ttl_seconds)
            except RedisError:
                logger.warning("Distributed lock: Redis error acquiring lock %s. Running job anyway.", lock_name)
                return func(*args, **kwargs)

            if not acquired:
                logger.info("Distributed lock: job '%s' already running on another instance. Skipping.", lock_name)
                return None

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
                except RedisError:
                    logger.warning("Distributed lock: failed to release lock %s (will auto-expire).", lock_name)

        return wrapper

    return decorator
