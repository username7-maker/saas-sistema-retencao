from typing import Any, Callable

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler  # type: ignore
    from slowapi.errors import RateLimitExceeded  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore

    limiter = Limiter(key_func=get_remote_address, default_limits=[])
    rate_limit_exceeded_handler = _rate_limit_exceeded_handler
    rate_limit_enabled = True
except ImportError:
    class _NoopLimiter:
        def limit(self, _: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return decorator

    class RateLimitExceeded(Exception):
        pass

    def rate_limit_exceeded_handler(*_: Any, **__: Any) -> Any:
        return None

    limiter = _NoopLimiter()
    rate_limit_enabled = False
