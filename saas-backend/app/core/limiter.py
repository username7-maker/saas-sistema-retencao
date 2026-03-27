from typing import Any, Callable

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler  # type: ignore
    from slowapi.errors import RateLimitExceeded  # type: ignore
    from slowapi.middleware import SlowAPIMiddleware  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore

    limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
    rate_limit_exceeded_handler = _rate_limit_exceeded_handler
    rate_limit_enabled = True
except ImportError:
    SlowAPIMiddleware = None  # type: ignore[assignment,misc]

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


def ensure_rate_limiting_ready(environment: str) -> None:
    if environment.lower() == "production" and not rate_limit_enabled:
        raise RuntimeError("Rate limiting real e obrigatorio em producao")
