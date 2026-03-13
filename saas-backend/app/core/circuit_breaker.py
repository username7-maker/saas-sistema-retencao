"""Circuit breaker for external API calls.

Protects AI services from cascading failures when Claude API is unavailable.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreaker:
    """Circuit breaker simples para proteger chamadas a APIs externas."""
    name: str
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _state: str = field(default="closed", init=False)  # closed, open, half_open

    def is_open(self) -> bool:
        if self._state == "open":
            if time.time() - self._last_failure_time >= self.recovery_timeout_seconds:
                self._state = "half_open"
                return False
            return True
        return False

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(
                "Circuit breaker '%s' ABERTO apos %d falhas",
                self.name,
                self._failure_count,
            )


# Instancia global para Claude API
claude_circuit_breaker = CircuitBreaker(
    name="claude_api",
    failure_threshold=5,
    recovery_timeout_seconds=120,
)
