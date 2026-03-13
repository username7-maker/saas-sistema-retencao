"""
Test circuit breaker behavior.
"""
import time
from unittest.mock import patch

from app.core.circuit_breaker import CircuitBreaker


def test_circuit_breaker_starts_closed():
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout_seconds=60)
    assert not cb.is_open()


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout_seconds=60)
    for _ in range(3):
        cb.record_failure()
    assert cb.is_open()


def test_circuit_breaker_resets_on_success():
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout_seconds=60)
    for _ in range(2):
        cb.record_failure()
    cb.record_success()
    assert not cb.is_open()
    assert cb._failure_count == 0
    assert cb._state == "closed"


def test_circuit_breaker_recovers_after_timeout():
    cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout_seconds=1)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open()

    # Simulate timeout passing
    cb._last_failure_time = time.time() - 2  # 2 seconds ago
    # After timeout, should be half_open (not open)
    assert not cb.is_open()
    assert cb._state == "half_open"


def test_circuit_breaker_below_threshold_stays_closed():
    cb = CircuitBreaker(name="test", failure_threshold=5, recovery_timeout_seconds=60)
    for _ in range(4):
        cb.record_failure()
    assert not cb.is_open()
    assert cb._state == "closed"
